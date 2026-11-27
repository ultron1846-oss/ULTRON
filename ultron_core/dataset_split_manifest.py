"""Verify existing ULTRON data and prepare metadata-only deterministic splits."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, math, os, re, tempfile
from pathlib import Path
from .data_generation import verify_dataset

_METHOD="prompt_group_hash_v1"
_SHA=re.compile(r"[0-9a-f]{64}")
_MAX_SPLIT=32*1024*1024
_MAX_DATA=1024*1024*1024
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

def _read_dataset(path):
    path=Path(path)
    if not path.is_file(): raise FileNotFoundError(f"dataset file not found: {path}")
    if path.stat().st_size>_MAX_DATA: raise ValueError("dataset exceeds the 1 GiB preflight limit")
    manifest=verify_dataset(path)
    digest=manifest.get("sha256")
    if not _valid_hash(digest): raise ValueError("verified dataset SHA-256 is invalid")
    content=path.read_bytes()
    if hashlib.sha256(content).hexdigest()!=digest: raise ValueError("dataset changed while being read")
    try:
        rows=[json.loads(line,object_pairs_hook=_strict_object) for line in content.decode("utf-8").splitlines()]
    except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc:
        raise ValueError("dataset JSONL malformed or contains duplicate keys") from exc
    if len(rows)!=manifest["example_count"]: raise ValueError("dataset row count changed after verification")
    return manifest,rows

def _expected(rows,seed,val,test):
    groups={}
    for row in rows:
        prompt=" ".join(row["input_text"].split())
        old=groups.get(prompt)
        if old is None or row["example_id"]<old: groups[prompt]=row["example_id"]
    if len(groups)<3: raise ValueError("at least three unique normalized prompts are required")
    result={"train":[],"validation":[],"test":[]}
    for prompt,example_id in sorted(groups.items()):
        digest=hashlib.sha256(f"ultron-split-v1\0{seed}\0{prompt}".encode("utf-8")).digest()
        bucket=int.from_bytes(digest[:8],"big")/2**64
        name="test" if bucket<test else "validation" if bucket<test+val else "train"
        result[name].append(example_id)
    if any(not result[name] for name in result): raise ValueError("split parameters produced an empty split")
    return {name:sorted(ids) for name,ids in result.items()}

def prepare_dataset_split_manifest(dataset_path,output_path,*,split_seed=0,validation_fraction=0.1,test_fraction=0.1):
    """Verify an existing dataset and atomically write split-ID metadata only."""
    _validate_parameters(split_seed,validation_fraction,test_fraction)
    dataset=Path(dataset_path).resolve(); output=Path(output_path).resolve()
    if output in (dataset,dataset.with_suffix(dataset.suffix+".manifest.json")):
        raise ValueError("split manifest output must not overwrite dataset or sidecar")
    manifest,rows=_read_dataset(dataset)
    payload={"schema_version":1,"split_method":_METHOD,"dataset_sha256":manifest["sha256"],
             "split_seed":split_seed,"validation_fraction":float(validation_fraction),
             "test_fraction":float(test_fraction),
             "split_ids":_expected(rows,split_seed,validation_fraction,test_fraction)}
    payload["sha256"]=hashlib.sha256(_canonical(payload)).hexdigest()
    encoded=_canonical(payload)+b"\n"
    if len(encoded)>_MAX_SPLIT: raise ValueError("split manifest exceeds 32 MiB")
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=f".{output.name}.",suffix=".tmp",dir=output.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
        os.replace(name,output)
    finally:
        if os.path.exists(name): os.unlink(name)
    return validate_dataset_split_manifest(dataset,output)

def validate_dataset_split_manifest(dataset_path,split_manifest_path):
    """Validate dataset bytes, canonical split digest, exact membership, and prompt-disjointness."""
    manifest,rows=_read_dataset(dataset_path)
    path=Path(split_manifest_path)
    if not path.is_file(): raise FileNotFoundError(f"split manifest not found: {path}")
    raw=path.read_bytes()
    if len(raw)>_MAX_SPLIT: raise ValueError("split manifest exceeds 32 MiB")
    try: payload=json.loads(raw.decode("utf-8"),object_pairs_hook=_strict_object)
    except (UnicodeDecodeError,json.JSONDecodeError,ValueError) as exc:
        raise ValueError("split manifest malformed or contains duplicate keys") from exc
    if not isinstance(payload,dict) or set(payload)!=_KEYS: raise ValueError("split manifest schema invalid")
    version=payload["schema_version"]
    if isinstance(version,bool) or not isinstance(version,int) or version!=1: raise ValueError("unsupported split schema")
    if payload["split_method"]!=_METHOD: raise ValueError("unsupported split method")
    if payload["dataset_sha256"]!=manifest["sha256"]: raise ValueError("split manifest belongs to another dataset")
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
    expected=_expected(rows,seed,val,test)
    if split_ids!=expected: raise ValueError("split membership differs from deterministic prompt-group assignment")
    all_ids=[item for ids in split_ids.values() for item in ids]
    if len(all_ids)!=len(set(all_ids)): raise ValueError("split IDs overlap")
    return VerifiedSplitManifest(manifest["sha256"],saved,seed,{k:len(v) for k,v in split_ids.items()},len(all_ids),manifest["example_count"])


def load_verified_split_rows(dataset_path, split_manifest_path, *, split_name):
    """Return selected verified records and binding metadata; never writes data."""
    if split_name not in ("train", "validation", "test"):
        raise ValueError("split_name must be train, validation, or test")
    verified = validate_dataset_split_manifest(dataset_path, split_manifest_path)
    _, rows = _read_dataset(dataset_path)
    try:
        payload = json.loads(
            Path(split_manifest_path).read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("split manifest could not be re-read safely") from exc
    wanted = set(payload["split_ids"][split_name])
    selected = [row for row in rows if row["example_id"] in wanted]
    if len(selected) != len(wanted):
        raise ValueError("split manifest references missing dataset rows")
    selected.sort(key=lambda row: row["example_id"])
    return verified, tuple(selected)
