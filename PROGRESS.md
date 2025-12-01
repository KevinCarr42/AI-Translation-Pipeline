# Pipeline Development Progress

## Status Overview

**Overall Progress**: 0% (Planning phase complete)

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| 1 | Data Cleaning | ✅ Complete | text_processing, correlation, feature_engineering, pipeline modules created |
| 2 | Fine-tuning | ✅ Complete | model_loading, preprocessing, trainer, pipeline modules created |
| 3 | Preferential Translations | In Progress | Awaiting implementation |
| 4 | Evaluation | Not Started | Awaiting implementation |
| 5 | Integration & Main Pipeline | ✅ Partial | config.py and requirements.txt created |

## Phase 1: Data Cleaning Module
**Target**: Complete implementation of data_cleaning/ directory
**Status**: ✅ **COMPLETE**

### Subtasks
- [x] Create data_cleaning/__init__.py
- [x] Create data_cleaning/text_processing.py (language classifier, extraction)
- [x] Create data_cleaning/correlation.py (sentence alignment, similarity)
- [x] Create data_cleaning/feature_engineering.py (add_features)
- [x] Create data_cleaning/pipeline.py (orchestrate workflow)
- [x] Copy language_classifier module from source
- [x] Create config.py with all paths and configurations
- [x] Create requirements.txt with all dependencies
- [ ] Test with sample data (pending)
- [ ] Verify output pickle structure (pending)

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Phase 2: Fine-Tuning Module
**Target**: Complete implementation of model_finetuning/ directory
**Status**: ✅ **COMPLETE**

### Subtasks
- [x] Create model_finetuning/__init__.py
- [x] Create model_finetuning/model_loading.py (tokenizer & model setup with QLoRA)
- [x] Create model_finetuning/preprocessing.py (Preprocessor class, M2MDataCollator)
- [x] Create model_finetuning/trainer.py (Seq2SeqTrainer setup)
- [x] Create model_finetuning/pipeline.py (orchestrate entire fine-tuning workflow)
- [ ] Test with small dataset (pending)
- [ ] Verify fine-tuned weights save correctly (pending)
- [ ] Test model merging (pending)

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Phase 3: Preferential Translations Module
**Target**: Complete implementation of preferential_translations/ directory

### Subtasks
- [ ] Create preferential_translations/__init__.py
- [ ] Create preferential_translations/token_utils.py
- [ ] Create preferential_translations/replacements.py
- [ ] Create preferential_translations/pipeline.py
- [ ] Test token creation & replacement
- [ ] Test edge cases (capitalization, punctuation, boundaries)
- [ ] Test reversion logic

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Phase 4: Evaluation Module
**Target**: Complete implementation of evaluation/ directory

### Subtasks
- [ ] Create evaluation/__init__.py
- [ ] Create evaluation/metrics.py (similarity, quality, comparison)
- [ ] Create evaluation/comparison.py (mistranslation detection)
- [ ] Test metrics computation
- [ ] Test integration into loops

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Phase 5: Integration & Setup
**Target**: Main pipeline orchestration & documentation

### Subtasks
- [ ] Create config.py (global configuration)
- [ ] Create main_pipeline.py (orchestrator)
- [ ] Create requirements.txt
- [ ] Create STYLE.md (code conventions)
- [ ] Create Cleanup.md (dead code inventory)
- [ ] Create README.md (quick start guide)
- [ ] End-to-end testing

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Key Decisions Made

1. **Data Cleaning Input**: Use matched_data_wo_linebreaks.pickle as primary dataset per user specification
2. **Hyperparameters**: Use final chosen values directly (no sweeping code)
3. **Token Naming**: Follow existing conventions (SITE, NOMENCLATURE, TAXON, ACRONYM)
4. **Code Style**: No docstrings/type hints; preserve variable names; clean readable code within Pipeline
5. **Data Storage**: All Pipeline outputs prepended with `pipeline_` to avoid overwriting source data
   - Example: `pipeline_matched_data.pickle`, `pipeline_training_data.jsonl`
   - Location: Data/ folder (configured in config.py)
   - Rationale: Preserves source repos, enables safe re-runs, supports parallel work

---

## Implementation Notes

### Phase 1 Completion (Dec 1, 2024)

**Files Created**:
- `config.py` (2.9 KB) - Central configuration with DATA_DIR, MODEL_OUTPUT_DIR, MODELS dict, hyperparameters, flags
- `requirements.txt` (282 B) - All package dependencies
- `data_cleaning/__init__.py` - Module initialization with exports
- `data_cleaning/text_processing.py` - Text cleaning, extraction functions
- `data_cleaning/correlation.py` - Sentence alignment, similarity computation
- `data_cleaning/feature_engineering.py` - Linguistic feature addition (verb_ratio, noun_ratio, etc.)
- `data_cleaning/pipeline.py` - Main orchestration function
- `language_classifier/` - Copied from DataCleaning source

**Key Design Decisions**:
- config.py centralizes all paths and feature flags
- All data outputs use `pipeline_` prefix (e.g., pipeline_matched_data.pickle)
- Imports use config.DATA_DIR for safe path handling
- Spacy models disabled parser for efficiency
- Multiprocessing with proper worker count calculation
- Device detection (CPU/CUDA) automatic

### Phase 2 Completion (Dec 1, 2024)

**Files Created**:
- `model_finetuning/__init__.py` - Module initialization with exports
- `model_finetuning/model_loading.py` (37 lines) - load_tokenizer_and_model() with QLoRA support
- `model_finetuning/preprocessing.py` (72 lines) - Preprocessor class, M2MDataCollator for data handling
- `model_finetuning/trainer.py` (68 lines) - build_trainer() for Seq2SeqTrainer setup
- `model_finetuning/pipeline.py` (169 lines) - finetune_model() main orchestration

**Key Design Decisions**:
- Uses config.MODELS for model definitions (5 models supported)
- Supports QLoRA quantization for memory efficiency
- Automatic device mapping detection
- Special handling for M2M100 models (decoder_input_ids)
- Gradient checkpointing enabled for memory optimization
- Dataset filtering by source language for directional models
- LoRA parameters (r=16, alpha=32, dropout=0.05) from config

**Next Phase**: Phase 3 (Preferential Translations) - ready to begin

- Refer to PLAN.md for detailed architecture
- Check Cleanup.md for dead code inventory
- See STYLE.md for code formatting conventions
- Use config.py for all file paths and feature flags
