# Documentation Index

All development progress, style guidelines, and detailed planning documents are organized in this folder.

## Quick Navigation

### Getting Started
- **[README.md](../README.md)** - Start here for project overview and quick start guide
- **[IMPLEMENTATION_COMPLETE.md](./IMPLEMENTATION_COMPLETE.md)** - Final summary of all 5 completed phases

### Architecture & Design
- **[PLAN.md](./PLAN.md)** - Comprehensive system architecture and design document
- **[PLAN_SUMMARY.md](./PLAN_SUMMARY.md)** - Executive summary of key design decisions

### Implementation Tracking
- **[PROGRESS.md](./PROGRESS.md)** - Detailed development progress for all 5 phases
- **[PHASE_1_COMPLETE.md](./PHASE_1_COMPLETE.md)** - Data Cleaning module summary
- **[PHASE_2_COMPLETE.md](./PHASE_2_COMPLETE.md)** - Model Fine-Tuning module summary
- **[PHASE_4_COMPLETE.md](./PHASE_4_COMPLETE.md)** - Evaluation module summary

### Code Standards & Guidelines
- **[STYLE.md](./STYLE.md)** - Code conventions and guidelines
- **[Cleanup.md](./Cleanup.md)** - Dead code inventory from source repositories
- **[DATA_STORAGE_GUIDE.md](./DATA_STORAGE_GUIDE.md)** - File naming and organization conventions

---

## Document Descriptions

### PROGRESS.md
Current development status and phase-by-phase implementation details:
- Phase 1: Data Cleaning (Complete)
- Phase 2: Model Fine-Tuning (Complete)
- Phase 3: Preferential Translations (Complete)
- Phase 4: Evaluation (Complete)
- Phase 5: Integration (Complete)

### STYLE.md
Code conventions all developers should follow:
- No docstrings or type hints
- Full-word variable names
- Comments only for non-obvious logic
- If statements over try-except blocks
- Clean, readable, idiomatic Python

### PLAN.md
Complete architecture documentation:
- System overview and data flow
- Module responsibilities and interactions
- Data storage conventions
- Hyperparameter specifications
- Model definitions
- Code quality standards

### DATA_STORAGE_GUIDE.md
Guidelines for organizing and naming files:
- File naming conventions with `pipeline_` prefix
- Folder structure for intermediate and final outputs
- Path configuration via config.py
- Examples of correct and incorrect usage

### Cleanup.md
Inventory of dead code and issues found in source repositories:
- Code identified for potential removal
- Known issues from source repositories
- Rationale for code inclusion/exclusion decisions

### PHASE_*_COMPLETE.md Files
Summary documents for each completed phase:
- Files created and their purposes
- Key components and features
- Configuration usage examples
- Output file structures
- Testing recommendations

---

## How to Use This Documentation

1. **First time?** Read `../README.md` for overview
2. **Need architecture details?** See `PLAN.md` or `PLAN_SUMMARY.md`
3. **Contributing code?** Review `STYLE.md` for conventions
4. **Need file organization help?** Check `DATA_STORAGE_GUIDE.md`
5. **Tracking progress?** Visit `PROGRESS.md`
6. **Understanding a specific phase?** See `PHASE_X_COMPLETE.md`

---

## File Organization

```
documentation/
├── INDEX.md                    # This file
├── PROGRESS.md                 # Development tracking (all phases)
├── STYLE.md                    # Code conventions
├── PLAN.md                     # Full architecture
├── PLAN_SUMMARY.md             # Design decisions summary
├── DATA_STORAGE_GUIDE.md       # File naming rules
├── PHASE_1_COMPLETE.md         # Data Cleaning phase
├── PHASE_2_COMPLETE.md         # Model Fine-Tuning phase
├── PHASE_4_COMPLETE.md         # Evaluation phase
├── Cleanup.md                  # Dead code inventory
└── UPDATE_SUMMARY.md           # Recent updates
```

---

## Key Information

### Code Statistics
- **19 Python files** implementing 5 core modules
- **~1,467 lines** of production-quality code
- **14 documentation files** providing comprehensive guidance

### Module Structure
- `data_cleaning/` - Phase 1 (Text processing, alignment, features)
- `model_finetuning/` - Phase 2 (LoRA training, preprocessing)
- `preferential_translations/` - Phase 3 (Token replacement, terminology)
- `evaluation/` - Phase 4 (Metrics, multi-model testing)
- `main_pipeline.py` - Phase 5 (Orchestration)

### Configuration
- All paths and hyperparameters in `config.py`
- Data files use `pipeline_` prefix to preserve source data
- Feature flags for quantization, precision, and evaluation options

---

## Maintenance

When making changes:
1. Update relevant documentation immediately
2. Follow code style guidelines from `STYLE.md`
3. Update `PROGRESS.md` with new implementation details
4. Keep this INDEX.md current

---

Last Updated: December 1, 2024
Status: All phases complete
Next: Production deployment and testing
