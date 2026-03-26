# Proofreader Pipeline

Automated proofreading pipeline for CSAS/DFO translated documents. Runs 5 sequential steps, producing a checkpoint `.docx` with tracked changes at each stage.

## Requirements

- Python 3.12+
- `python-docx`, `lxml` (already in project dependencies)

## Usage

Files are expected in `data/_PROOFREADING/` by default (override with `--review-dir`). The original and its translation must both be present:
- `1432_en.docx` (original)
- `1432_en_translated.docx` (translation to review)

### Workflow

The pipeline pauses at each LLM step to let you paste the prompt into Claude (claude.ai) and save the response.

```bash
# 1. Run steps 1-2 (deterministic) and generate the step 3 prompt
python scripts/run_proofreader_pipeline.py 1432_en.docx

# 2. Paste the prompt (copied to clipboard) into Claude.
#    Save Claude's JSON response to the path printed by the script.

# 3. Apply step 3 response and generate the step 4 prompt
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 3

# 4. Paste prompt into Claude, save response, then:
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 4

# 5. Paste prompt into Claude, save response, then:
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 5
```

## Pipeline Steps

Each step produces a checkpoint file. Suffixes replace each other, not accumulate:

| Step | Output suffix | Type | Description |
|------|--------------|------|-------------|
| 1 | `_lexical_checklist.json` | Auto | Scans original doc for glossary terms, builds location checklist |
| 2 | `_fix_formatting.docx` | Auto | Glossary replacements + punctuation fixes (tracked changes) |
| 3 | `_proofreading.docx` | LLM | Translation accuracy review |
| 4 | `_lexical_constraints.docx` | LLM | Verifies preferred terminology from step 1 checklist |
| 5 | `_recommended_updates.docx` | LLM | Final punctuation pass + grammar review |

For LLM steps, the script generates a `_stepN_prompt.md` file and expects you to save the response as `_stepN_response.json` in the same directory.

## Running Individual Steps

Each step is an importable function in `scripts/run_proofreader_pipeline.py`:

```python
from scripts.run_proofreader_pipeline import step1_lexical_checklist, step2_fix_formatting
```

The existing `scripts/run_proofreader.py` helper functions (`run_fix_formatting`, `run_apply_review`, `run_build_prompt`) still work for standalone use.

## Module Structure

| File | Purpose |
|------|---------|
| `extract_text.py` | Extract text with location IDs (`[P0]`, `[T0-R0]`, `[H0]`, `[F0]`) |
| `accept_changes.py` | Accept all tracked changes in a `.docx` |
| `lexical_checklist.py` | Build glossary term checklist from original document |
| `apply_review.py` | Apply LLM review JSON as tracked changes |
| `fix_formatting.py` | Punctuation spacing and glossary replacements |
| `glossary.py` | Load and filter preferential translations |
| `build_prompt.py` | Legacy prompt builder (used by `run_proofreader.py`) |
| `prompts/` | Per-step LLM prompt files (proofreading, lexical constraints, grammar review) |
| `instructions.md` | Full proofreading specification (reference / legacy) |
