# Data Storage & File Naming Guide

## Overview

This guide clarifies data storage conventions for the Pipeline project to prevent accidental overwriting of source data while enabling efficient Pipeline processing.

---

## Core Principle

**All Pipeline-generated files must be clearly distinguished from source data files.**

---

## Folder Structure

```
Project Root (C:\Users\CARRK\Documents\Repositories\AI\)
│
├── Data/                           ← All data files (input & output)
│   ├── [Source repo files]         ← Original data (DO NOT MODIFY)
│   │   ├── matched_data.pickle
│   │   ├── matched_data_wo_linebreaks.pickle
│   │   ├── fr_eng_correlation_data.csv
│   │   ├── preferential_translations.json
│   │   └── ... (other original files)
│   │
│   └── pipeline_*                  ← Pipeline outputs (safe to regenerate)
│       ├── pipeline_matched_data.pickle
│       ├── pipeline_df_with_features.pickle
│       ├── pipeline_training_data.jsonl
│       ├── pipeline_evaluation_results.json
│       └── ... (other pipeline outputs)
│
├── outputs/                        ← Model weights & training logs
│   ├── m2m100_418m/
│   │   ├── lora/                   (LoRA adapter weights)
│   │   ├── merged_model.bin        (merged weights)
│   │   ├── tokenizer_config.json
│   │   └── console_output.txt      (training log)
│   ├── opus_mt_en_fr/
│   │   └── ... (same structure)
│   └── ... (other models)
│
└── [Source Repositories - UNCHANGED]
    ├── DataCleaning/
    ├── FineTuning/
    ├── RuleBasedTranslationMatching/
    ├── CSASTranslator/
    └── Pipeline/                   ← This repo
```

---

## File Naming Convention

### Rule 1: Pipeline Outputs in Data/ Use `pipeline_` Prefix

**Format**: `pipeline_[descriptive_name].[extension]`

**Examples**:
```
✓ CORRECT:
  - pipeline_matched_data.pickle
  - pipeline_df_with_features.pickle
  - pipeline_training_data.jsonl
  - pipeline_evaluation_results.json
  - pipeline_token_mapping.json

✗ WRONG:
  - matched_data.pickle              (overwrites original!)
  - training_data.jsonl              (vague source)
  - evaluation.json                  (missing prefix)
```

### Rule 2: Model Outputs Go in outputs/ Directory

**Location**: `/outputs/[model_name]/`

**Examples**:
```
/outputs/m2m100_418m/
  ├── lora/                          (LoRA weights from finetuning)
  ├── merged_model.bin               (merged base + LoRA)
  ├── config.json
  ├── tokenizer_config.json
  └── console_output.txt             (training log)

/outputs/opus_mt_en_fr/
  ├── [same structure]
```

### Rule 3: Never Modify Source Data

**Source files** (in Data/ from original repos):
```
✗ DO NOT OVERWRITE:
  - matched_data.pickle              (Original from DataCleaning)
  - matched_data_wo_linebreaks.pickle (Original from DataCleaning)
  - df_with_features.pickle          (Original from FineTuning)
  - training_data.jsonl              (Original from FineTuning)
  - fr_eng_correlation_data.csv      (Original from DataCleaning)
  - preferential_translations.json    (Original from RuleBasedTranslationMatching)
  - all_translations.json            (Original from CSASTranslator)

✓ CREATE INSTEAD:
  - pipeline_[name].pickle           (Pipeline version)
```

---

## Implementation Examples

### Example 1: Data Cleaning Output

**Source Code**:
```python
# config.py defines DATA_DIR
import config
import os

def save_training_data(dataframe, output_name):
    # CORRECT: Prepend pipeline_
    output_path = os.path.join(config.DATA_DIR, f"pipeline_{output_name}.pickle")
    dataframe.to_pickle(output_path)
    return output_path

# Usage in data_cleaning/pipeline.py
training_df = prepare_training_data(...)
save_training_data(training_df, "matched_data_wo_linebreaks")
# Saves to: Data/pipeline_matched_data_wo_linebreaks.pickle
```

### Example 2: Adding Features

**Source Code**:
```python
def add_features_and_save(dataframe, output_name):
    # Add features
    featured_df = add_features(dataframe)

    # CORRECT: Prepend pipeline_
    output_path = os.path.join(config.DATA_DIR, f"pipeline_{output_name}.pickle")
    featured_df.to_pickle(output_path)

    return featured_df

# Usage
training_df = load_data("pipeline_matched_data_wo_linebreaks.pickle")
featured_df = add_features_and_save(training_df, "df_with_features")
# Saves to: Data/pipeline_df_with_features.pickle
```

### Example 3: Creating Training Data JSONL

**Source Code**:
```python
def create_training_jsonl(dataframe, output_name):
    import json

    # CORRECT: Prepend pipeline_
    output_path = os.path.join(config.DATA_DIR, f"pipeline_{output_name}.jsonl")

    with open(output_path, "w", encoding="utf-8") as f:
        for i, row in enumerate(dataframe.itertuples(index=False)):
            f.write(json.dumps({
                "source": f"{row.en}",
                "target": f"{row.fr}",
                "source_lang": "en",
            }, ensure_ascii=False) + "\n")
            f.write(json.dumps({
                "source": f"{row.fr}",
                "target": f"{row.en}",
                "source_lang": "fr",
            }, ensure_ascii=False) + "\n")

    return output_path

# Usage
create_training_jsonl(featured_df, "training_data")
# Saves to: Data/pipeline_training_data.jsonl
```

### Example 4: Saving Evaluation Results

**Source Code**:
```python
def save_evaluation_results(results_dict, output_name):
    import json

    # CORRECT: Prepend pipeline_
    output_path = os.path.join(config.DATA_DIR, f"pipeline_{output_name}.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_dict, f, ensure_ascii=False, indent=2)

    return output_path

# Usage
results = evaluate_translation_quality(...)
save_evaluation_results(results, "evaluation_results")
# Saves to: Data/pipeline_evaluation_results.json
```

---

## Loading Data

### Load Original Source Data (Read-Only)

```python
import pandas as pd
import config
import os

# Load original data for processing
original_data = pd.read_pickle(
    os.path.join(config.DATA_DIR, "matched_data_wo_linebreaks.pickle")
)

# Do NOT modify this dataframe in-place; create a copy if needed
processed_data = original_data.copy()
# ... process ...
```

### Load Pipeline-Generated Data (Safe to Modify)

```python
# Load pipeline outputs (safe to overwrite if re-running)
pipeline_data = pd.read_pickle(
    os.path.join(config.DATA_DIR, "pipeline_matched_data_wo_linebreaks.pickle")
)

# OK to modify and re-save
pipeline_data['new_column'] = ...
pipeline_data.to_pickle(
    os.path.join(config.DATA_DIR, "pipeline_matched_data_with_new_column.pickle")
)
```

---

## Why This Matters

### Problem: Without Convention

```
Data/
├── matched_data.pickle                    ← Original (reference)
├── matched_data.pickle                    ← Pipeline run 1 (OVERWRITES!)
├── matched_data.pickle                    ← Pipeline run 2 (OVERWRITES AGAIN!)
└── Can't recover original data!
```

**Risk**: Data loss, inability to compare different pipeline versions, confusion about which version is which.

### Solution: With Convention

```
Data/
├── matched_data.pickle                    ← Original (safe, reference)
├── pipeline_matched_data.pickle           ← Pipeline run 1 (safe to regenerate)
├── pipeline_matched_data_v2.pickle        ← Pipeline run 2 (different experiment)
├── pipeline_matched_data_feature_exp.pickle ← Pipeline run 3 (feature experiment)
└── All versions coexist safely!
```

**Benefits**:
- Original data never at risk
- Can compare different pipeline versions
- Safe to re-run and experiment
- Clear ownership (what's source vs. what's generated)

---

## Special Cases

### Case 1: Reading Input Data (Source Repos)

**These files exist already:**
```python
# Read source data without prefix
training_df = pd.read_pickle(
    os.path.join(config.DATA_DIR, "matched_data_wo_linebreaks.pickle")
)

# Read source CSV
correlation_df = pd.read_csv(
    os.path.join(config.DATA_DIR, "fr_eng_correlation_data.csv")
)
```

### Case 2: Multiple Pipeline Versions

**If you want to keep multiple versions:**
```python
# Version with different hyperparams
output_path = os.path.join(
    config.DATA_DIR,
    f"pipeline_df_with_features_lr2e4.pickle"
)

# Version with different feature set
output_path = os.path.join(
    config.DATA_DIR,
    f"pipeline_df_with_linguistic_features.pickle"
)
```

### Case 3: Temporary Intermediate Files

**If creating many intermediate files:**
```python
# Option A: Use pipeline_ prefix
pipeline_intermediate_1.pickle
pipeline_intermediate_2.pickle

# Option B: Clean up after
temp_file = os.path.join(config.DATA_DIR, "pipeline_temp.pickle")
df.to_pickle(temp_file)
# ... use temp_file ...
os.remove(temp_file)  # Clean up
```

---

## Data Pipeline Flow Example

```
Source Data                 Pipeline Steps                 Outputs
─────────────              ──────────────                 ────────

fr_eng_correlation.csv ──┐
                         ├──→ Data Cleaning ──→ pipeline_matched_data.pickle
matched_data_wo_         │
linebreaks.pickle ────────

pipeline_matched_data.pickle ──→ Feature Engineering ──→ pipeline_df_with_features.pickle

pipeline_df_with_features.pickle ──→ Create JSONL ──→ pipeline_training_data.jsonl

pipeline_training_data.jsonl ──→ Fine-tuning ──→ outputs/m2m100_418m/merged_model.bin

pipeline_training_data.jsonl ──→ Evaluation ──→ pipeline_evaluation_results.json
(with model)
```

---

## Checking Your Work

### Before Committing Code

**Checklist**:
- [ ] All `to_pickle()` calls use `pipeline_` prefix
- [ ] All JSON/JSONL saves use `pipeline_` prefix
- [ ] No overwrites of source data files
- [ ] All paths use `config.DATA_DIR`
- [ ] Can safely re-run without data loss

### After Running Code

**Verify Data Folder**:
```python
import os
import config

files = os.listdir(config.DATA_DIR)
for f in files:
    if not f.startswith('pipeline_') and f.endswith('.pickle'):
        print(f"⚠️  WARNING: Non-pipeline pickle file: {f}")
        print("   Is this intentional?")

print("\n✓ Pipeline files:")
for f in files:
    if f.startswith('pipeline_'):
        print(f"  - {f}")
```

---

## Configuration (config.py)

```python
import os

# Data directory - all data files stored here
DATA_DIR = os.environ.get("DATA_DIR", "./Data")

# Model output directory - separate from data
MODEL_OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./outputs")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
```

---

## Summary

| Aspect | Rule | Example |
|--------|------|---------|
| **Source data** | Read-only | `matched_data_wo_linebreaks.pickle` |
| **Pipeline outputs** | Prepend `pipeline_` | `pipeline_matched_data.pickle` |
| **Data location** | `Data/` folder | `config.DATA_DIR` |
| **Model location** | `outputs/` folder | `outputs/m2m100_418m/` |
| **Never do** | Overwrite source files | ✗ Save to original name |
| **Always do** | Use `pipeline_` prefix | ✓ Save with prefix |

---

## Questions?

- **"Where do I save my output?"** → `config.DATA_DIR` with `pipeline_` prefix
- **"What if I want multiple versions?"** → Add version identifier after `pipeline_`: `pipeline_name_v2.pickle`
- **"Is it OK to delete pipeline_ files?"** → Yes! They're regenerable. Source files are not.
- **"What about model files?"** → Go in `outputs/` directory, not `Data/`
- **"Can I modify original source files?"** → NO! Read them but don't save over them.

---

**Remember**: The `pipeline_` prefix is your safety net. Use it consistently on every file your code saves to the Data/ folder.
