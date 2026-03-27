# AI Translation Pipeline — Update Summary

**Period:** December 17, 2025 – February 12, 2026 <br>
**Commits:** 41 | **Files Touched:** 37 | **Lines of Code:** ~7,700
additions

---

## Highlights at a Glance

| Area                    | What Changed                                                                               |
|-------------------------|--------------------------------------------------------------------------------------------|
| **MS Word Support**     | Full `.docx` translation with formatting, headers, footers, and tables                     |
| **Translation Caching** | Hashmap-based deduplication eliminates redundant model calls                               |
| **Name Preservation**   | Proper nouns (people's names) are now shielded from translation                            |
| **Bug Fixes**           | Four targeted fixes to the model generation and postprocessing pipeline                    |
| **Quality Evaluation**  | New evaluation module with Jupyter notebook for cross-feature comparison                   |
| **Manual Testing**      | Three iterative trial rounds using real FSAR documents, each driving targeted improvements |
| **Test Suite**          | 32 automated tests across 4 new test modules, integrated with pytest                       |
| **Codebase Cleanup**    | Removed ~5,000 lines of obsolete notebooks, guides, and dead code                          |

---

## New Features

### Microsoft Word Document Translation

Added end-to-end support for translating `.docx` files while preserving document
structure and formatting:

- **Run-level formatting preservation** — bold, italic, underline, font size, and colour are maintained through translation
- **Header & footer translation** — including tables embedded within headers/footers
- **Multi-section deduplication** — linked headers/footers are translated once and shared, avoiding double-translation
- **Intelligent run merging** — consecutive runs with identical formatting are merged to prevent text concatenation artifacts
- **970 lines of new tests** across two dedicated test modules (`test_word_translation.py`, `test_word_header_footer.py`) with fixture documents

### Translation Cache (Hashmap Deduplication)

Implemented an in-memory translation cache that stores previously translated segments in a hashmap. When the same source text appears multiple times in a document, the cached result is returned instantly — eliminating redundant model inference and significantly reducing processing time for repetitive content. This feature significantly reduces translations overhead during sections with a large amount of repeated sentence fragments — i.e., Figures and Tables. Backed by 6 dedicated tests in `test_translation_cache.py`.

### Proper Noun Preservation

Added intelligent detection and protection of people's names during translation. Names are tokenized and shielded from the model so they pass through untranslated, preventing common issues like "Pierre" being altered or names being conjugated as verbs. Includes 418+ lines of new test coverage.

---

## Bug Fixes & Model Improvements

### Targeted Fixes

Four focused fixes addressing known issues in the translation pipeline:

1. **Retry parameters applied to MBART50 generation** — model generation now correctly uses configured retry/backoff parameters instead of defaults
2. **Word-boundary matching in postprocessing** — token replacement now respects word boundaries, preventing partial-word substitutions
3. **Fuzzy token matching for corrupted output** — a recovery mechanism that rescues usable translations even when the model produces slightly corrupted tokens
4. **Corrupted token acceptance in validation** — the validation layer now tolerates minor token corruption rather than rejecting otherwise valid translations

### Foundation Fixes

- **Sentence splitting algorithm overhaul** — improved paragraph and sentence boundary detection, fixed extra period injection, added leading-number exclusions for figure text
- **Token replacement robustness** — all tokens are now included in fallback find-and-replace, fixing cases where replacements were silently dropped
- **Single model translation fix** — resolved an issue where using a single model could produce no valid translation output

---

## Quality & Evaluation

### Quality Evaluation Module

Built a standalone quality evaluation pipeline (`quality_evaluation/evaluate.py`) to benchmark translation output across different model configurations:

- Supports comparison of 1,000-sample evaluation runs
- Jupyter notebook (`quality_results.ipynb`) for visual performance comparison across features
- Length-based exclusion filtering for training data to improve model accuracy
- Results documented in `TESTING.md` with pytest integration and coverage reporting

---

## Manual Translation Testing — FSAR Document Trials

Three rounds of hands-on testing were conducted using real FSAR documents to validate translation quality and identify gaps in the pipeline. Each trial directly informed the next phase of development, creating a tight feedback loop between testing and implementation.

### Trial 1 — Workflow Feasibility

> *Outcome: Identified need for Word document support*

The first trial revealed that manually copying and pasting translated content back into formatted documents was extremely labour-intensive and error-prone. The overhead of reconstructing document structure by hand was a significant barrier to practical use. This finding directly motivated the development of native Word document support, allowing the pipeline to produce fully formatted `.docx` output and eliminating the manual copy-paste workflow entirely.

### Trial 2 — Structural Coverage

> *Outcome: Extended Word support to headers, footers, and tables*

With Word output in place, the second trial uncovered that only paragraph and table content was being translated — headers, footers, and other structural elements were being skipped. This gap meant the output documents were incomplete and still required manual intervention. These findings drove the second round of improvements to the Word module, adding translation support for headers, footers, embedded tables within headers/footers, and multi-section deduplication logic.

### Trial 3 — Near-Production Readiness

The most recent trial confirmed that the core translation and document structure handling are functioning as expected. Minor formatting issues were identified and are currently being addressed. Once these remaining fixes are implemented, the translated documents are expected to be ready for the first round of full human evaluation — a side-by-side comparison with previously accepted official translations. This milestone will mark the transition from development testing to formal quality assessment.

---

## Codebase Health

### Major Cleanup

A significant housekeeping effort removed over **5,000 lines** of accumulated
technical debt:

- Removed 4 obsolete Jupyter notebooks (`ocr_errors.ipynb`, `recalc_cosine_similarity.ipynb`, `recheck_similarity_stats.ipynb`, `sentence_splitting.ipynb`)
- Deleted stale planning documents and evaluation guides
- Relocated helper scripts from `tests/` to a dedicated `helpers/` directory
- Cleaned up print statements and development notes from production code
- Consolidated `requirements.txt`

### Test Infrastructure

- Migrated to **pytest** with coverage reporting
- Added `pytest.ini` configuration
- **4 new test modules** with **32 test functions** covering:
    - Token replacement and postprocessing fixes
    - Translation caching behaviour
    - Word document translation (content and formatting)
    - Header/footer handling and deduplication

### Documentation

- Created comprehensive `README.md` with project overview, architecture, and
  usage instructions
- Added `TESTING.md` with test execution guidelines and coverage expectations

---

## Summary

Over the past eight weeks, the AI Translation Pipeline has evolved from a text-only translation prototype into a multi-format translation system validated through iterative real-world testing. Three rounds of manual trials using FSAR documents created a direct feedback loop — each trial surfaced concrete issues that were resolved before the next, progressively raising the quality bar. The addition of Word document support significantly reduces required effort, while the translation cache and bug fixes improve both speed and accuracy. A strong automated test suite and thorough codebase cleanup ensure the project is maintainable and well-positioned for the next milestone: formal human evaluation against accepted official translations.
