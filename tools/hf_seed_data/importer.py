"""Import/curate approved Hugging Face math seed sources; never trains a model."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("config.json")

def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def normalize_source_name(value: Any) -> str:
    raw = normalize_text(value).lower().replace("\\", "/")
    raw = raw.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]+", "_", raw).strip("_")

def contains_program_or_tool_output(answer: str, source: str = "") -> bool:
    source_lower = source.lower().replace("\\", "/")
    if "/pot/" in source_lower or "program-of-thought" in source_lower:
        return True
    patterns = (
        r"\x60{3}\s*(python|py|javascript|js|bash|sh)\b",
        r"\b(import\s+\w+|def\s+\w+\s*\(|print\s*\()",
        r"\b(code|program)\s+(output|result|execution)\b",
        r"let's program in (python|the response)",
        r"\b(tool|calculator)\s+(returned|output|result)\b",
    )
    return any(re.search(pattern, answer, re.IGNORECASE) for pattern in patterns)

def mathinstruct_license(source: Any, config: dict[str, Any]) -> str | None:
    raw_source = normalize_text(source).lower().replace("\\", "/")
    source_name = normalize_source_name(source)
    denied = {normalize_source_name(x) for x in config["mathinstruct_source_denylist"]}
    if "/pot/" in raw_source or "program-of-thought" in raw_source:
        return None
    if source_name in denied or "pot" in source_name:
        return None
    for allowed_name, license_name in config["mathinstruct_source_license_allowlist"].items():
        allowed = normalize_source_name(allowed_name)
        if source_name == allowed or source_name.startswith(allowed + "_"):
            return license_name
    return None

def normalize_row(dataset_id: str, row: dict[str, Any], index: int,
                  revision: str, config: dict[str, Any]) -> dict[str, Any] | None:
    if dataset_id == "metamathqa":
        question, answer = normalize_text(row.get("query")), normalize_text(row.get("response"))
        source_name = "MetaMathQA:" + (normalize_text(row.get("type")) or "unknown")
        license_name = "MIT"
    elif dataset_id == "mathinstruct":
        question, answer = normalize_text(row.get("instruction")), normalize_text(row.get("output"))
        raw_source = row.get("source")
        license_name = mathinstruct_license(raw_source, config)
        if license_name is None or contains_program_or_tool_output(answer, normalize_text(raw_source)):
            return None
        source_name = normalize_text(raw_source)
    else:
        raise ValueError("Unsupported configured dataset: " + dataset_id)

    limits = config["limits"]
    if not question or not answer:
        return None
    if len(question) > limits["max_question_chars"] or len(answer) > limits["max_answer_chars"]:
        return None
    if contains_program_or_tool_output(answer, source_name):
        return None
    qhash = sha256_text(normalize_text(question).lower())
    record_id = normalize_text(row.get("id")) or sha256_text(f"{dataset_id}:{index}:{qhash}")
    return {
        "schema_version": 1, "record_id": record_id, "question": question,
        "reasoning_answer": answer, "dataset_id": dataset_id,
        "dataset_repo": "meta-math/MetaMathQA" if dataset_id == "metamathqa" else "TIGER-Lab/MathInstruct",
        "dataset_revision": revision, "source": source_name, "source_license": license_name,
        "question_sha256": qhash, "answer_sha256": sha256_text(answer),
    }

def split_for_question(question_hash: str, config: dict[str, Any]) -> str:
    byte_value = int(question_hash[:2], 16)
    cfg = config["split"]
    validation_cutoff = round(256 * cfg["validation_percent"] / 100)
    test_cutoff = validation_cutoff + round(256 * cfg["test_percent"] / 100)
    if byte_value < validation_cutoff:
        return "validation"
    if byte_value < test_cutoff:
        return "test"
    return "train"

def import_sources(output_dir: Path, max_rows: int | None = None) -> dict[str, Any]:
    """Mockable streaming importer that publishes only a complete output set."""
    try:
        from datasets import load_dataset
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("Install optional dependencies with: pip install -e .[seed-data]") from exc

    config = load_config()
    output_dir = Path(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    seen_questions: set[str] = set()
    stats: dict[str, Any] = {}
    counts = {"train": 0, "validation": 0, "test": 0}
    rejected = {"license_or_program_filter": 0, "duplicate": 0}

    with tempfile.TemporaryDirectory(prefix=".ultron-seed-stage-", dir=output_dir.parent) as temp_dir:
        stage = Path(temp_dir)
        paths = {name: stage / (name + ".jsonl") for name in counts}
        handles = {name: path.open("w", encoding="utf-8") for name, path in paths.items()}
        try:
            processed = 0
            for source_cfg in config["sources"]:
                if not source_cfg.get("allowed"):
                    continue
                repo_id = source_cfg["repo_id"]
                revision = api.dataset_info(repo_id, revision=source_cfg["revision"]).sha
                dataset = load_dataset(
                    repo_id, split=source_cfg["split"], streaming=True, revision=revision
                )
                accepted = 0
                seen = 0
                for row in dataset:
                    if max_rows is not None and processed >= max_rows:
                        break
                    processed += 1
                    seen += 1
                    record = normalize_row(
                        source_cfg["id"], dict(row), processed - 1, revision, config
                    )
                    if record is None:
                        rejected["license_or_program_filter"] += 1
                        continue
                    qhash = record["question_sha256"]
                    if qhash in seen_questions:
                        rejected["duplicate"] += 1
                        continue
                    seen_questions.add(qhash)
                    split_name = split_for_question(qhash, config)
                    handles[split_name].write(
                        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                    )
                    counts[split_name] += 1
                    accepted += 1
                stats[source_cfg["id"]] = {
                    "repo_id": repo_id,
                    "revision": revision,
                    "expected_rows": source_cfg["expected_rows"],
                    "seen_rows": seen,
                    "accepted_rows": accepted,
                }
                if max_rows is not None and processed >= max_rows:
                    break
        finally:
            for handle in handles.values():
                handle.close()

        hashes = {}
        for name, path in paths.items():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            hashes[path.name] = digest.hexdigest()

        manifest = {
            "schema_version": 1,
            "sources": stats,
            "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
            "split_counts": counts,
            "rejected_counts": rejected,
            "unique_accepted_rows": sum(counts.values()),
            "files_sha256": hashes,
            "data_is_training_authorized": False,
            "note": "Import/curation only. Final license review and benchmark contamination checks remain required.",
        }
        (stage / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        backup = None
        if output_dir.exists():
            backup = Path(tempfile.mkdtemp(prefix=".ultron-seed-backup-", dir=output_dir.parent))
            backup.rmdir()
            output_dir.replace(backup)
        try:
            stage.replace(output_dir)
        except Exception:
            if backup is not None and backup.exists() and not output_dir.exists():
                backup.replace(output_dir)
            raise
        if backup is not None:
            shutil.rmtree(backup)

    return manifest

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/hf_seed"))
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--confirm-download", action="store_true",
        help="Required to fetch and curate the large Hugging Face datasets.")
    args = parser.parse_args()
    if not args.confirm_download:
        parser.error("This fetches external data. Review source cards, then pass --confirm-download.")
    if args.max_rows is not None and args.max_rows < 1:
        parser.error("--max-rows must be positive")
    print(json.dumps(import_sources(args.output_dir, args.max_rows), indent=2))

if __name__ == "__main__":
    main()
