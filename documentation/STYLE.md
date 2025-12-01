# Pipeline Code Style & Guidelines

## Core Principles

Based on user instructions in .claude/CLAUDE.md:

1. **No Docstrings or Type Hints** - Absolutely never add them
2. **Comments Only When Counterintuitive** - Remove generic comments; preserve those explaining non-obvious logic
3. **Code Readability** - Write clean, readable, idiomatic Python
4. **Variable Names** - Use full-word names for new variables (not abbreviations like `df`, `msg`)
5. **If Over Try-Except** - Prefer if statements for error checking
6. **Minimize Nesting** - Never nest try-except blocks; keep try blocks short
7. **Preserve Existing Code** - When copying from source repos, maintain structure as-is
8. **No Over-Engineering** - Only add code that's directly requested or clearly necessary

---

## Code Organization

### Module Structure Template

```python
# data_cleaning/text_processing.py
import json
import re
import os
from pathlib import Path

# Global constants
ALLOWED_CHARS_WITH_NUMBERS = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
MIN_BLOCK_LENGTH = 10
MAX_BLOCK_LENGTH = 500

def clean_text(text, skip_cleaning=False):
    # Function body
    pass

def extract_text_from_single_file(json_file, target_language, clf, skip_cleaning=False, linebreaks=True):
    # Function body
    pass

class SomeClass:
    def __init__(self, param):
        self.param = param

    def method(self):
        # Method body
        pass
```

### File Organization

- **Imports**: Group by standard library, third-party, local
- **Constants**: Define at module level in UPPER_CASE
- **Functions**: Define in logical order (helpers before main functions)
- **Classes**: Group related classes; keep methods in logical order

---

## Variable Naming

### Acceptable Abbreviations (Common Conventions)

- `i, j, k` - Loop indices
- `n` - Number/length (in math-heavy code)
- `x, y, z` - Coordinates or generic values
- `df` - Only when working with pandas DataFrames and it's already standard
- `f` - File handles in context managers
- `e` - Exception variables
- `_` - Unused values

### Unacceptable Abbreviations (New Code)

- `msg` → `message`
- `cfg` → `config`
- `fn` → `function`
- `tok` → `token`
- `sent` → `sentence`
- `src` → `source`
- `tgt` → `target`

### Examples

Good:
```python
training_data = []
max_sequence_length = 512
similarity_threshold = 0.7
for index, row in enumerate(dataframe.iterrows()):
    source_text = row["source"]
    target_text = row["target"]
```

Avoid:
```python
train_data = []  # OK in context of "training"
max_seq_len = 512  # Too abbreviated
sim_thresh = 0.7  # Too abbreviated
for idx, row in enumerate(df.iterrows()):  # OK for loop variable
    src = row["source"]  # Too abbreviated
    tgt = row["target"]  # Too abbreviated
```

---

## Error Handling

### Correct Pattern

```python
def load_file(filepath):
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r') as file:
        data = json.load(file)
    return data
```

### Incorrect Patterns to Avoid

```python
# Don't use try-except for simple file checks
try:
    with open(filepath, 'r') as file:
        data = json.load(file)
except FileNotFoundError:
    return None
except json.JSONDecodeError:
    return None
```

```python
# Never nest try-except
try:
    try:
        something()
    except ValueError:
        handle_value_error()
except Exception:
    handle_general_error()
```

```python
# Never use else after except
try:
    result = compute()
except ValueError:
    result = None
else:
    process(result)
```

---

## Boolean Flags & Configuration

### Module-Level Flags

For features that can be toggled, use explicit flags at the top of functions:

```python
def run_data_cleaning(data_path, output_path, skip_cleaning=False, linebreaks=True, add_features=True):
    if skip_cleaning:
        # Skip text cleaning step
        pass

    if linebreaks:
        # Include linebreak splitting
        pass

    if add_features:
        # Compute linguistic features
        pass
```

### Global Configuration

Use config.py for paths and persistent settings:

```python
# config.py
import os

DATA_DIR = os.environ.get("DATA_DIR", "./Data")
MODEL_DIR = os.path.join(DATA_DIR, "models")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

USE_QUANTIZATION = True
USE_QLORA = True
DEVICE_MAP = "auto"

TRAINING_HYPERPARAMS = {
    "learning_rate": 2e-4,
    "batch_size": 8,
    "epochs": 2.0,
    "lora_r": 16,
    "lora_alpha": 32,
}
```

---

## Copying Code from Source Repos

### Guidelines

1. **Copy function logic as-is**: Don't refactor or improve when copying
2. **Adapt imports**: Update relative imports to fit Pipeline structure
3. **Remove notebook-specific code**: Cells, display statements, etc.
4. **Preserve variable names**: Keep original names unless there's a conflict
5. **Keep comments**: Preserve only comments that explain counterintuitive logic
6. **Test after copying**: Verify copied code works in new context

### Example: Copying from DataCleaning/generate_training_data.py

Before (original):
```python
def clean_text(text, skip_cleaning=False):
    allow_numbers = True

    if not skip_cleaning:
        if allow_numbers:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
        else:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ.,;:!?()'\"-]"
        text = re.sub(allowed_chars, ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

    return text
```

After (in Pipeline):
```python
def clean_text(text, skip_cleaning=False):
    allow_numbers = True

    if not skip_cleaning:
        if allow_numbers:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
        else:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ.,;:!?()'\"-]"
        text = re.sub(allowed_chars, ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

    return text
```

(Identical - no refactoring)

### When to Not Copy Code

- Hyperparameter sweeping code (use final hyperparams directly)
- Notebook-specific plotting/visualization
- Dead code marked with # TODO or # DEPRECATED
- Experimental features not in final product
- Code with incorrect file paths (refactor path logic into config.py)

---

## Data Structures

### Common Patterns

**Train/Test Split**:
```python
dataset_processed = {
    "train": processed_training_data,
    "eval": processed_eval_data
}
```

**Model Info Dictionary**:
```python
model_info = {
    "model_id": "facebook/m2m100_418M",
    "type": "seq2seq",
    "language_map": {"en": "en", "fr": "fr"},
    "restrict_source_language": "en"
}
```

**Token Mapping**:
```python
token_mapping = {
    "SITE0001": {
        "original_text": "Newfoundland",
        "category": "site",
        "translation": "Terre-Neuve"
    }
}
```

---

## Import Organization

```python
# Standard library (alphabetically)
import csv
import json
import logging
import math
import os
import re
import sys
import time
from pathlib import Path

# Third-party (alphabetically)
import numpy as np
import pandas as pd
import spacy
import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Local imports
from config import DATA_DIR, MODEL_DIR
from language_classifier import LanguageClassifier
```

---

## Testing Pattern

When adding new functionality, include basic validation:

```python
def process_data(input_path, output_path):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    data = load_data(input_path)

    if len(data) == 0:
        raise ValueError("Input data is empty")

    processed = transform(data)

    if len(processed) != len(data):
        raise ValueError("Data loss during processing")

    save_data(output_path, processed)
    return processed
```

---

## Comments Guidelines

### Include Comments For

- Counterintuitive logic: "threshold is 0.7, not 0.5, because [reason]"
- Non-obvious choices: "skip opus models on device_map because [compatibility issue]"
- Important caveats: "This assumes input text is already cleaned"
- Complex algorithms: Brief description of DP alignment logic

### Exclude Comments For

- Self-evident code: `result = clean_text(data)` doesn't need "clean the text"
- Parameter documentation: Use clear names instead
- State tracking: Use clear variable names
- Generic statements: "add feature to dataframe"

### Comment Style

```python
# This comment explains WHY something non-obvious is done this way
threshold = 0.7  # Skip lowscores to reduce noise during alignment

# Comments on own line for complex blocks
for i in range(1, n + 1):
    for j in range(1, m + 1):
        # DP recurrence: choose best of match, skip_fr, skip_en
        score_match = dp[i - 1, j - 1] + weights[i - 1, j - 1]
        score_skip_fr = dp[i - 1, j]
        score_skip_en = dp[i, j - 1]
        dp[i, j] = np.max([score_match, score_skip_fr, score_skip_en])
```

---

## File Naming Conventions

### Data Files
When saving intermediate results to the Data/ folder, always prepend with `pipeline_`:

```python
# When saving dataframes
dataframe.to_pickle(os.path.join(config.DATA_DIR, "pipeline_matched_data.pickle"))
dataframe.to_pickle(os.path.join(config.DATA_DIR, "pipeline_training_data.jsonl"))
dataframe.to_pickle(os.path.join(config.DATA_DIR, "pipeline_df_with_features.pickle"))

# When saving evaluation results
with open(os.path.join(config.DATA_DIR, "pipeline_evaluation_results.json"), 'w') as f:
    json.dump(results, f)
```

### Why This Matters
- **Preserves original data**: Source repo files remain untouched
- **Clarifies ownership**: `pipeline_*` files are generated by Pipeline, not source data
- **Enables safe re-runs**: Can run pipeline multiple times without overwriting
- **Parallel work**: Different agents can run experiments simultaneously

### Model Outputs
Model files go in `outputs/` directory, not Data/:
```
outputs/
├── m2m100_418m/
│   ├── lora/                    (LoRA weights)
│   ├── merged_model.bin         (merged weights)
│   ├── config.json
│   └── tokenizer_config.json
├── opus_mt_en_fr/
│   └── ...
```

---

## Summary Checklist

- [ ] No docstrings or type hints
- [ ] Full-word variable names (except common loop vars i, j, k)
- [ ] Comments only for counterintuitive logic
- [ ] If statements preferred over try-except
- [ ] No nested try-except blocks
- [ ] Code copied as-is from source repos (no refactoring)
- [ ] Boolean flags for feature toggling
- [ ] Constants in UPPER_CASE at module level
- [ ] Imports organized by library type
- [ ] File paths in config.py, not hardcoded
- [ ] Pipeline outputs prepended with `pipeline_` in Data/
- [ ] Model outputs go in outputs/ directory
- [ ] Clean, readable, idiomatic Python
