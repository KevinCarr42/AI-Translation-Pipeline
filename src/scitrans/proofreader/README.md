# Proofreader Pipeline

Automated proofreading pipeline for CSAS/DFO translated documents. Runs 5 sequential steps, producing a checkpoint `.docx` with tracked changes at each stage.

## Requirements

- Python 3.12+
- `python-docx`, `lxml` (already in project dependencies)

## Usage

Files are expected in `data/_PROOFREADING/` by default (override with `--review-dir`). The original and its translation must both be present:

- `1432_en.docx` (original)
- `1432_en_translated.docx` (translation to review)

### Interactive workflow (recommended)

Run the full pipeline interactively via `run_proofreader.py`. The script pauses at each LLM step, copies the prompt to your clipboard, and waits for you to press Enter once the response file exists.

```bash
python scripts/run_proofreader.py
```

At each LLM step:
1. The prompt is copied to your clipboard.
2. Paste it into Claude Code — the prompt includes a save instruction, so Claude Code writes the JSON response file automatically.
3. Press Enter in the script to continue to the next step.

Edit the `__main__` block at the bottom of `run_proofreader.py` to change the filename.

### Manual step-by-step workflow

You can also run individual steps via `run_proofreader_pipeline.py`:

```bash
# Run steps 1-2 (deterministic) and generate the step 3 prompt
python scripts/run_proofreader_pipeline.py 1432_en.docx

# Apply step 3 response and generate the step 4 prompt
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 3

# Apply step 4 response and generate the step 5 prompt
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 4

# Apply step 5 response — pipeline complete
python scripts/run_proofreader_pipeline.py 1432_en.docx --step 5
```

## Pipeline Steps

Each step produces a checkpoint file. Suffixes replace each other, not accumulate:

| Step | Output suffix               | Type | Description                                                      |
|------|-----------------------------|------|------------------------------------------------------------------|
| 1    | `_lexical_checklist.json`   | Auto | Scans original doc for glossary terms, builds location checklist |
| 2    | `_fix_formatting.docx`      | Auto | Glossary replacements + punctuation fixes (tracked changes)      |
| 3    | `_proofreading.docx`        | LLM  | Translation accuracy review                                      |
| 4    | `_lexical_constraints.docx` | LLM  | Verifies preferred terminology from step 1 checklist             |
| 5    | `_recommended_updates.docx` | LLM  | Final punctuation pass + grammar review                          |

For LLM steps, the script generates a `_stepN_prompt.md` file. The prompt instructs Claude Code to save its response as `_stepN_response.json` in the same directory.

## Running Individual Steps

Each step is an importable function in `scripts/run_proofreader_pipeline.py`:

```python
from scripts.run_proofreader_pipeline import step1_lexical_checklist, step2_fix_formatting
```

`scripts/run_proofreader.py` also exposes standalone helper functions (`run_fix_formatting`, `run_apply_review`, `run_build_prompt`) for ad-hoc use.

## Module Structure

| File                   | Purpose                                                                       |
|------------------------|-------------------------------------------------------------------------------|
| `extract_text.py`      | Extract text with location IDs (`[P0]`, `[T0-R0]`, `[H0]`, `[F0]`)            |
| `accept_changes.py`    | Accept all tracked changes in a `.docx`                                       |
| `lexical_checklist.py` | Build glossary term checklist from original document                          |
| `apply_review.py`      | Apply LLM review JSON as tracked changes                                      |
| `fix_formatting.py`    | Punctuation spacing and glossary replacements                                 |
| `glossary.py`          | Load and filter preferential translations                                     |
| `build_prompt.py`      | Legacy prompt builder (used by `run_proofreader.py`)                          |
| `prompts/`             | Per-step LLM prompt files (proofreading, lexical constraints, grammar review) |
| `instructions.md`      | Full proofreading specification (reference / legacy)                          |
