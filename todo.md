# Code Quality Improvement Plan

Generated: 2026-01-28
Files Reviewed: 27 Python files across translate/, rules_based_replacements/, model_finetuning/, quality_evaluation/, create_training_data/, helpers/, tests/

## Executive Summary

This is a translation pipeline for English-French document translation using seq2seq models (Opus-MT, M2M-100, mBART-50) with terminology preservation via token replacement. The codebase is functional and well-structured, but the `lexical_constraints_options.md` document correctly identifies significant issues with gender/plural agreement and token corruption. The highest-priority items are implementing the recommended short-term fixes (Option 4A/4B) and preparing infrastructure for the LLM proofreader (Option 2).

## Critical Issues

### From lexical_constraints_options.md Recommendations

- [ ] **Token postprocessing uses unsafe str.replace()** | `rules_based_replacements/replacements.py` line 132 | Effort: Low | Impact: Critical
  - The document correctly identifies this: `result_text = result_text.replace(token, replacement)` is not boundary-aware
  - Should use regex with word boundaries as suggested in Option 4A
  - Risk: Could replace parts of words if token appears as substring

- [ ] **No fuzzy token matching for corrupted tokens** | `translate/models.py` lines 365-374, `rules_based_replacements/replacements.py` | Effort: Low | Impact: Critical
  - Token corruption (spaces inserted, pluralization) causes fallback to unconstrained translation
  - Implement Option 4B fuzzy matching before falling back

### Code Bugs Found

- [ ] **Bug: MBART50 ignores generation_kwargs** | `translate/models.py` line 256 | Effort: Low | Impact: Critical
  ```python
  generation_arguments.update(generation_arguments)  # BUG: should be generation_kwargs
  ```
  - This means MBART50 model ignores any custom generation parameters passed to translate_text()

- [ ] **Bug: Unused variable i in translate_with_retries** | `translate/models.py` lines 346, 355 | Effort: Low | Impact: Low
  - Uses `i` from the for loop scope after it ends; should use `len(param_variations) - 1`

## High Priority

### Implementing lexical_constraints_options.md Recommendations

- [ ] **Implement Option 4A: Boundary-aware postprocessing** | `rules_based_replacements/replacements.py` | Effort: Low | Impact: High
  ```python
  # Replace line 132:
  # result_text = result_text.replace(token, replacement)
  # With:
  import re
  pattern = re.compile(r'\b' + re.escape(token) + r'\b')
  result_text = pattern.sub(replacement, result_text)
  ```

- [ ] **Implement Option 4B: Fuzzy token matching** | `rules_based_replacements/replacements.py` or new function | Effort: Medium | Impact: High
  - Add function to detect corrupted tokens (spaced, pluralized)
  - Call before fallback to unconstrained translation
  - Reduces fallback rate significantly

- [ ] **Prepare for Option 2: LLM Proofreader** | New file in translate/ | Effort: Medium | Impact: High
  - Create `translate/llm_proofreader.py` with interface for post-translation correction
  - Support for batching sentences (10-20 per call)
  - Support for local models (Mistral/Llama) and API (Claude Haiku)
  - This is the recommended medium-term solution

- [ ] **Add gender metadata to terminology JSON** | `../Data/preferential_translations.json` | Effort: Medium | Impact: High
  - Extend JSON structure as suggested in Option 4D
  - Required for any gender agreement solution
  - Start with high-frequency terms

### Model Selection Improvement

- [ ] **Consider using similarity_vs_target for selection** | `translate/models.py` lines 482-492 | Effort: Low | Impact: Medium
  - Currently uses `similarity_vs_source` which may favor overly literal translations
  - When target_text is available (quality evaluation), use `similarity_vs_target`
  - The lexical_constraints_options.md identifies this as Option 4C

## Medium Priority

### Code Quality Issues

- [ ] **translate_with_retries returns None without explicit handling** | `translate/models.py` line 326 | Effort: Low | Impact: Medium
  - When `is_valid_translation` returns False on all attempts, returns None
  - Callers handle this, but could use more explicit typing/documentation

- [ ] **Recursive function with no depth limit** | `rules_based_replacements/token_utils.py` lines 9-13 | Effort: Low | Impact: Medium
  ```python
  def choose_random_int(max_n=999):
      n = int(pareto(b=1.16, scale=1).rvs())
      if n <= max_n:
          return n
      return choose_random_int(max_n)  # Could recurse deeply with bad luck
  ```
  - Add max_attempts parameter or use iterative approach

- [ ] **Inconsistent handling of empty token_mapping** | `translate/models.py`, `rules_based_replacements/preferential_translations.py` | Effort: Low | Impact: Low
  - Some functions check `if token_mapping:`, others check `if not token_mapping:`
  - Consider standardizing to always return empty dict rather than None

- [ ] **Missing apostrophe normalization inconsistency** | `translate/document.py` line 125-126 | Effort: Low | Impact: Low
  - `normalize_apostrophes` only handles two variants; French uses more
  - Could miss other Unicode apostrophe-like characters

### Structural Improvements

- [ ] **No retry mechanism isolation** | `translate/models.py` | Effort: Medium | Impact: Medium
  - `translate_with_retries` is tightly coupled to TranslationManager
  - Consider extracting to separate module for easier testing and modification

- [ ] **Debug output uses print() not logging** | Multiple files | Effort: Low | Impact: Low
  - Mix of print() and logging throughout codebase
  - Could standardize on logging for better control

## Low Priority

### Style and Consistency

- [ ] **Unused imports in some files** | Various | Effort: Low | Impact: Low
  - `scipy.stats.pareto` in token_utils.py only used for random int (unusual choice)
  - Some files import modules not used

- [ ] **Magic numbers in document.py** | `translate/document.py` line 55 | Effort: Low | Impact: Low
  - `MAX_CHAR = 600` could be in config.py with other constants

- [ ] **Inconsistent parameter naming** | Various | Effort: Low | Impact: Low
  - Some use `use_find_replace`, others `with_preferential_translation`
  - Aliases to same concept but confusing

## Project-Wide Recommendations

### Architecture

1. **Token replacement pipeline is well-designed but needs the improvements identified in lexical_constraints_options.md.** The Option 4A/4B fixes are quick wins that reduce fallback rates.

2. **The ensemble approach (multiple models + similarity scoring) is sound but the selection metric (similarity_vs_source) may not be optimal.** Consider A/B testing with similarity_vs_target when reference translations are available.

3. **The lexical_constraints_options.md correctly identifies that LLM Proofreader (Option 2) is the most practical medium-term solution.** It can be added as an optional post-processing step without changing the existing pipeline.

### Testing

1. **Create evaluation dataset as suggested in lexical_constraints_options.md section "Evaluation Criteria"** - 100 sentences per category, 50 with gender context, 50 with plurals, 50 with multiple terms.

2. **Add unit tests for token replacement edge cases** - boundary matching, case preservation, multi-word terms.

### Data

1. **Extend preferential_translations.json** with gender metadata for French terms. Start with the most frequent terms.

2. **Consider tracking plural forms** in the terminology dictionary.

## Quick Wins

High-impact, low-effort items to implement first:

1. **Fix MBART50 generation_kwargs bug** - 1 line change, restores parameter functionality
2. **Implement boundary-aware postprocessing (Option 4A)** - 3 line change, reduces partial word replacement risk
3. **Implement fuzzy token matching (Option 4B)** - ~20 lines, reduces fallback rate
4. **Use similarity_vs_target when available (Option 4C)** - 5 line change, may improve translation selection

## Refactoring Dependencies

Order of implementation:

1. Fix the MBART50 bug (no dependencies, standalone fix)
2. Implement Option 4A boundary-aware postprocessing (no dependencies)
3. Implement Option 4B fuzzy token matching (no dependencies, can be done with 4A)
4. Add gender metadata to terminology JSON (needed before any gender agreement work)
5. Implement Option 2 LLM Proofreader (requires gender metadata for best prompts)
6. Consider Option 3 instruction fine-tuning only after 4A/4B/2 are evaluated

## Files Referenced

| File | Purpose |
|------|---------|
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\translate\models.py` | Core translation models and manager |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\rules_based_replacements\replacements.py` | Token preprocessing/postprocessing |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\rules_based_replacements\token_utils.py` | Token utilities |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\rules_based_replacements\preferential_translations.py` | Translation API |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\translate\document.py` | Document translation |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\config.py` | Configuration |
| `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\lexical_constraints_options.md` | Recommendations document |
