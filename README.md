# Pipeline: End-to-End Translation Model Fine-Tuning

A modular Python pipeline for cleaning translation data, fine-tuning translation models, applying rule-based preferential translations, and evaluating translation quality.

## Overview

Pipeline consolidates five repositories (DataCleaning, FineTuning, RuleBasedTranslationMatching, CSASTranslator, and research notebooks) into a unified, production-ready system for:

1. **Data Cleaning**: Prepare raw text data for training
2. **Model Fine-Tuning**: Adapt pre-trained translation models to domain-specific terminology
3. **Preferential Translations**: Apply rule-based find-and-replace for consistent terminology
4. **Evaluation**: Assess translation quality using multiple metrics

## Directory Structure

```
Pipeline/
├── data_cleaning/              # Phase 1: Raw data → Training datasets
│   ├── __init__.py
│   ├── text_processing.py
│   ├── correlation.py
│   ├── feature_engineering.py
│   └── pipeline.py
├── model_finetuning/           # Phase 2: Training data → Fine-tuned models
│   ├── __init__.py
│   ├── training_config.py
│   ├── model_loading.py
│   ├── preprocessing.py
│   ├── trainer.py
│   └── pipeline.py
├── preferential_translations/  # Phase 3: Rule-based term replacement
│   ├── __init__.py
│   ├── token_utils.py
│   ├── replacements.py
│   └── pipeline.py
├── evaluation/                 # Phase 4: Quality metrics & comparison
│   ├── __init__.py
│   ├── metrics.py
│   └── comparison.py
├── main_pipeline.py            # Phase 5: Orchestrate all components
├── config.py                   # Global configuration & paths
├── requirements.txt
├── PLAN.md                     # Detailed implementation plan
├── PROGRESS.md                 # Development status & checkpoints
├── STYLE.md                    # Code conventions & guidelines
├── Cleanup.md                  # Dead code inventory & issues
└── README.md                   # This file
```

## Quick Start

### Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt

# Download required spacy models
python -m spacy download en_core_web_lg
python -m spacy download fr_core_news_lg
```

3. Configure file paths in `config.py`:
```python
DATA_DIR = "/path/to/your/data"
MODEL_DIR = "/path/to/your/models"
OUTPUT_DIR = "/path/to/your/outputs"
```

### Basic Usage

```python
from main_pipeline import run_full_pipeline

run_full_pipeline(
    raw_data_path="/path/to/raw/text",
    output_dir="/path/to/outputs",
    enable_data_cleaning=True,
    enable_finetuning=True,
    enable_preferential_translations=True,
    enable_evaluation=True
)
```

## Modules

### 1. Data Cleaning (`data_cleaning/`)

Prepares raw text data into structured training datasets.

**Input**: Raw JSON files with text content
**Output**: Pickle files with cleaned, aligned sentence pairs

**Key Features**:
- Language detection and text extraction
- Sentence alignment using similarity metrics
- Linguistic feature extraction (verb/noun ratios, entity counts, etc.)
- Train/test split

**Boolean Flags**:
- `skip_cleaning` - Skip text normalization
- `linebreaks` - Include/exclude linebreak splitting
- `add_features` - Compute linguistic features

**Example**:
```python
from data_cleaning.pipeline import prepare_training_data

dataframe = prepare_training_data(
    correlation_csv="fr_eng_correlation_data.csv",
    parsed_docs_folder="../ParsedPublications",
    skip_cleaning=False,
    linebreaks=True,
    add_features=True
)
```

### 2. Model Fine-Tuning (`model_finetuning/`)

Fine-tunes pre-trained translation models using LoRA adapters.

**Supported Models**:
- `m2m100_418m` - Facebook M2M100 (418M parameters)
- `mbart50_mmt_en` - mBART-50 (English→French)
- `mbart50_mmt_fr` - mBART-50 (French→English)
- `opus_mt_en_fr` - OPUS-MT (English→French)
- `opus_mt_fr_en` - OPUS-MT (French→English)

**Hyperparameters** (Optimized):
- Learning rate: 2e-4
- Batch size: 8
- Epochs: 2.0
- LoRA r=16, alpha=32, dropout=0.05
- Max sequence length: 512

**Example**:
```python
from model_finetuning.pipeline import finetune_models

finetune_models(
    data_path="training_data.jsonl",
    models=["m2m100_418m", "opus_mt_en_fr"],
    output_dir="./outputs",
    epochs=2.0,
    batch_size=8
)
```

### 3. Preferential Translations (`preferential_translations/`)

Applies rule-based find-and-replace to preserve domain-specific terminology.

**Token Types**:
- `SITE[0000-9999]` - Geographic locations
- `NOMENCLATURE[0000-9999]` - Scientific terminology
- `TAXON[0000-9999]` - Species/taxa names
- `ACRONYM[0000-9999]` - Acronyms and abbreviations

**Workflow**:
1. Replace terminology with tokens (preprocessing)
2. Translate tokenized text
3. Replace tokens with correct translations (postprocessing)

**Example**:
```python
from preferential_translations.pipeline import translate_with_replacements

translation = translate_with_replacements(
    source_text="...",
    source_language="en",
    target_language="fr",
    translations_file="all_translations.json",
    model=translator_model
)
```

### 4. Evaluation (`evaluation/`)

Assesses translation quality through multiple metrics.

**Metric Types**:
- **Similarity**: Cosine similarity between embeddings
- **Quality**: Fluency and accuracy assessment
- **Comparison**: Similarity between two translations
- **Rule-Based**: Validation against preferential translations

**Example**:
```python
from evaluation.metrics import calculate_similarity, assess_quality

similarity = calculate_similarity(english_text, french_text)
quality = assess_quality(source_text, translated_text)
```

## Data Storage Conventions

**Important**: All Pipeline-generated files must preserve original source data.

### Naming Rules
- **Pickle files**: Prepend with `pipeline_` (e.g., `pipeline_matched_data.pickle`)
- **Training data**: `pipeline_training_data.jsonl`
- **Evaluation results**: `pipeline_evaluation_results.json`
- **Location**: All saved to `Data/` folder (configured in config.py)

### Reason
Source repositories contain reference data. Pipeline creates intermediate files during processing. The `pipeline_` prefix clearly distinguishes Pipeline-generated files from source data, preventing accidental overwrites.

**Example**:
```python
# Correct - preserves original
output_path = os.path.join(config.DATA_DIR, "pipeline_matched_data.pickle")
dataframe.to_pickle(output_path)

# Wrong - overwrites original source
output_path = "matched_data_wo_linebreaks.pickle"  # Would overwrite!
```

---

## Configuration

Edit `config.py` to set:

```python
# File Paths
DATA_DIR = "./Data"
MODEL_DIR = "./models"
OUTPUT_DIR = "./outputs"
PARSED_DOCS_DIR = "../ParsedPublications"
CORRELATION_CSV_PATH = "fr_eng_correlation_data.csv"
TRAINING_DATA_PATH = os.path.join(DATA_DIR, "training_data.jsonl")
TRANSLATIONS_JSON_PATH = os.path.join(DATA_DIR, "all_translations.json")

# Model Configuration
MODELS = {
    "m2m100_418m": {...},
    "opus_mt_en_fr": {...},
    # ...
}

# Hyperparameters
TRAINING_HYPERPARAMS = {
    "learning_rate": 2e-4,
    "batch_size": 8,
    "epochs": 2.0,
    # ...
}

# Feature Flags
USE_QUANTIZATION = True
USE_QLORA = True
DEVICE_MAP = "auto"
```

## Code Style

Pipeline follows strict code conventions (see `STYLE.md`):

- **No docstrings or type hints**
- **Comments only for counterintuitive logic**
- **Full-word variable names** (except common loop vars: i, j, k)
- **Prefer if statements over try-except**
- **Clean, readable, idiomatic Python**
- **Code copied as-is from source repositories** (no refactoring)

## Development Progress

**Current Status**: Planning phase complete. See `PROGRESS.md` for implementation roadmap.

**Phases**:
1. ✓ Planning & architecture
2. Data Cleaning module (in progress)
3. Fine-Tuning module (pending)
4. Preferential Translations module (pending)
5. Evaluation module (pending)
6. Integration & documentation (pending)

## Documentation

- `PLAN.md` - Detailed architecture and implementation strategy
- `PROGRESS.md` - Development status and checkpoints
- `STYLE.md` - Code conventions and guidelines
- `Cleanup.md` - Dead code inventory and issues from source repos

## Requirements

- Python 3.9+
- PyTorch with CUDA support (GPU recommended)
- Transformers library
- Spacy language models (en_core_web_lg, fr_core_news_lg)
- Pandas, NumPy, SentenceTransformers

See `requirements.txt` for full dependencies.

## Source Repositories

Pipeline consolidates code from:

1. **DataCleaning** - Text extraction and sentence alignment
2. **FineTuning** - Model fine-tuning and training
3. **RuleBasedTranslationMatching** - Token-based terminology replacement
4. **CSASTranslator** - Translation orchestration and evaluation
5. **Research notebooks** - Exploratory analysis (not included in production)

See `Cleanup.md` for details on what was excluded and why.

## Known Limitations

1. Language classifier requires large spacy models
2. Fine-tuning requires significant GPU memory (8GB+ recommended)
3. Token validation is simple (all tokens replaced); advanced recovery possible
4. Evaluation metrics are analytical; human evaluation recommended for production

## Contributing

When adding new functionality:

1. Follow code style guidelines in `STYLE.md`
2. Keep modules self-contained and loosely coupled
3. Use `config.py` for all file paths
4. Update `PROGRESS.md` and `STYLE.md` as needed
5. Document any changes in relevant markdown files

## License

(To be specified by user)

## Contact

(To be specified by user)
