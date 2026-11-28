"""Verify existing ULTRON data and prepare metadata-only deterministic splits."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, math, os, re, sqlite3, tempfile
from pathlib import Path
from .data_generation import verify_dataset
from .dataset_resource_limits import DatasetResourceLimits

_METHOD="prompt_group_hash_v1"
_SHA=re.compile(r"[0-9a-f]{64}")
_MAX_SPLIT=32*1024*1024
_MAX_DATA=1024*1024*1024
_MAX_LINE_BYTES=8*1024*1024
_MAX_ROWS=100_000
_KEYS={"schema_version","split_method","dataset_sha256","split_seed","validation_fraction","test_fraction","split_ids","sha256"}

@dataclass(frozen=True)
class VerifiedSplitManifest:
    dataset_sha256:str
    split_manifest_sha256:str
    split_seed:int
    split_counts:dict[str,int]
    selected_example_count:int
    dataset_example_count:int

def _strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError(f"duplicate JSON key: {key}")
        result[key]=value
    return result

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _valid_hash(value):
    return isinstance(value,str) and _SHA.fullmatch(value) is not None

def _validate_parameters(seed,val,test):
    if isinstance(seed,bool) or not isinstance(seed,int): raise TypeError("split_seed must be an integer")
    if not -(2**63)<=seed<2**63: raise ValueError("split_seed must fit signed 64-bit range")
    for name,value in (("validation_fraction",val),("test_fraction",test)):
        if isinstance(value,bool) or not isinstance(value,(int,float)): raise TypeError(f"{name} must be finite")
        if not math.isfinite(value) or not 0.0<value<1.0: raise ValueError(f"{name} must be in (0, 1)")
    if val+test>=1.0: raise ValueError("validation_fraction + test_fraction must be less than 1")

def _read_dataset(path, *, selected_ids=None, include_full_rows=False, row_callback=None, resource_limits=None):
    """Verify the dataset and retain only the row data needed by the caller.

    The semantic verifier remains authoritative. This second bounded pass binds
    returned rows to the verified digest and detects changes between passes.
    Split validation retains only (example_id, input_text); row loaders may
    request full records, optionally filtered to one verified split.
    """
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"dataset file not found: {path}")
    before = path.stat()
    if before.st_size > resource_limits.max_dataset_bytes:
        raise ValueError("dataset exceeds configured max_dataset_bytes")
    manifest = verify_dataset(
        path,
        max_bytes=resource_limits.max_dataset_bytes,
        max_rows=resource_limits.max_rows,
        max_line_bytes=resource_limits.max_line_bytes,
        max_manifest_bytes=resource_limits.max_dataset_manifest_bytes,
    )
    digest_expected = manifest.get("sha256")
    if not _valid_hash(digest_expected):
        raise ValueError("verified dataset SHA-256 is invalid")

    selected = None if selected_ids is None else (selected_ids if isinstance(selected_ids, (set, frozenset, dict)) else set(selected_ids))
    digest = hashlib.sha256()
    rows = []
    bytes_seen = 0
    rows_seen = 0
    try:
        with path.open("rb") as stream:
            while True:
                line = stream.readline(resource_limits.max_line_bytes + 1)
                if not line:
                    break
                rows_seen += 1
                if rows_seen > resource_limits.max_rows or rows_seen > manifest["example_count"]:
                    raise ValueError("dataset row count exceeds verified manifest or preflight limit")
                if len(line) > resource_limits.max_line_bytes:
                    raise ValueError("dataset JSONL row exceeds configured max_line_bytes")
                bytes_seen += len(line)
                if bytes_seen > resource_limits.max_dataset_bytes:
                    raise ValueError("dataset exceeds configured max_dataset_bytes")
                digest.update(line)
                if not line.endswith(b"\n"):
                    raise ValueError("dataset JSONL must end with a newline")
                encoded = line[:-1]
                if not encoded:
                    raise ValueError("dataset JSONL contains blank rows")
                try:
                    row = json.loads(
                        encoded.decode("utf-8"),
                        object_pairs_hook=_strict_object,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    raise ValueError("dataset JSONL malformed or contains duplicate keys") from exc
                example_id = row.get("example_id") if isinstance(row, dict) else None
                if selected is not None and example_id not in selected:
                    continue
                if row_callback is not None:
                    row_callback(row)
                elif include_full_rows:
                    rows.append(row)
                else:
                    rows.append((row["input_text"], example_id))
    except OSError as exc:
        raise ValueError("dataset could not be read safely after verification") from exc

    after = path.stat()
    if (bytes_seen != before.st_size or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
            or digest.hexdigest() != digest_expected):
        raise ValueError("dataset changed while being read")
    if rows_seen != manifest["example_count"]:
        raise ValueError("dataset row count changed after verification")
    if selected is not None and len(rows) != len(selected):
        raise ValueError("split manifest references missing dataset rows")
    return manifest, rows

def _derive_split_ids(dataset_path, seed, val, test, *, resource_limits=None):
    """Build prompt-group split metadata using a bounded disk-backed index."""
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    with tempfile.TemporaryDirectory(prefix="ultron-split-index-") as temp_dir:
        db_path = Path(temp_dir) / "prompt-groups.sqlite3"
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("PRAGMA temp_store=FILE")
            connection.execute(f"PRAGMA cache_size=-{resource_limits.sqlite_cache_kib}")
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            index_budget = min(
                resource_limits.max_index_bytes,
                resource_limits.max_temporary_bytes,
            )
            if index_budget < page_size:
                raise ValueError("split-index temporary budget cannot hold one SQLite page")
            connection.execute(f"PRAGMA max_page_count={index_budget // page_size}")
            connection.execute(
                "CREATE TABLE prompt_groups (prompt TEXT PRIMARY KEY, example_id TEXT NOT NULL) WITHOUT ROWID"
            )

            def retain_prompt(row):
                prompt = " ".join(row["input_text"].split())
                connection.execute(
                    "INSERT INTO prompt_groups(prompt, example_id) VALUES (?, ?) "
                    "ON CONFLICT(prompt) DO UPDATE SET example_id = "
                    "MIN(prompt_groups.example_id, excluded.example_id)",
                    (prompt, row["example_id"]),
                )

            manifest, _ = _read_dataset(
                dataset_path, row_callback=retain_prompt, resource_limits=resource_limits
            )
            connection.commit()
            index_bytes = db_path.stat().st_size
            if index_bytes > resource_limits.max_index_bytes or index_bytes > resource_limits.max_temporary_bytes:
                raise ValueError("split index exceeds configured disk budget")
            unique_prompts = connection.execute(
                "SELECT COUNT(*) FROM prompt_groups"
            ).fetchone()[0]
            if unique_prompts < 3:
                raise ValueError("at least three unique normalized prompts are required")

            result = {"train": [], "validation": [], "test": []}
            cursor = connection.execute(
                "SELECT prompt, example_id FROM prompt_groups ORDER BY prompt"
            )
            for prompt, example_id in cursor:
                digest = hashlib.sha256(
                    f"ultron-split-v1\0{seed}\0{prompt}".encode("utf-8")
                ).digest()
                bucket = int.from_bytes(digest[:8], "big") / 2**64
                name = "test" if bucket < test else "validation" if bucket < test + val else "train"
                result[name].append(example_id)
            if any(not result[name] for name in result):
                raise ValueError("split parameters produced an empty split")
            return manifest, {name: sorted(ids) for name, ids in result.items()}
        finally:
            connection.close()


def prepare_dataset_split_manifest(dataset_path,output_path,*,split_seed=0,validation_fraction=0.1,test_fraction=0.1,resource_limits=None):
    """Verify an existing dataset and atomically write split-ID metadata only."""
    _validate_parameters(split_seed,validation_fraction,test_fraction)
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    dataset=Path(dataset_path).resolve(); output=Path(output_path).resolve()
    if output in (dataset,dataset.with_suffix(dataset.suffix+".manifest.json")):
        raise ValueError("split manifest output must not overwrite dataset or sidecar")
    manifest, split_ids = _derive_split_ids(
        dataset, split_seed, validation_fraction, test_fraction,
        resource_limits=resource_limits,
    )
    payload={"schema_version":1,"split_method":_METHOD,"dataset_sha256":manifest["sha256"],
             "split_seed":split_seed,"validation_fraction":float(validation_fraction),
             "test_fraction":float(test_fraction),"split_ids":split_ids}
    payload["sha256"]=hashlib.sha256(_canonical(payload)).hexdigest()
    encoded=_canonical(payload)+b"\n"
    if len(encoded)>resource_limits.max_split_manifest_bytes: raise ValueError("split manifest exceeds configured max_split_manifest_bytes")
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{output.name}.",suffix=".tmp",dir=output.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,output)
    finally:
        if os.path.exists(name): os.unlink(name)
    return validate_dataset_split_manifest(dataset,output,resource_limits=resource_limits)

def validate_dataset_split_manifest(dataset_path,split_manifest_path,*,resource_limits=None):
    """Validate dataset bytes, canonical split digest, exact membership, and prompt-disjointness."""
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    path=Path(split_manifest_path)
    if not path.is_file(): raise FileNotFoundError(f"split manifest not found: {path}")
    try:
        with path.open("rb") as stream:
            raw = stream.read(resource_limits.max_split_manifest_bytes + 1)
    except OSError as exc:
        raise ValueError("split manifest could not be read safely") from exc
    if len(raw) > resource_limits.max_split_manifest_bytes:
        raise ValueError("split manifest exceeds configured max_split_manifest_bytes")
    try: payload=json.loads(raw.decode("utf-8"),object_pairs_hook=_strict_object)
    except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc:
        raise ValueError("split manifest malformed or contains duplicate keys") from exc
    if not isinstance(payload,dict) or set(payload)!=_KEYS: raise ValueError("split manifest schema invalid")
    version=payload["schema_version"]
    if isinstance(version,bool) or not isinstance(version,int) or version!=1: raise ValueError("unsupported split schema")
    if payload["split_method"]!=_METHOD: raise ValueError("unsupported split method")
    seed=payload["split_seed"]; val=payload["validation_fraction"]; test=payload["test_fraction"]
    _validate_parameters(seed,val,test)
    saved=payload["sha256"]
    if not _valid_hash(saved): raise ValueError("split manifest SHA-256 malformed")
    unsigned={k:v for k,v in payload.items() if k!="sha256"}
    if hashlib.sha256(_canonical(unsigned)).hexdigest()!=saved: raise ValueError("split manifest SHA-256 mismatch")
    split_ids=payload["split_ids"]
    if not isinstance(split_ids,dict) or set(split_ids)!={"train","validation","test"}: raise ValueError("split IDs schema invalid")
    for name,ids in split_ids.items():
        if not isinstance(ids,list) or any(not _valid_hash(item) for item in ids): raise ValueError(f"{name} IDs invalid")
        if ids!=sorted(ids) or len(ids)!=len(set(ids)): raise ValueError(f"{name} IDs must be sorted and unique")
    manifest, expected = _derive_split_ids(
        dataset_path, seed, val, test, resource_limits=resource_limits
    )
    if payload["dataset_sha256"]!=manifest["sha256"]: raise ValueError("split manifest belongs to another dataset")
    if split_ids!=expected: raise ValueError("split membership differs from deterministic prompt-group assignment")
    all_ids=[item for ids in split_ids.values() for item in ids]
    if len(all_ids)!=len(set(all_ids)): raise ValueError("split IDs overlap")
    return VerifiedSplitManifest(manifest["sha256"],saved,seed,{k:len(v) for k,v in split_ids.items()},len(all_ids),manifest["example_count"])


def _read_bound_split_payload(split_manifest_path, verified, *, resource_limits=None):
    """Read the exact split-manifest snapshot already validated by digest."""
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    path = Path(split_manifest_path)
    try:
        if not path.is_file():
            raise FileNotFoundError(f"split manifest not found: {path}")
        with path.open("rb") as stream:
            raw = stream.read(resource_limits.max_split_manifest_bytes + 1)
    except OSError as exc:
        raise ValueError("split manifest could not be re-read safely") from exc
    if len(raw) > resource_limits.max_split_manifest_bytes:
        raise ValueError("split manifest exceeds configured max_split_manifest_bytes")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("split manifest malformed or contains duplicate keys") from exc
    if not isinstance(payload, dict) or set(payload) != _KEYS:
        raise ValueError("split manifest changed between validation and row loading")
    saved_digest = payload.get("sha256")
    unsigned = {key: value for key, value in payload.items() if key != "sha256"}
    if (saved_digest != verified.split_manifest_sha256
            or not _valid_hash(saved_digest)
            or hashlib.sha256(_canonical(unsigned)).hexdigest() != saved_digest
            or payload.get("dataset_sha256") != verified.dataset_sha256):
        raise ValueError("split manifest changed between validation and row loading")
    split_ids = payload.get("split_ids")
    if not isinstance(split_ids, dict) or set(split_ids) != {"train", "validation", "test"}:
        raise ValueError("split manifest changed between validation and row loading")
    return payload


def load_verified_split_rows(dataset_path, split_manifest_path, *, split_name, resource_limits=None):
    """Return full records for one split only, bound to verified digests."""
    if split_name not in ("train", "validation", "test"):
        raise ValueError("split_name must be train, validation, or test")
    resource_limits = resource_limits or DatasetResourceLimits()
    verified = validate_dataset_split_manifest(
        dataset_path, split_manifest_path, resource_limits=resource_limits
    )
    payload = _read_bound_split_payload(
        split_manifest_path, verified, resource_limits=resource_limits
    )
    wanted = set(payload["split_ids"][split_name])
    dataset_manifest, selected = _read_dataset(
        dataset_path, selected_ids=wanted, include_full_rows=True,
        resource_limits=resource_limits,
    )
    if dataset_manifest["sha256"] != verified.dataset_sha256:
        raise ValueError("dataset changed between split validation and row loading")
    selected.sort(key=lambda row: row["example_id"])
    return verified, tuple(selected)


def load_verified_split_rows_by_split(dataset_path, split_manifest_path, *, resource_limits=None):
    """Load all verified split records from one consistent dataset snapshot.

    Validation retains only example IDs and normalized prompt text. The second
    pass retains full row objects only for split IDs and groups them directly,
    avoiding an additional full-dataset ID-to-row dictionary.
    """
    resource_limits = resource_limits or DatasetResourceLimits()
    verified = validate_dataset_split_manifest(
        dataset_path, split_manifest_path, resource_limits=resource_limits
    )
    payload = _read_bound_split_payload(
        split_manifest_path, verified, resource_limits=resource_limits
    )
    split_ids = payload["split_ids"]
    split_for_id = {}
    for split_name in ("train", "validation", "test"):
        ids = split_ids[split_name]
        if not isinstance(ids, list):
            raise ValueError(f"{split_name} split IDs are malformed")
        for example_id in ids:
            if example_id in split_for_id:
                raise ValueError("split IDs overlap")
            split_for_id[example_id] = split_name

    dataset_manifest, rows = _read_dataset(
        dataset_path, selected_ids=split_for_id, include_full_rows=True,
        resource_limits=resource_limits,
    )
    if dataset_manifest["sha256"] != verified.dataset_sha256:
        raise ValueError("dataset changed between split validation and row loading")

    result = {"train": [], "validation": [], "test": []}
    for row in rows:
        split_name = split_for_id.get(row["example_id"])
        if split_name is None:
            raise ValueError("split manifest references an unknown dataset row")
        result[split_name].append(row)
    for split_name in result:
        if len(result[split_name]) != len(split_ids[split_name]):
            raise ValueError("split manifest references missing dataset rows")
        result[split_name].sort(key=lambda row: row["example_id"])
        result[split_name] = tuple(result[split_name])
    return verified, result
