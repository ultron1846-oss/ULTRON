"""Validated, local retrieval over ULTRON's curated starter knowledge bank."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_PATH = Path(__file__).with_name("data") / "knowledge_bank.json"


def load_knowledge_bank(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path is not None else _DEFAULT_PATH
    with source.open("r", encoding="utf-8") as handle:
        bank = json.load(handle)
    entries = bank.get("entries")
    if not isinstance(entries, list) or bank.get("entry_count") != len(entries):
        raise ValueError("knowledge bank entry_count does not match entries")
    ids = [entry.get("id") for entry in entries]
    if any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("every knowledge entry must have a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("knowledge bank contains duplicate IDs")
    required = {"subject", "level", "kind", "statement", "verification_status"}
    for entry in entries:
        if not required.issubset(entry) or not all(isinstance(entry[key], str) for key in required):
            raise ValueError(f"malformed knowledge entry: {entry.get('id')}")
    return bank


def search_knowledge(query: str, subject: str | None = None, level: str | None = None,
                    limit: int = 5, path: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("limit must be an integer from 1 to 20")
    bank = load_knowledge_bank(path)
    terms = [term.lower() for term in query.split() if term.strip()]
    results = []
    for entry in bank["entries"]:
        if subject and subject.lower() not in entry["subject"].lower():
            continue
        if level and level.lower() not in entry["level"].lower():
            continue
        statement = entry["statement"].lower()
        haystack = (statement + " " + entry["subject"] + " " + entry["level"] + " " + entry["kind"]).lower()
        score = sum(2 if term in statement else 1 for term in terms if term in haystack)
        if score:
            results.append((score, entry))
    results.sort(key=lambda item: (-item[0], item[1]["id"]))
    return {
        "tool": "knowledge_search",
        "status": "results" if results else "no_match",
        "query": query,
        "total_entries": bank["entry_count"],
        "results": [entry for _, entry in results[:limit]],
        "notice": bank["notice"],
    }


def run_knowledge_search(arguments: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise TypeError("tool arguments must be an object")
    allowed = {"query", "subject", "level", "limit"}
    extra = set(arguments) - allowed
    if extra:
        raise ValueError("unknown argument(s): " + ", ".join(sorted(extra)))
    return search_knowledge(arguments.get("query", ""), subject=arguments.get("subject"),
                            level=arguments.get("level"), limit=arguments.get("limit", 5))
