# Data Storage Conventions Update - Summary

**Date**: December 1, 2024
**Status**: ✅ Complete
**Files Updated**: 6 markdown files
**New Files Created**: 1 comprehensive guide

---

## What Changed

### Critical Clarification Added

**Data files must be stored in the Data/ folder with a `pipeline_` prefix to avoid overwriting source data.**

### Example Naming Convention

| Do NOT | Do Instead |
|--------|-----------|
| `matched_data.pickle` | `pipeline_matched_data.pickle` |
| `training_data.jsonl` | `pipeline_training_data.jsonl` |
| `evaluation.json` | `pipeline_evaluation_results.json` |
| `df_with_features.pickle` | `pipeline_df_with_features.pickle` |

---

## Files Updated

### 1. NEW: DATA_STORAGE_GUIDE.md (13 KB) ⭐
**Status**: Created
**Purpose**: Comprehensive guide for data storage and file naming
**Key Sections**:
- Core principle (distinguish source from pipeline outputs)
- Folder structure diagram
- File naming rules with examples
- 4 implementation examples with code
- Why this matters (data loss prevention)
- Special cases (multiple versions, temporary files)
- Checklist for verification
- Configuration setup

**Audience**: All developers (critical before writing code)

---

### 2. PLAN.md (Updated)
**Change**: Added "Data Storage Conventions" section
**Location**: Before "Copying Strategy" section
**Content**:
- Folder structure showing Data/ organization
- File naming rules for Pipeline outputs
- Rationale for the convention
- Example of correct vs. incorrect naming

**Impact**: Developers now know proper naming during Phase 1 implementation

---

### 3. STYLE.md (Updated)
**Change**: Added "File Naming Conventions" section
**Location**: Before "Summary Checklist"
**Content**:
- Data file naming rules with code examples
- Model output directory structure
- Explanation of why this matters
- Additional checklist items (2 new items)

**Impact**: Code review checklist now includes file naming validation

---

### 4. README.md (Updated)
**Change**: Added "Data Storage Conventions" section
**Location**: Before "Configuration" section
**Content**:
- Important note about preserving source data
- Naming rules (pickle, training data, evaluation)
- Location (Data/ folder)
- Reason for convention
- Example (correct vs. incorrect)

**Impact**: First-time users see this immediately in quick start

---

### 5. PROGRESS.md (Updated)
**Change**: Added 5th Key Decision
**Location**: In "Key Decisions Made" section
**Content**:
- Data Storage: All outputs prepended with `pipeline_`
- Examples of naming
- Location (Data/ folder with config.py)
- Rationale (preserves source repos, enables safe re-runs, supports parallel work)

**Impact**: Team can track this important decision

---

### 6. PLAN_SUMMARY.md (Updated)
**Change**: Added 7th Critical Design Decision
**Location**: In "Critical Design Decisions" table
**Content**:
- Decision: Prepend `pipeline_` to all outputs
- Rationale: Preserve source data, avoid overwrites
- Impact: Enables safe re-runs & parallel work

**Impact**: Managers understand data safety strategy

---

### 7. DOCUMENTATION_INDEX.md (Updated)
**Changes**:
1. Added DATA_STORAGE_GUIDE.md as first new file description
2. Updated "Quick Navigation" section with critical warning
3. Added `DATA_STORAGE_GUIDE.md` to "Before writing ANY code" section
4. Updated "Most Common Questions" with critical file location

**Impact**: Navigation now emphasizes data safety as top priority

---

## Key Documentation

### Files to Read First (In Order)
1. **README.md** - 5 min - Project overview
2. **PLAN_SUMMARY.md** - 10 min - Executive summary
3. **DATA_STORAGE_GUIDE.md** - 15 min - ⭐ **CRITICAL** - File naming & storage
4. **PLAN.md** - Full technical specs (refer during implementation)
5. **STYLE.md** - Code conventions & checklist

### For Implementation Teams
1. Read DATA_STORAGE_GUIDE.md completely before coding
2. Refer to STYLE.md checklist items (now includes file naming)
3. Check Cleanup.md for implementation checkpoints (updated with data naming reminders)

---

## Implementation Impact

### Before Coding
- **MUST READ**: DATA_STORAGE_GUIDE.md
- **CRITICAL**: Understand the `pipeline_` prefix convention
- **Verify**: File paths use config.DATA_DIR

### During Coding
- Every `to_pickle()` → prepend `pipeline_`
- Every `.json` save → prepend `pipeline_`
- All paths → use `config.DATA_DIR`

### During Code Review
- Check: All output files start with `pipeline_`
- Check: Data/ folder only has original files + pipeline_* files
- Check: No overwrites of source data

### After Running Code
- Verify: Data/ has original files untouched
- Verify: New files start with `pipeline_`
- Can safely: Run again without data loss

---

## Examples for Developers

### Phase 1 (Data Cleaning)
```python
# Save matched data
output_path = os.path.join(config.DATA_DIR, "pipeline_matched_data.pickle")
dataframe.to_pickle(output_path)

# Add features and save
featured_path = os.path.join(config.DATA_DIR, "pipeline_df_with_features.pickle")
featured_df.to_pickle(featured_path)
```

### Phase 2 (Fine-tuning)
```python
# Create training JSONL
output_path = os.path.join(config.DATA_DIR, "pipeline_training_data.jsonl")
save_jsonl(dataframe, output_path)

# Save evaluation metrics
eval_path = os.path.join(config.DATA_DIR, "pipeline_eval_metrics.json")
with open(eval_path, 'w') as f:
    json.dump(metrics, f)
```

### Models (output/ directory)
```python
# Model weights go in outputs/, NOT Data/
model_output_dir = os.path.join(config.MODEL_OUTPUT_DIR, model_name)
os.makedirs(model_output_dir, exist_ok=True)
model.save_pretrained(model_output_dir)
```

---

## Folder Structure (Final)

```
Data/
├── [Original source files - DO NOT MODIFY]
│   ├── matched_data.pickle
│   ├── matched_data_wo_linebreaks.pickle
│   ├── fr_eng_correlation_data.csv
│   ├── preferential_translations.json
│   └── ... (other original files)
│
└── [Pipeline outputs - Safe to regenerate]
    ├── pipeline_matched_data.pickle
    ├── pipeline_df_with_features.pickle
    ├── pipeline_training_data.jsonl
    ├── pipeline_evaluation_results.json
    └── ... (other pipeline outputs)

outputs/
├── m2m100_418m/
│   ├── lora/
│   ├── merged_model.bin
│   └── tokenizer_config.json
└── ... (other models)
```

---

## Success Criteria

- ✅ DATA_STORAGE_GUIDE.md created (7.5 KB, 200+ lines)
- ✅ PLAN.md updated with data storage section
- ✅ STYLE.md updated with file naming conventions
- ✅ README.md updated with data storage section
- ✅ PROGRESS.md updated with key decision
- ✅ PLAN_SUMMARY.md updated with design decision
- ✅ DOCUMENTATION_INDEX.md updated (navigation & warnings)
- ✅ All files reference DATA_STORAGE_GUIDE.md as critical reading
- ✅ Checklist items include `pipeline_` prefix verification
- ✅ Implementation checkpoints include data naming verification

---

## Testing the Convention

**Before submitting code:**
```python
import os
import config

# Verify all output files use pipeline_ prefix
files = os.listdir(config.DATA_DIR)
for f in files:
    if f.endswith(('.pickle', '.jsonl', '.json')):
        if not f.startswith('pipeline_'):
            raise Exception(f"File must use pipeline_ prefix: {f}")

print("✓ All files follow naming convention")
```

---

## Notes for Implementation

### Critical Reminders
1. **Every file you save to Data/ must start with `pipeline_`**
2. **Original source files should NEVER be modified**
3. **Model files go in outputs/, not Data/**
4. **Use config.DATA_DIR for all data paths**
5. **If unsure, read DATA_STORAGE_GUIDE.md**

### Red Flags (Stop & Fix)
🚩 Saving to Data/ without `pipeline_` prefix
🚩 Overwriting files from source repos
🚩 Hardcoding Data/ paths (should use config.DATA_DIR)
🚩 Mixing model files with data files

### Safe to Delete
✓ Any file starting with `pipeline_` (it's regenerable)
✓ Files in outputs/ (models can be re-trained)

### NEVER Delete
✗ Original source data (no `pipeline_` prefix)
✗ fr_eng_correlation_data.csv
✗ Any original reference files

---

## Timeline

| When | What | Why |
|------|------|-----|
| Before Phase 1 | Read DATA_STORAGE_GUIDE.md | Prevent mistakes from day 1 |
| During coding | Prepend `pipeline_` | Protect source data |
| Code review | Check checklist | Verify convention followed |
| After running | Verify folder structure | Confirm no overwrites |

---

## Quick Reference

### Prepend `pipeline_` To:
- All `.pickle` files
- All `.jsonl` files
- All `.json` results files
- Any tabular data saved to Data/

### Do NOT Prepend To:
- Configuration files
- Source data from other repos
- Files in outputs/ directory
- Model checkpoints

### Location Rules:
- **Data/** ← intermediate data processing (pipeline_*)
- **outputs/** ← model weights & training logs
- **Pipeline/** ← code and documentation

---

## Documentation Checklist

- ✅ Data storage guide created (comprehensive)
- ✅ All markdown files updated with references
- ✅ Navigation guide emphasizes data safety
- ✅ Code examples provided for all phases
- ✅ Folder structure diagram included
- ✅ Rationale explained (data loss prevention)
- ✅ Verification checklist provided
- ✅ Special cases documented
- ✅ Integration with existing docs (cross-references)
- ✅ Ready for implementation teams

---

## Final Status

**CLARIFICATION COMPLETE** ✅

All documentation has been updated to clearly communicate:
1. ✅ Data files stored in Data/ folder
2. ✅ Pipeline outputs use `pipeline_` prefix
3. ✅ Source data must never be overwritten
4. ✅ Models go in outputs/ directory
5. ✅ Implementation teams know exact convention before coding

**Next Step**: Begin implementation with DATA_STORAGE_GUIDE.md as mandatory reading.

---

Generated: December 1, 2024
Update Type: Data Storage Conventions Clarification
Files Modified: 7
New Files: 1
Status: Ready for Implementation
