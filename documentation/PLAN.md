# Pipeline Repository Development Plan

## Project Overview

The Pipeline repository consolidates code from five source repositories into a unified, modular translation pipeline that can:
1. Clean raw text data and generate training/testing datasets
2. Fine-tune translation models using optimized hyperparameters
3. Apply rule-based preferential translations (find-and-replace with tokens)
4. Evaluate translation quality through multiple metrics

## Architecture

The Pipeline will be organized into the following modules:

```
Pipeline/
├── data_cleaning/
│   ├── __init__.py
│   ├── text_processing.py      (language classification, text extraction)
│   ├── correlation.py           (sentence alignment, similarity matrices)
│   ├── feature_engineering.py   (add features for data quality analysis)
│   └── pipeline.py              (orchestrate: raw data → training/test datasets)
│
├── model_finetuning/
│   ├── __init__.py
│   ├── training_config.py       (MODELS dict, hyperparameters)
│   ├── model_loading.py         (tokenizer & model loading, LoRA attachment)
│   ├── preprocessing.py         (data preprocessing, language mapping)
│   ├── trainer.py               (trainer setup & training execution)
│   └── pipeline.py              (orchestrate: training data → fine-tuned models)
│
├── preferential_translations/
│   ├── __init__.py
│   ├── token_utils.py           (token creation, naming conventions)
│   ├── replacements.py          (find-and-replace logic)
│   └── pipeline.py              (pre-translate replacements, post-translate reversions)
│
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py               (similarity, cosine, quality metrics)
│   └── comparison.py            (compare translations, detect mistranslations)
│
├── main_pipeline.py             (orchestrate all components)
├── requirements.txt
└── config.py                    (global configuration, file paths, flags)
```

## Implementation Phases

### Phase 1: Data Cleaning Module
**Source**: DataCleaning repo (generate_training_data.py) + FineTuning repo (add_features.py)

**Inputs**:
- Raw text files (JSON format with 'text' field)
- Correlation data (CSV with pub_number, filename_fr, filename_en)
- Spacy models (en_core_news_lg, fr_core_news_lg)

**Outputs**:
- Training dataset (pickle): columns [pub_number, fr, en, similarity, len_ratio, verb_ratio, noun_ratio, entity_ratio, clause_ratio]
- Test dataset (pickle): same format

**Key Functions**:
- `clean_text(text, skip_cleaning=False)` - remove non-alphanumeric chars
- `extract_text_from_single_file()` - extract single language from JSON
- `extract_both_languages_from_two_files()` - extract from paired files
- `extract_both_languages_from_single_file()` - extract both languages from single file
- `create_sentences()` - split text into sentences
- `create_similarity_matrix()` - use SentenceTransformer
- `align_sentences()` - dynamic programming alignment with threshold
- `add_features()` - attach linguistic features using spacy

**Data Flow**:
1. Load correlation CSV and parsed JSON files
2. Extract & clean text (language classification + text extraction)
3. Create sentences from text
4. Generate similarity matrix (SentenceTransformer embeddings)
5. Align sentences using DP algorithm
6. Add linguistic features
7. Split into train/test (80/20 or configurable)
8. Save as pickle files

**Boolean Flags**:
- `SKIP_CLEANING` - skip text cleaning
- `LINEBREAKS` - include/exclude linebreak splitting
- `SKIP_ABSTRACTS` - filter abstract-only translations
- `ADD_FEATURES` - compute linguistic features

---

### Phase 2: Model Fine-Tuning Module
**Source**: FineTuning repo (finetune_hyperparams.py, translate.py + merge_weights.py)

**Inputs**:
- Training data (JSONL): {source, target, source_lang}
- Pre-trained model IDs (or local paths)

**Outputs**:
- Fine-tuned LoRA weights (./outputs/[model_name]/lora/)
- Merged model (weights combined with base)
- Tokenizer (./outputs/[model_name]/)

**Models Supported**:
- `m2m100_418m`: facebook/m2m100_418M
- `mbart50_mmt_fr`: facebook/mbart-large-50-many-to-many-mmt (English source)
- `mbart50_mmt_en`: facebook/mbart-large-50-many-to-many-mmt (French source)
- `opus_mt_en_fr`: Helsinki-NLP/opus-mt-tc-big-en-fr
- `opus_mt_fr_en`: Helsinki-NLP/opus-mt-tc-big-fr-en

**Hyperparameters** (Chosen from phase 2 experimentation, no sweeping):
- Learning rate: 2e-4
- Batch size: 8
- Gradient accumulation: 2
- Epochs: 2.0
- LoRA r: 16, alpha: 32, dropout: 0.05
- Max sequence lengths: 512 (source & target)
- Validation ratio: 0.05
- Warmup ratio: 0.03
- Weight decay: 0.01
- Label smoothing: 0.1

**Key Functions**:
- `load_tokenizer_and_model()` - load with device mapping & quantization
- `attach_lora()` - attach LoRA adapters to model
- `Preprocessor.__call__()` - preprocess JSONL examples for training
- `M2MDataCollator` - special data collation for M2M100 models
- `build_trainer()` - construct Seq2SeqTrainer
- `finetune_model()` - orchestrate training

**Data Flow**:
1. Load JSONL training data
2. Filter by model (some models restrict source language)
3. Split into train/val
4. Load tokenizer and base model
5. Attach LoRA
6. Preprocess data (tokenization, language mapping)
7. Build trainer with appropriate data collator
8. Train and save LoRA weights + tokenizer
9. Merge weights with base model (using `merge_weights.py` logic)

**Boolean Flags**:
- `USE_QLORA` - apply QLoRA quantization
- `BF16` - use bfloat16 precision
- `FP16` - use float16 precision

---

### Phase 3: Preferential Translations Module
**Source**: RuleBasedTranslationMatching repo (finetune_replacements.py, text_processing.py)

**Inputs**:
- JSON file with preferential translations (structure: {translations: {category: {term: translation}}})
- Input text to translate

**Outputs**:
- Preprocessed text (tokens replacing preferred terms)
- Token mapping (token → {category, original_text, translation})
- Postprocessed translation (tokens reverted to translations)

**Token Naming Conventions**:
- `SITE[0000-9999]` - Locations (identical in EN & FR)
- `NOMENCLATURE[0000-9999]` - Scientific terminology (identical in EN & FR)
- `TAXON[0000-9999]` - Species/taxa (identical in EN & FR)
- `ACRONYM[0000-9999]` - Acronyms (EN "ACRONYM" ≈ FR "ACRONYME", minimal translation)

**Key Functions**:
- `load_translations()` - load JSON translation dictionary
- `build_term_index()` - create bidirectional lookup indices
- `find_translation_matches()` - locate terms in source & target
- `create_replacement_token()` - generate category-based tokens
- `replace_whole_word()` - regex-based word boundary replacement
- `preprocess_for_translation()` - replace terms with tokens (before translation)
- `postprocess_translation()` - replace tokens with translations (after translation)

**Data Flow**:

**Preprocessing (before translation)**:
1. Load translation dictionary
2. Build term indices (French → info, English → info)
3. For each source language, find matching terms
4. Replace terms with language-neutral tokens
5. Return token_mapping

**Postprocessing (after translation)**:
1. Receive translated text with tokens intact
2. For each token, retrieve translation from mapping
3. Replace tokens with appropriate translations
4. Validate all tokens were replaced (error handling with fallback)

**Boolean Flags**:
- `USE_REPLACEMENTS` - enable/disable preferential translations
- `VALIDATE_TOKENS` - check all tokens replaced before returning

---

### Phase 4: Evaluation Module
**Source**: CSASTranslator repo + existing evaluation scripts

**Inputs**:
- English text block(s)
- French text block(s)
- Optional: Reference translations for comparison

**Outputs**:
- Quality metrics (similarity scores, cosine similarity, BLEU-like metrics)
- Comparison results (mistranslation detection)

**Key Functions**:
- `cosine_similarity()` - compute similarity between embeddings
- `quality_score()` - assess translation fluency/accuracy
- `compare_translations()` - compare two document translations
- `detect_mistranslations()` - identify potential errors

**Metric Types**:
- **Similarity-based**: Compare embeddings of source & translation using cosine similarity
- **Quality-based**: Assess fluency, terminology accuracy, context preservation
- **Comparison-based**: Compute similarity between two translation outputs
- **Rule-based**: Check against preferential translation rules

**Boolean Flags**:
- `USE_SIMILARITY` - include cosine similarity metric
- `USE_QUALITY` - include quality assessment
- `USE_COMPARISON` - include comparative analysis

---

### Phase 5: Integration & Main Pipeline
**Source**: CSASTranslator repo architecture

**Purpose**: Orchestrate all modules into a unified pipeline

**Workflow**:
1. **Data Preparation**: Clean & prepare training/test data
2. **Model Training**: Fine-tune translation models
3. **Translation**: Apply preferential replacements + model inference + revert replacements
4. **Evaluation**: Assess translation quality
5. **Output**: Save results, metrics, logs

**Main Functions**:
- `run_data_cleaning()` - execute Phase 1
- `run_finetuning()` - execute Phase 2
- `run_translation()` - apply preferential translations + inference
- `run_evaluation()` - execute Phase 4
- `run_full_pipeline()` - execute all phases

**Configuration**:
- Global config.py with:
  - File paths (DATA_DIR, MODEL_DIR, OUTPUT_DIR)
  - Model selections
  - Feature flags for each module
  - Hyperparameter overrides

---

## Data Storage Conventions

**IMPORTANT**: Avoid overwriting existing files. Use these conventions:

### Folder Structure
```
Data/
├── [existing source files - DO NOT MODIFY]
└── pipeline_*  ← All Pipeline-generated files
```

### File Naming for Pipeline Outputs
- **Pickle files**: Prepend with `pipeline_` (e.g., `pipeline_matched_data.pickle`, `pipeline_df_with_features.pickle`)
- **JSONL training data**: `pipeline_training_data.jsonl`
- **Model outputs**: Store in `outputs/` (separate from Data/)
- **Evaluation results**: `pipeline_evaluation_results.json`

**Example**:
```python
# BAD - overwrites existing data
dataframe.to_pickle("matched_data_wo_linebreaks.pickle")

# GOOD - preserves original, creates pipeline version
dataframe.to_pickle("pipeline_matched_data_wo_linebreaks.pickle")
```

### Rationale
- Source repos contain original/reference data
- Pipeline creates intermediate files during processing
- Naming convention clarifies which files are Pipeline-generated
- Prevents accidental overwriting of source data
- Allows parallel experimentation without conflicts

---

## Copying Strategy

### Files to Copy (Grouped by Module)

**data_cleaning/**
- `DataCleaning/generate_training_data.py` → Copy key functions, reuse class structure
- `FineTuning/add_features.py` → Copy add_features() directly
- `DataCleaning/language_classifier/` → Copy entire module as-is

**model_finetuning/**
- `FineTuning/finetune_hyperparams.py` → Extract training logic, remove sweep code
- `FineTuning/create_jsonl.py` → Copy save_jsonl() function
- `FineTuning/merge_weights.py` → Copy weight merging logic
- `FineTuning/translate.py` → Copy model classes

**preferential_translations/**
- `RuleBasedTranslationMatching/finetune_replacements.py` → Copy replacement logic
- `RuleBasedTranslationMatching/text_processing.py` → Copy token utils
- `CSASTranslator/text_processing.py` → Copy preprocessing logic

**evaluation/**
- CSASTranslator evaluation code → Modularize metrics

---

## Code Style Guidelines

**Adherence to User Instructions**:
- No docstrings, type hints, or comments (except for counterintuitive logic)
- Clean, readable, idiomatic Python
- Preserve existing variable names when copying
- Use full-word variable names for new code (not abbreviations)
- Avoid nested try-except; prefer if statements for error checking
- Default to leaving existing code as-is when copying

**File Organization**:
- Each module is self-contained with `__init__.py`
- Functions are organized logically within files
- Boolean flags enable/disable features without modifying code
- Minimal cross-module dependencies; call each other as required

---

## Dead Code & Issues to Document

**Cleanup.md will track**:
1. Notebooks not included in final product
2. Unused functions from source repositories
3. File path/location errors from refactoring
4. Hyperparameter sweep code (removed)
5. Abandoned or experimental code

**Known Issues**:
- File paths in source repos hardcoded (e.g., `../Data/`) → Centralize in config.py
- Multiple versions of similar functions → Consolidate to single implementation
- Notebook-specific code → Refactor into reusable functions
- Language classifier import path → Document in config

---

## Markdown Documentation Files

**PLAN.md** (this file)
- High-level architecture & phase breakdown
- Data flow diagrams (text-based)
- Implementation strategy

**PROGRESS.md**
- Track completed phases
- Note challenges & solutions
- Link to specific code implementations

**Cleanup.md**
- Dead code inventory
- Path/reference errors
- Lessons learned

**STYLE.md**
- Code conventions for Pipeline
- Module structure template
- Copy-paste guidelines to maintain consistency

**README.md**
- Quick start guide
- Module descriptions
- Usage examples

---

## Testing & Validation Strategy

**Per-Phase Testing**:
1. **Data Cleaning**: Verify output pickle structure, feature columns, data quality checks
2. **Fine-tuning**: Verify training completes, weights saved, model loads successfully
3. **Preferential Translations**: Test token replacement/reversion, edge cases (capitalization, punctuation)
4. **Evaluation**: Test metrics computation on sample text
5. **Integration**: End-to-end pipeline test with small dataset

**Validation Checkpoints**:
- Output formats match expected schema
- No data loss during transformations
- Model inference produces valid translations
- All modules can be toggled on/off via flags

---

## Implementation Order

1. **Setup Phase**: Create directory structure, config.py, requirements.txt
2. **Phase 1 (Data Cleaning)**: Copy functions, test with sample data
3. **Phase 2 (Fine-tuning)**: Implement training pipeline, test model loading
4. **Phase 3 (Preferential Translations)**: Implement token replacement/reversion
5. **Phase 4 (Evaluation)**: Implement metrics & comparison functions
6. **Phase 5 (Integration)**: Create main_pipeline.py orchestrator
7. **Documentation**: Write PROGRESS.md, Cleanup.md, STYLE.md, README.md
8. **Final Testing**: End-to-end validation with real data

---

## Notes

- **Hyperparameter Selection**: Do NOT include sweep code. Use final chosen hyperparameters directly.
- **Data Paths**: Centralize all paths in config.py to avoid hardcoding.
- **Model Paths**: Support both remote (HuggingFace) and local paths.
- **Modular Design**: Each module should work independently with clear input/output.
- **Reusability**: Metrics & evaluation functions should integrate into loops or standalone.
- **De-coupling**: Minimize dependencies between modules; use flags for optional features.
- **Backward Compatibility**: Don't modify source repositories; only add to Pipeline.
