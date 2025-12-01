# Pipeline Implementation Plan - Executive Summary

## Overview

A comprehensive implementation plan has been developed to consolidate 5 source repositories into a unified, modular **Pipeline** repository. The pipeline will support the complete workflow from raw data to fine-tuned translation models with optional rule-based terminology replacement and quality evaluation.

**Planning Duration**: Complete
**Estimated Implementation**: 40-60 hours of development (to be managed incrementally)
**Status**: Ready for phase-by-phase implementation

---

## What Has Been Done (Planning Phase)

✅ **1. Analyzed all 5 source repositories**
- DataCleaning: Text extraction & alignment functions
- FineTuning: Model training with LoRA & hyperparameter selection
- RuleBasedTranslationMatching: Token-based terminology preservation
- CSASTranslator: Integration, evaluation, and deployment
- Research notebooks: Identified as exploratory (excluded)

✅ **2. Created comprehensive documentation**
- `PLAN.md` (565 lines): Detailed architecture, data flow, implementation phases
- `PROGRESS.md` (250 lines): Development tracking and checkpoints
- `STYLE.md` (450 lines): Code conventions aligned with user instructions
- `Cleanup.md` (450 lines): Dead code inventory and issue tracking
- `README.md` (300 lines): Quick start guide and module overview
- `PLAN_SUMMARY.md` (this file)

✅ **3. Established architecture**
- 5 self-contained modules (data_cleaning, model_finetuning, preferential_translations, evaluation, main_pipeline)
- 15+ markdown files for documentation and tracking
- 9 implementation tasks identified in todo list

✅ **4. Defined code standards**
- No docstrings/type hints
- Full-word variable names
- Comments only for counterintuitive logic
- If-statements over try-except
- Code copied as-is from sources (not refactored)

✅ **5. Identified key consolidation points**
- Centralized file paths in `config.py` (10+ hardcoded paths eliminated)
- Unified model configuration (5 model variants with flexible paths)
- Boolean flags for feature toggle (data_cleaning, preferential_translations, evaluation)
- Hyperparameter selection (final values hardcoded, no sweeping code)

---

## Implementation Roadmap

### Phase 1: Data Cleaning Module
**Scope**: Raw text → Training/test datasets
**Source Lines**: ~800 lines (consolidated from multiple files)
**Key Tasks**:
- Copy text_processing functions from DataCleaning/generate_training_data.py
- Copy feature_engineering from FineTuning/add_features.py
- Implement sentence alignment & similarity computation
- Create pipeline orchestrator
- Test with sample correlation data

### Phase 2: Model Fine-Tuning Module
**Scope**: Training data → Fine-tuned models
**Source Lines**: ~900 lines (consolidated from multiple files)
**Key Tasks**:
- Extract model definitions & hyperparameters
- Implement tokenizer/model loading with device mapping
- Copy LoRA attachment logic
- Implement data preprocessing with language-specific tokenization
- Build trainer with appropriate data collators
- Implement weight merging
- Test with small subset of training data

### Phase 3: Preferential Translations Module
**Scope**: Rule-based terminology replacement
**Source Lines**: ~600 lines (consolidated from multiple files)
**Key Tasks**:
- Extract token creation and naming utilities
- Implement find-and-replace with word boundaries
- Copy preprocessing (token replacement) logic
- Implement postprocessing (token reversion)
- Add error handling and fallback mechanisms
- Test edge cases (capitalization, punctuation, sentence boundaries)

### Phase 4: Evaluation Module
**Scope**: Translation quality assessment
**Source Lines**: ~400 lines (consolidated from multiple files)
**Key Tasks**:
- Extract similarity metric computation
- Implement quality assessment functions
- Create comparison utilities for document-level analysis
- Add mistranslation detection
- Test with reference translations

### Phase 5: Integration & Setup
**Scope**: Orchestration and configuration
**Source Lines**: ~500 lines
**Key Tasks**:
- Create `config.py` with centralized paths and settings
- Create `requirements.txt` with all dependencies
- Create `main_pipeline.py` orchestrator
- End-to-end testing with sample workflow
- Finalize documentation

---

## Critical Design Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| **Exclude hyperparameter sweeping** | User requested final hyperparams only | Eliminates ~2,000 lines of sweep code |
| **Centralize file paths in config.py** | Avoid hardcoding across 10+ locations | Enables easy deployment & reconfiguration |
| **Support flexible model paths** | Mix of remote (HF) and local paths | Handles different deployment scenarios |
| **Copy code as-is, don't refactor** | Preserve source functionality & behavior | Lower risk of introducing bugs |
| **Minimize cross-module dependencies** | Loose coupling via config.py | Enables independent testing & reuse |
| **Boolean flags for features** | Easy enable/disable without code changes | Simplifies different use cases |

---

## Deliverables

### Code (5 modules + orchestrator)
```
Pipeline/
├── data_cleaning/            ~800 lines
├── model_finetuning/         ~900 lines
├── preferential_translations/ ~600 lines
├── evaluation/               ~400 lines
├── main_pipeline.py          ~200 lines
├── config.py                 ~100 lines
└── requirements.txt          ~50 lines

Total: ~3,050 lines (vs ~25,000 lines in source repos)
```

### Documentation (6 markdown files + tracking)
- PLAN.md (565 lines) - Architecture & implementation details
- PROGRESS.md (250 lines) - Development status & checkpoints
- STYLE.md (450 lines) - Code conventions & examples
- Cleanup.md (450 lines) - Dead code & issue tracking
- README.md (300 lines) - Quick start & module overview
- PLAN_SUMMARY.md (this file)
- Ongoing: PROGRESS.md updates during implementation

### Structured Organization
- Clear module boundaries
- Self-contained functionality
- Extensible architecture
- Comprehensive documentation

---

## Key Resources

### Implementation References
1. **PLAN.md** - Detailed specs for each phase (refer during implementation)
2. **STYLE.md** - Code examples and conventions (copy-paste friendly)
3. **Cleanup.md** - Dead code & path issues (avoid re-implementing)
4. **README.md** - Module descriptions (understand integration points)

### Source Code to Copy From
- `DataCleaning/generate_training_data.py` - Text processing functions
- `FineTuning/add_features.py` - Linguistic feature extraction
- `FineTuning/finetune_hyperparams.py` - Training logic (without sweeping)
- `FineTuning/translate.py` - Model classes (simplified for Pipeline)
- `RuleBasedTranslationMatching/finetune_replacements.py` - Replacement logic
- `CSASTranslator/text_processing.py` - Preprocessing utilities
- `CSASTranslator/translate.py` - Translation orchestration

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Path errors during copying | Centralize in config.py; validate file existence |
| Function dependencies on notebooks | Extract functions; remove notebook-specific code |
| Mixed hyperparameter configs | Hard-code final values; remove sweep logic |
| Model compatibility issues | Test each model before merging code |
| Feature creep | Stick to Phase 1-5 scope; document out-of-scope items |
| Integration bugs | End-to-end testing with small dataset per phase |

---

## Quality Assurance

### Per-Phase Testing
1. **Data Cleaning**: Output pickle structure, feature columns, quality validation
2. **Fine-tuning**: Training completes, weights save, model loads
3. **Preferential Translations**: Token replacement/reversion, edge cases
4. **Evaluation**: Metrics computation on sample text
5. **Integration**: End-to-end pipeline with sample workflow

### Code Review Checkpoints
- No docstrings or type hints
- Full-word variable names
- Comments only for non-obvious logic
- Boolean flags for feature control
- All paths in config.py (none hardcoded)
- Code copied unchanged from sources

---

## Success Criteria

✅ All 5 modules implemented and tested
✅ End-to-end pipeline functions without errors
✅ Configuration centralized in config.py
✅ Code style consistent across all modules
✅ Dead code documented in Cleanup.md
✅ PROGRESS.md updated with completion status
✅ README.md provides working quick-start example
✅ All source paths eliminated (centralized in config.py)
✅ Feature flags enable/disable each module
✅ No dependencies on notebook environments

---

## Next Steps for Implementation

1. **Before Starting Each Phase**:
   - Read relevant section in PLAN.md
   - Review source files listed
   - Check Cleanup.md for path references
   - Plan config.py entries

2. **During Implementation**:
   - Copy functions as-is (don't refactor)
   - Update imports for Pipeline structure
   - Replace hardcoded paths with config.py references
   - Test with small sample data
   - Update PROGRESS.md with checkpoint status

3. **After Completing Each Phase**:
   - Mark todos as completed
   - Document any issues discovered
   - Update PROGRESS.md with lessons learned
   - Run end-to-end test
   - Verify code style compliance

---

## Documentation for Multi-Agent Implementation

This plan is structured to be implementable by **multiple AI agents working in parallel**:

- **Agent 1**: Phase 1 (Data Cleaning)
- **Agent 2**: Phase 2 (Fine-tuning)
- **Agent 3**: Phase 3 (Preferential Translations)
- **Agent 4**: Phase 4 (Evaluation)
- **Agent 5**: Phase 5 (Integration)

Each agent has:
- Clear scope and deliverables
- Source code references
- Implementation checkpoints
- Testing requirements
- Style guidelines

---

## Estimated Effort Breakdown

| Phase | Implementation | Testing | Documentation | Total |
|-------|---|---|---|---|
| 1 (Data Cleaning) | 10h | 2h | 1h | 13h |
| 2 (Fine-tuning) | 12h | 3h | 1h | 16h |
| 3 (Preferential Translations) | 8h | 2h | 1h | 11h |
| 4 (Evaluation) | 6h | 2h | 1h | 9h |
| 5 (Integration) | 8h | 4h | 2h | 14h |
| **Total** | **44h** | **13h** | **6h** | **63h** |

*(Estimates assume familiar with source code and no major rewrites)*

---

## Repository Structure (Final)

```
Pipeline/
├── README.md                  ← Start here
├── PLAN.md                    ← Detailed implementation plan
├── PROGRESS.md                ← Track implementation status
├── STYLE.md                   ← Code conventions
├── Cleanup.md                 ← Dead code & issues
├── PLAN_SUMMARY.md            ← This file
│
├── data_cleaning/
│   ├── __init__.py
│   ├── text_processing.py
│   ├── correlation.py
│   ├── feature_engineering.py
│   └── pipeline.py
│
├── model_finetuning/
│   ├── __init__.py
│   ├── training_config.py
│   ├── model_loading.py
│   ├── preprocessing.py
│   ├── trainer.py
│   └── pipeline.py
│
├── preferential_translations/
│   ├── __init__.py
│   ├── token_utils.py
│   ├── replacements.py
│   └── pipeline.py
│
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py
│   └── comparison.py
│
├── main_pipeline.py
├── config.py
├── requirements.txt
│
└── tests/                     ← Optional
    ├── test_data_cleaning.py
    ├── test_finetuning.py
    ├── test_translations.py
    ├── test_evaluation.py
    └── test_integration.py
```

---

## Conclusion

The planning phase is **complete and comprehensive**. All information needed for implementation is documented in the markdown files created. The architecture is modular, the code style is well-defined, and the dead code has been identified and excluded.

**Status**: Ready to begin Phase 1 implementation whenever desired.

**Documentation Quality**: Ready for independent agent-based implementation across all 5 phases in parallel.

**Next Action**: Begin Phase 1 (Data Cleaning) or Phase 5 (Setup config.py & requirements.txt) as starting points.
