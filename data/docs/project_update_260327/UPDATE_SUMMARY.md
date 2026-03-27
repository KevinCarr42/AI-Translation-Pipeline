# AI Translations Project — Update Summary

---
**Period:** February 12, 2026 – March 27, 2026 <br>
**Commits:** 64 | **Files Touched:** 91 | **Lines Added:** ~27,200

## Highlights at a Glance

| Area                          | What Changed                                                                                   |
|-------------------------------|------------------------------------------------------------------------------------------------|
| **Repo Layout Refactor**      | Full restructure to industry-standard Python package layout (`src/scitrans/`)                  |
| **Word Document Translation** | Major enhancements to `.docx` pipeline: hyperlinks, tabs, figure/table numbering, tracked bugs |
| **Proofreader Pipeline**      | New LLM-assisted 5-step post-translation review module replacing find-and-replace approach     |
| **Test Suite**                | Grew from 32 to 261 automated tests across 11 test modules                                     |
| **Package Management**        | Migrated to `uv` with `pyproject.toml`; lockfile added for reproducible environments           |
| **Style Guides**              | Source and test style guides committed to repo for long-term maintainability                   |

## Major Refactor — Industry-Standard Repo Layout

The entire codebase was restructured in a single large PR into a proper Python package following modern conventions. This was a significant investment in long-term maintainability and professionalism.

### What Changed

- **`src/scitrans/` package layout** — all source code moved under a proper package namespace (`scitrans`), eliminating implicit relative imports and making the project installable
- **`pyproject.toml`** — replaced `requirements.txt` with a modern build configuration; project is now declared as an installable package with explicit metadata, entry points, and dependency management
- **`uv` package manager** — migrated from `pip` to `uv` with a committed `uv.lock` lockfile, providing fast, reproducible environment setup
- **Module reorganisation** — source split into dedicated sub-packages:
  - `src/scitrans/translate/` — translation pipeline (txt and Word)
  - `src/scitrans/proofreader/` — post-translation review
  - `src/scitrans/rules_based_replacements/` — lexical rules engine
  - `src/scitrans/model_finetuning/` — fine-tuning pipeline
  - `src/scitrans/quality_evaluation/` — evaluation tools
  - `src/scitrans/create_training_data/` — data preparation
  - `src/scitrans/helpers/` — shared utilities
- **Scripts separated** — entry-point scripts moved to a top-level `scripts/` directory, distinct from library code
- **Style guides committed** — `STYLE_GUIDE.md` (source) and `tests/TESTS_STYLE_GUIDE.md` added to codify conventions

## Word Document Translation — Large Document Support

Significant work was done to make the `.docx` translation pipeline robust for large, complex documents like FSARs. Several categories of bugs were identified through iterative testing and fixed.

### Hyperlink Handling

Large technical documents frequently contain inline hyperlinks embedded within translated paragraphs. These required dedicated infrastructure:

- **`_get_all_runs()` helper** — yields both direct paragraph runs and hyperlink-nested runs in document order, giving the translation pipeline a unified view of paragraph content
- **`HyperlinkRunWrapper`** — a proxy class that makes hyperlink-nested runs behave identically to direct runs throughout the pipeline
- **Hyperlink-aware formatting and merging** — `_build_format_segments`, `_merge_identical_runs`, and `_has_formatting_differences` all updated to use the unified run iterator
- **Notes output for hyperlinks** — `hyperlink_notes.py` records hyperlink locations and content for downstream review

### Tab Handling

Tabs are common structural elements in technical documents (e.g., numbered lists, indented items) and were previously being dropped or incorrectly merged during translation:

- Identified and fixed cases where tabs were lost at run boundaries
- Added dedicated tests (`test_word_translation.py`) with failing-then-passing coverage for tab preservation edge cases

### Figure and Table Numbering

A recurring issue in FSAR documents: figure and table labels (e.g., "Figure 3-1", "Tableau 2") were being altered or broken by the translation model. Addressed with:

- **`translate/numeric.py`** — dedicated module to detect and protect figure/table number patterns
- **`test_figure_table_numbers.py`** — 141-line test module covering label formats across paragraph and table-cell contexts
- Bugfix: period after figure/table labels was being incorrectly stripped in some cases; fixed and regression-covered

### Additional Word Fixes

- **Paragraph-level translation with proportional run remapping** — replaced segment-by-segment translation with whole-paragraph translation followed by proportional redistribution of translated text back to source runs, reducing formatting corruption
- **600-character input guard** — added budget limit matching the txt pipeline to prevent oversized paragraphs from being sent to the model
- **`_set_proofing_language()`** — sets the spellcheck language on translated output documents
- **Translation notes output** — pipeline now writes a `.json` notes file alongside translated `.docx` output, capturing formatting anomalies, hyperlinks, and other reviewer-relevant observations; a `json_to_word` converter produces a human-readable Word summary document

## Proofreader Pipeline — LLM-Assisted Post-Translation Review

The previous approach to enforcing preferred terminology used a find-and-replace method driven by lexical constraint rules. This was brittle: it could not handle context-dependent term choices, multi-word expressions, or cases where the correct term depended on surrounding translation. The approach has been replaced by a structured, multi-step LLM review pipeline.

### The Problem with Find-and-Replace

Lexical constraints (a glossary of preferred French translations for technical terms) were previously applied by scanning the translated output for known incorrect terms and substituting the preferred ones. This fails in practice because:

- The same source word may need different translations depending on context
- Find-and-replace cannot verify whether a substitution makes grammatical sense
- It silently corrupts translations when term boundaries are not exact

### The New Pipeline

The new proofreader module (`src/scitrans/proofreader/`) runs 5 sequential steps, producing a checkpoint `.docx` with tracked changes at each stage:

| Step | Type | Description                                                    |
|------|------|----------------------------------------------------------------|
| 1    | Auto | Scans original for glossary terms; builds a location checklist |
| 2    | Auto | Glossary replacements + punctuation fixes (tracked changes)    |
| 3    | LLM  | Translation accuracy review                                    |
| 4    | LLM  | Verifies preferred terminology against the step 1 checklist    |
| 5    | LLM  | Final punctuation pass and grammar review                      |

Steps 1 and 2 are fully automated. Steps 3–5 invoke an LLM: the script generates a structured prompt, pauses, and waits for the response JSON before proceeding to the next step. This human-in-the-loop design keeps a reviewer in control while automating the mechanical parts.

### Module Structure

| File                   | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| `extract_text.py`      | Extracts text with location IDs for LLM prompts                |
| `lexical_checklist.py` | Builds glossary term checklist from the source document        |
| `fix_formatting.py`    | Automated punctuation spacing and glossary replacements        |
| `apply_review.py`      | Applies LLM response JSON as tracked changes in the `.docx`    |
| `glossary.py`          | Loads and filters the preferential translations table          |
| `accept_changes.py`    | Accepts all tracked changes in a document                      |
| `prompts/`             | Per-step LLM prompt templates (proofreading, lexical, grammar) |

Two entry-point scripts are provided: `run_proofreader.py` for interactive step-by-step use, and `run_proofreader_pipeline.py` for running individual steps programmatically.

## Test Suite Growth

| Metric         | Feb 12 | Mar 27 |
|----------------|--------|--------|
| Test functions | 32     | 261    |
| Test modules   | 4      | 11     |

New modules added:

- `test_figure_table_numbers.py` — figure/table label preservation across formats
- `test_formatting_errors.py` — formatting edge cases in Word translation
- `test_table_cell_translation.py` — table cell dispatch and translation logic
- `test_tables_match.py` — source/target table structure alignment
- `test_multiline_and_smarttag.py` — multi-line paragraph and smart tag handling
- `test_rules_based_replacements.py` — integration tests for the lexical rules engine
- `test_proofreader_pipeline.py` — proofreader pipeline step coverage

## Next Steps

| Area                          | Description                                                                                |
|-------------------------------|--------------------------------------------------------------------------------------------|
| **Proofreader Evaluation**    | Evaluate LLM proofreader against translations bureau output; tune based on repeated errors |
| **Proofreader Deployment**    | Design and build a deployable proofreader workflow accessible to other DFO staff           |
| **Word Formatting Rules**     | Refine `.docx` formatting rules based on feedback from the web & publications team         |
| **Preferential Translations** | Extend and improve the preferential translations dataset                                   |
| **Figure & Image Support**    | LLM-assisted review of figures with recommended translations for authors                   |

### Proofreader Evaluation & Tuning

The LLM proofreader pipeline was built and tested internally. The next phase is evaluation against real-world output by comparing AI-produced translations with translations produced by the translations bureau.

- **Evaluate performance based on repeated errors** — identify systematic failure patterns across documents and use these to guide prompt refinement or rule updates
- **Add error handling where necessary** — harden the pipeline against edge cases discovered during human review testing
- **Consider re-finetuning models** — depending on evaluation results, targeted fine-tuning of the underlying translation model may be warranted

### Proofreader Deployment

The proofreader pipeline currently runs as a developer-facing script. The goal is to make it accessible to other DFO staff without requiring a local Python environment or technical setup.

- Design a deployable workflow (e.g., a packaged tool, web interface, or guided script) that non-technical staff can run independently
- Ensure the human-in-the-loop review steps remain intact in the deployed version

### Word Formatting Rules

`.docx` formatting support has been developed iteratively based on internal testing. Conversations with the web & publications team will surface real-world formatting requirements that have not yet been accounted for.

- Adjust formatting rules based on findings from those conversations
- Ensure output documents meet the formatting standards expected for publication

### Preferential Translations

The preferential translations dataset (used by both the proofreader and the rules-based replacement engine) needs to be extended to cover more terminology and improved where existing entries are incomplete or incorrect.

- Review and revise existing entries
- Expand coverage based on recurring terminology in source documents

### Figure & Image Support

Figures in technical documents (e.g., FSARs) contain text that is currently outside the scope of the translation pipeline. The planned approach is LLM-assisted review of figure content:

- Figures will be examined by an LLM to identify translatable text elements
- A table of recommended translations will be generated and provided to the author to guide translated figure creation
- Recommendations will draw from the preferential translations file and known variable translations for consistency with the rest of the document

