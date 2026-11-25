"""Stage B topic expansion readiness contract; no data/model execution."""
from __future__ import annotations
import re
from typing import Mapping

STAGE_B_TOPICS=("geometry","trigonometry","probability","statistics","linear_algebra","number_theory")
_SHA256=re.compile(r"^[0-9a-f]{64}$")
_FIELDS=("topic","generator_id","verifier_id","benchmark_id","benchmark_sha256","split_sha256","held_out_examples","generator_independently_validated","verifier_independently_tested","baseline_model","baseline_results_sha256")

def validate_stage_b_manifest(manifest: Mapping) -> dict:
    """Check preregistration metadata; this does not audit referenced artifacts."""
    if not isinstance(manifest,Mapping): raise TypeError("manifest must be a mapping")
    if manifest.get("schema_version")!=1: raise ValueError("schema_version must be 1")
    entries=manifest.get("topics")
    if not isinstance(entries,list): raise ValueError("topics must be a list")
    seen=set(); rows={}; blockers=[]
    for i,entry in enumerate(entries):
        if not isinstance(entry,Mapping):
            blockers.append(f"topics[{i}] must be a mapping"); continue
        topic=entry.get("topic")
        if topic not in STAGE_B_TOPICS:
            blockers.append(f"topics[{i}] has unsupported Stage B topic"); continue
        if topic in seen:
            blockers.append(f"duplicate topic: {topic}"); continue
        seen.add(topic); missing=[f for f in _FIELDS if f not in entry]
        issues=[f"missing {f}" for f in missing]
        for field in ("generator_id","verifier_id","benchmark_id","baseline_model"):
            if field not in missing and (not isinstance(entry[field],str) or not entry[field].strip()):
                issues.append(f"{field} must be non-empty")
        for field in ("benchmark_sha256","split_sha256","baseline_results_sha256"):
            if field not in missing and (not isinstance(entry[field],str) or not _SHA256.fullmatch(entry[field])):
                issues.append(f"{field} must be a lowercase SHA-256")
        count=entry.get("held_out_examples")
        if "held_out_examples" not in missing and (isinstance(count,bool) or not isinstance(count,int) or count<200):
            issues.append("held_out_examples must be at least 200")
        for field in ("generator_independently_validated","verifier_independently_tested"):
            if field not in missing and entry[field] is not True: issues.append(f"{field} must be true")
        if entry.get("baseline_model")!="Fable 5.2": issues.append("baseline_model must identify Fable 5.2")
        rows[topic]={"ready":not issues,"blockers":issues}
        blockers.extend(f"{topic}: {issue}" for issue in issues)
    for topic in STAGE_B_TOPICS:
        if topic not in seen: blockers.append(f"missing Stage B topic: {topic}")
    return {"schema_version":1,"stage":"B","required_topics":list(STAGE_B_TOPICS),
            "topic_count":len(STAGE_B_TOPICS),"provided_topic_count":len(seen),
            "ready":not blockers,"per_topic":rows,"blockers":blockers,
            "data_generated":False,"model_invoked":False,"training_performed":False,
            "external_ai_api_used":False}
