# Cleanup Notes: Dead Code & Issues

This file tracks code that was not included in the Pipeline, as well as path/reference errors discovered during consolidation.

## Status

- [ ] Analysis complete
- [ ] Dead code inventory compiled
- [ ] Path errors documented
- [ ] Lessons learned recorded

---

## Dead Code & Unused Notebooks

### DataCleaning Repository

**Unused Notebooks** (Not included in Pipeline):
- `1_fr_eng_correlation.ipynb` - EDA for French/English correlation
- `11_corpus_evaluation.ipynb` - Corpus quality evaluation
- `12_confirm_drop_text_cleaning.ipynb` - Text cleaning validation
- `91_create_eda_df.ipynb` - EDA dataframe creation
- `92_website_errors.ipynb` - Website parsing error analysis

**Reason**: These are exploratory/analysis notebooks, not part of the production pipeline. The key output (`generate_training_data.py`) is consolidated into `data_cleaning/pipeline.py`.

**Unused Code**:
- Language classifier development modules in `language_classifier_development/` - experimental versions, final version in `language_classifier/` is used

---

### FineTuning Repository

**Unused Notebooks** (Not included in Pipeline):
- `finetuned_model_comparison.ipynb` - Model comparison analysis
- `s2s_model_comparison.ipynb` - Seq2seq model analysis
- `sweep_evaluation.ipynb` - Hyperparameter sweep evaluation
- `training_data_creation_and_cleaning.ipynb` - Data preparation (some logic copied)
- `add_more_features.ipynb` - Feature engineering exploration

**Reason**: Analysis and experimental notebooks. Core functionality extracted into modules.

**Unused Code**:
- `launch_sweep.py` - Hyperparameter sweeping script. **INTENTIONALLY EXCLUDED**: Per user request, pipeline uses final chosen hyperparameters directly without sweeping.
- `finetune_hyperparams.py` - Contains sweep logic mixed with training logic. Only training logic copied.
- Sweeping argument parser code (`--sweep`, `--sweep_lr`, `--sweep_r`, etc.) - removed from final training pipeline
- Early stopping callback in some versions - included in final version

**Abandoned Folder**:
- `abandoned/` - Experimental approaches (unclear purpose, not used in final product)

**Backup Folder**:
- `backup/` - Versioned backups (not needed in Pipeline)

---

### RuleBasedTranslationMatching Repository

**Unused Scripts**:
- `sample_training_data.py` - Sample data generation (not part of production pipeline)
- `reference/` folder - Reference materials and documentation

**Partially Used**:
- `finetune_all.py` - Fine-tuning with replacements. Token replacement logic extracted; fine-tuning orchestration handled in Pipeline.
- `merge_weights.py` - Weight merging logic copied; script not directly used

**Abandoned Folder**:
- `abandoned/` - Old approaches to token preservation

---

### CSASTranslator Repository

**Current Status**: This repo is Phase 5 (final product), so most code is production-ready.

**Unused Components**:
- `translate.py` - Full implementation included, but some model-specific classes simplified in Pipeline
- `create_translated_document.py` - Document translation orchestration; higher-level than Pipeline scope (Pipeline is lower-level component)
- Survey app integration code - outside Pipeline scope

**Unused Notebooks**:
- Survey results analysis (post-deployment evaluation)

**Folders Not Included**:
- `backup/` - Versioned backups
- `offload/` - Hugging Face offload folder (device-specific)
- `translations_evaluation/` - Evaluation results (outputs, not code)

---

## Path & Reference Errors

### Hardcoded Relative Paths (Source Repos)

These paths will be centralized in `config.py` in Pipeline:

| Source | Hardcoded Path | Issue | Solution |
|--------|---|--------|----------|
| DataCleaning/generate_training_data.py | `../ParsedPublications` | Assumes structure relative to script | Config.py: `PARSED_DOCS_DIR` |
| DataCleaning/generate_training_data.py | `fr_eng_correlation_data.csv` | Current working directory assumption | Config.py: `CORRELATION_CSV_PATH` |
| FineTuning/add_features.py | `../Data/matched_data_wo_linebreaks.pickle` | Relative to FineTuning dir | Config.py: `DATA_DIR` |
| FineTuning/add_features.py | Save to `../Data/df_with_features.pickle` | Output path hardcoded | Config.py: `OUTPUT_DIR` |
| FineTuning/finetune_hyperparams.py | `../Data/training_data.jsonl` | Data path relative | Config.py: `TRAINING_DATA_PATH` |
| FineTuning/finetune_hyperparams.py | `outputs/` directory | Output path hardcoded | Config.py: `FINETUNING_OUTPUT_DIR` |
| RuleBasedTranslationMatching/finetune_replacements.py | `../Data/preferential_translations.json` | Translation dict path | Config.py: `TRANSLATIONS_JSON_PATH` |
| CSASTranslator/text_processing.py | `all_translations.json` | Translations file location | Config.py: `TRANSLATIONS_JSON_PATH` |
| CSASTranslator/translate.py | Model paths in parameters | Mixed local/remote paths | Config.py: `MODELS` dict with flexible paths |

### Incorrect Model Paths (RuleBasedTranslationMatching/finetune_replacements.py)

In FineTuning version:
```python
MODELS = {
    "m2m100_418m": {"model_id": "../Data/merged/m2m100_418m", ...},  # Path assumes merged weights
    # etc.
}
```

**Issue**: These are local paths to merged models, but source repos may not have these merged models saved. Pipeline will support:
- Remote model IDs (HuggingFace)
- Local paths (if pre-downloaded)
- Configuration-based paths

---

## Lessons Learned & Design Decisions

### 1. Hyperparameter Sweeping (EXCLUDED)

**Decision**: Do not include hyperparameter sweeping code.

**Reason**: User specified to use "chosen hyperparameters" directly. Hyperparameter sweeping was exploratory; final pipeline uses:
- learning_rate: 2e-4
- batch_size: 8
- lora_r: 16, alpha: 32, dropout: 0.05
- epochs: 2.0

**Impact**: Simplified `finetune_hyperparams.py` significantly by removing sweep argument parser and sweep combinatorial logic.

### 2. Notebook-to-Script Extraction

**Decision**: Extract code from notebooks, not copy notebooks.

**Reason**: Notebooks contain cells, visualizations, and exploratory code not suitable for production. Extracting core logic into functions is cleaner.

**Example**: `training_data_creation_and_cleaning.ipynb` contains feature engineering logic extracted into `add_features.py`.

### 3. Model Merging

**Decision**: Include weight merging in fine-tuning pipeline.

**Reason**: LoRA weights must be merged with base model for inference. Pipeline includes this step automatically.

### 4. Token Naming Strategy

**Decision**: Use predefined token naming conventions (SITE, NOMENCLATURE, TAXON, ACRONYM).

**Reason**: Final solution in RuleBasedTranslationMatching phase evolved to simple word-based tokens (avoid translation model modification). These conventions work across all supported models.

**Not Used** (from earlier iterations):
- Complex tokens like `__TECHNICAL_001__` (models translate special chars)
- Unicode special chars (affected by translation models)
- Encoder-integrated tokens (degraded translation quality)

### 5. Language-Specific Model Variants

**Decision**: Support directional model variants (en_fr vs fr_en).

**Reason**: Some models have separate checkpoints for each direction. OPUS-MT and mBART50 support this. Pipeline configuration allows specifying merged model paths per direction.

### 6. Cross-Module Dependencies

**Decision**: Minimize coupling; use config.py for shared state.

**Reason**: Each module should work independently. Shared configuration (paths, flags, hyperparams) in `config.py` enables flexibility and testing.

---

## Future Improvements (Out of Scope)

These were identified but not implemented (beyond current Pipeline scope):

1. **Ensemble Model Selection**: CSASTranslator implements best-of-ensemble from multiple models. Pipeline focuses on single-model fine-tuning.

2. **Survey Integration**: Phase 4 included human evaluation survey app. Pipeline is technical infrastructure (pre-survey).

3. **Automatic Token Generation**: Current approach uses predefined translation dictionary. Could be extended with automatic terminology extraction.

4. **Advanced Error Recovery**: Token validation & retranslation with different configs (Phase 3). Simplified in Pipeline to validation + fallback.

5. **Comprehensive Logging**: CSASTranslator has extensive logging. Pipeline will add structured logging in final phase.

---

## Known Limitations

1. **Language Classifier**: Requires pre-trained models (en_core_news_lg, fr_core_news_lg). Must be installed separately.

2. **Spacy Models**: Feature engineering requires large spacy models. Add to requirements.txt with note about disk space.

3. **Model Download Time**: First run downloads large pre-trained models. Consider caching strategy for repeated runs.

4. **GPU Memory**: Fine-tuning large models requires significant GPU memory. QLoRA quantization helps but doesn't eliminate memory requirements.

5. **Token Validation**: Simple approach of checking all tokens replaced. More sophisticated recovery possible but adds complexity.

---

## Implementation Checkpoints

**Before Phase Implementation**:
- [ ] Read corresponding section in PLAN.md
- [ ] Review relevant source files
- [ ] Check for path references in this Cleanup.md
- [ ] Note any deprecated/unused code
- [ ] Plan config.py entries needed
- [ ] **IMPORTANT**: Review data naming convention (PLAN.md Data Storage section)

**During Implementation**:
- [ ] Copy functions as-is (no refactoring)
- [ ] Adapt imports to Pipeline structure
- [ ] Update hardcoded paths to config.py references
- [ ] **Prepend `pipeline_` to all saved intermediate files** (pickle, jsonl, json)
- [ ] Remove notebook-specific code
- [ ] Test with sample data
- [ ] Verify no source data files overwritten

**After Implementation**:
- [ ] Update PROGRESS.md with completion status
- [ ] Document any new issues discovered
- [ ] Verify Data/ folder has only `pipeline_*` output files
- [ ] Add to this file if new dead code identified

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| Dead Notebooks | 15+ | Excluded, documented |
| Unused Scripts | 8+ | Excluded, documented |
| Hardcoded Paths | 10+ | Identified, will consolidate in config.py |
| Model Variants | 5 | Supported through flexible config |
| Hyperparameter Combinations | 288 | Excluded (using final values) |

**Total Reduction**: ~25,000 lines of exploratory/experimental code excluded. Pipeline focuses on production-ready components (~5,000-8,000 lines of consolidated code expected).
