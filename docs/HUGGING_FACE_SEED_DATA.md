# Hugging Face seed-data import

ULTRON's source registry lists:

- [MetaMathQA](https://huggingface.co/datasets/meta-math/MetaMathQA): 395,000 rows; dataset card license MIT.
- [MathInstruct](https://huggingface.co/datasets/TIGER-Lab/MathInstruct): 262,039 rows; constituent-source licenses vary.

Raw total: approximately 657,039 rows. Accepted counts will be lower after source/license filtering, code/tool-output rejection, length checks, and exact question deduplication.

## Import (not training)

Install optional dependencies with:

    pip install -e ".[seed-data]"

After reviewing the dataset cards and allowlist, explicitly run:

    python -m tools.hf_seed_data.importer --confirm-download --output-dir data/hf_seed

A bounded smoke import can use --max-rows 100. This still fetches dataset rows and requires --confirm-download.

The importer resolves Hub revisions to commit SHAs, streams the train split, normalizes the known columns, retains source/license/revision and hashes, rejects obvious code/PoT/tool targets, collapses exact normalized-question duplicates, and creates deterministic 98/1/1 train/validation/test splits. It writes JSONL and a manifest with actual counts and SHA-256 hashes. Raw datasets are not committed to Git.

## License and contamination safeguards

MathInstruct's source allowlist is intentionally narrow: AQuA-RAT (Apache-2.0), GSM8K/MATH/TheoremQA (MIT), NumGLUE/MathQA (Apache-2.0), and the curated MIT source. GSM8K-RFT, Camel-Math, program-of-thought sources, and unknown source names are excluded by default. This technical allowlist is not legal advice; review source terms before expanding it.

MetaMathQA's card says its examples are augmented from GSM8K and MATH training sets. Keep final evaluation separate and run benchmark contamination checks against original benchmark questions/answers before training. Imported examples are not evidence of ULTRON's independent capability.

The importer does not call ULTRON commands, derive targets from calculator/solver outputs, or start training. Its manifest marks training authorization false. Training requires separate explicit authorization.


## Concept-first learning (required before training)

The corpora are **examples**, not a list of facts ULTRON should memorize. The future training pipeline must organize examples around reusable mathematical ideas and relationships:

- Map each example, when feasible, to concept/skill IDs and prerequisites.
- Preserve the mathematical principle and derivation, including assumptions and conditions; do not reduce the target to a final answer alone.
- Build varied examples of the same concept across wording, values, representations, and contexts. Add contrastive pairs where a changed condition changes the valid method or conclusion.
- Curate concept clusters and sample across them, rather than repeatedly exposing nearly identical question/answer records.
- Reserve unseen-value/unseen-wording and combined-concept tasks for held-out transfer evaluation. Measure by concept, transfer, and exact-overlap/memorization checks separately.
- Never mark a concept as learned just because its source examples were imported. Model-only transfer performance is the evidence; tool-assisted scores are separate.

Concept annotation may be incomplete or uncertain. Preserve the source record and provenance, and do not invent verified labels. No command tool may replace ULTRON's own attempt or silently produce its training target. This requirement is part of the training-readiness gate; it does not authorize training.


## Workflow safety gate

The GitHub Actions importer is manual-only and skipped unless the dispatch input confirm_download is true and the repository variable ULTRON_SEED_IMPORT_ENABLED is explicitly set to true. The variable is intentionally absent by default. Do not enable it or dispatch this workflow without separate explicit authorization for external dataset download/curation. Ordinary PR tests use mocked clients and never contact Hugging Face.


## Basic arithmetic seed source

The registry now includes the MIT-licensed [ChrisMcCormick/basic-arithmetic](https://huggingface.co/datasets/ChrisMcCormick/basic-arithmetic) dataset as a separate foundation arithmetic source. Only its **10,000-row train split** is configured; validation and test splits are never imported. The source card lists addition, subtraction, multiplication, and division and includes answer-only records.

The importer independently checks each accepted row against its integer operands and operation, requires exact integer division (rejecting zero divisors and non-integer quotients), rejects mismatched answers and unsupported operations, and limits each operand to absolute value 10,000. Accepted records are marked `target_kind: answer_only` so they are not misrepresented as worked reasoning. This is a small foundational arithmetic source, not a complete reasoning corpus.

Import remains behind the manual workflow and owner-controlled repository-variable gate. This PR adds source support only; it does not download or publish dataset rows and does not start training.
