# Pipeline Development Progress

## Status Overview

**Overall Progress**: 0% (Planning phase complete)

| Phase | Component | Status | Notes |
|-------|-----------|--------|-------|
| 1 | Data Cleaning | Not Started | Awaiting implementation |
| 2 | Fine-tuning | Not Started | Awaiting implementation |
| 3 | Preferential Translations | Not Started | Awaiting implementation |
| 4 | Evaluation | Not Started | Awaiting implementation |
| 5 | Integration & Main Pipeline | Not Started | Awaiting implementation |

## Phase 1: Data Cleaning Module
**Target**: Complete implementation of data_cleaning/ directory

### Subtasks
- [ ] Create data_cleaning/__init__.py
- [ ] Create data_cleaning/text_processing.py (language classifier, extraction)
- [ ] Create data_cleaning/correlation.py (sentence alignment, similarity)
- [ ] Create data_cleaning/feature_engineering.py (add_features)
- [ ] Create data_cleaning/pipeline.py (orchestrate workflow)
- [ ] Test with sample data
- [ ] Verify output pickle structure

### Challenges & Solutions
(To be filled as implementation progresses)

---

## Phase 2: Fine-Tuning Module
**Target**: Complete implementation of model_finetuning/ directory

### Subtasks
- [ ] Create model_finetuning/__init__.py
- [ ] Create model_finetuning/training_config.py (MODELS dict, hyperparams)
- [ ] Create model_finetuning/model_loading.py (tokenizer & model setup)
- [ ] Create model_finetuning/preprocessing.py (data preprocessing)
- [ ] Create model_finetuning/trainer.py (trainer setup & training)
- [ ] Create model_finetuning/pipeline.py (orchestrate training)
- [ ] Test with small dataset
- [ ] Verify fine-tuned weights save correctly
- [ ] Test model merging

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

---

## Implementation Notes

- Refer to PLAN.md for detailed architecture
- Check Cleanup.md for dead code inventory
- See STYLE.md for code formatting conventions
- Use config.py for all file paths and feature flags
