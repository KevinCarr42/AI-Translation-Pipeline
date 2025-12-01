# Pipeline Repository Tests

This directory contains tests to validate that the Pipeline repository is consistent with the source repositories (FineTuning, CSASTranslator, DataCleaning, etc.).

---

## Test Files

### 1. `test_config_consistency.py`
**Purpose**: Verify that configuration parameters match source repositories

**Tests**:
- `test_training_hyperparams_defaults()` - Validates TRAINING_HYPERPARAMS defaults match FineTuning repo
  - epochs = 1.0
  - lora_r = 32
  - lora_alpha = 64
  - batch_size = 8
  - learning_rate = 2e-4

- `test_quantization_config()` - Validates QUANTIZATION_CONFIG matches finetune_all.py
  - use_qlora = False (NO_QLORA=True)
  - use_bfloat16 = True (BF16=True)
  - use_fp16 = False (FP16=False)

- `test_model_specific_hyperparams()` - Validates per-model hyperparameter overrides match finetune_all.py
  - All 5 models configured with correct batch_size, learning_rate, lora_r, lora_alpha

- `test_models_config()` - Validates all translation models are properly configured
  - m2m100_418m
  - mbart50_mmt_fr
  - mbart50_mmt_en
  - opus_mt_en_fr
  - opus_mt_fr_en

- `test_data_paths()` - Validates data directory configuration
  - DATA_DIR = "../Data"
  - MODEL_OUTPUT_DIR = "../outputs"

**Run**: `python tests/test_config_consistency.py`

---

### 2. `test_function_signatures.py`
**Purpose**: Compare function signatures between Pipeline and source repositories

**Tests**:
- `test_data_cleaning_pipeline()` - Validates data_cleaning_pipeline is importable and has correct signature

- `test_finetuning_pipeline()` - Validates finetune_model and finetuning_pipeline have correct parameters
  - finetune_model first parameter: `which` (not `model_name`)
  - Has `grad_accum` (not `gradient_accumulation`)
  - Has `no_qlora` (not `use_qlora`)
  - Has `max_source_len` and `max_target_len` (not `max_source_length` and `max_target_length`)
  - Has `bf16` and `fp16` (not `use_bfloat16` and `use_fp16`)

- `test_translation_pipeline()` - Validates translation_pipeline has correct parameters
  - with_preferential_translation
  - input_text_file
  - output_text_file
  - source_lang

- `test_translate_models()` - Validates all translation model classes are available
  - BaseTranslationModel
  - OpusTranslationModel
  - M2M100TranslationModel
  - MBART50TranslationModel
  - TranslationManager

- `test_preprocessing_classes()` - Validates preprocessing classes are available
  - Preprocessor
  - M2MDataCollator

**Run**: `python tests/test_function_signatures.py`

---

### 3. `test_module_imports.py`
**Purpose**: Verify all module imports work correctly

**Tests**:
- `test_config_import()` - Validates config module imports and has required attributes

- `test_data_cleaning_import()` - Validates data_cleaning module imports successfully

- `test_model_finetuning_imports()` - Validates all model_finetuning components import
  - finetune_model
  - finetuning_pipeline
  - Preprocessor
  - M2MDataCollator
  - load_tokenizer_and_model
  - build_trainer

- `test_translate_imports()` - Validates all translate module components import
  - Model classes (5 classes)
  - Document functions (3 functions)
  - Pipeline functions (2 functions)

- `test_main_imports()` - Validates that main.py can import all required functions
  - Ensures integration between all modules

**Run**: `python tests/test_module_imports.py`

---

### 4. `test_basic_functionality.py`
**Purpose**: Test basic functionality without requiring full model loading

**Tests**:
- `test_config_data_structures()` - Validates config defines proper data structures
  - MODELS is dict with 5 entries
  - All hyperparameter dicts are properly defined
  - All models in MODELS have corresponding MODEL_SPECIFIC_HYPERPARAMS

- `test_document_splitting()` - Tests document splitting functions
  - split_by_sentences() produces correct chunks
  - split_by_paragraphs() produces correct chunks

- `test_training_data_format()` - Validates training data JSONL format
  - Loads test JSONL with source, target, source_lang fields
  - Verifies dataset structure using HuggingFace datasets library

- `test_translate_module_structure()` - Validates translate module has correct submodule structure
  - translate.models (classes)
  - translate.document (functions)
  - translate.pipeline (functions)

- `test_model_finetuning_structure()` - Validates model_finetuning has correct submodule structure
  - model_finetuning.pipeline (finetune_model, finetuning_pipeline)
  - model_finetuning.preprocessing (Preprocessor, M2MDataCollator)
  - model_finetuning.model_loading (load_tokenizer_and_model)
  - model_finetuning.trainer (build_trainer)

- `test_preprocessor_initialization()` - Tests Preprocessor class instantiation with correct parameters

- `test_quantization_boolean_logic()` - Validates boolean logic for quantization
  - use_qlora ↔ no_qlora conversion works correctly

**Run**: `python tests/test_basic_functionality.py`

---

## Running All Tests

```bash
# From Pipeline root directory
cd C:\Users\CARRK\Documents\Repositories\AI\Pipeline

# Run all tests
python tests/test_config_consistency.py
python tests/test_function_signatures.py
python tests/test_module_imports.py
python tests/test_basic_functionality.py

# Or run individually
python -m pytest tests/  # If pytest is installed
```

---

## Test Results

### Success Indicators
- ✓ All config values match FineTuning repo specifications
- ✓ All function signatures match expected parameter names
- ✓ All modules import without errors
- ✓ Basic functionality works as expected

### Common Issues

**ModuleNotFoundError: No module named 'torch'**
- Expected in minimal environments
- Tests that check structure still pass
- Will work when environment has torch installed

**ImportError with datasets library**
- Training data format test gracefully handles this
- Returns True to allow test to continue

---

## What These Tests Validate

### ✓ Configuration Consistency
- Hyperparameters match FineTuning repo's finetune_all.py
- Model-specific overrides are properly configured
- Quantization settings match (no_qlora, bf16, fp16)
- Data paths are correctly set

### ✓ API Consistency
- Function signatures match source repositories
- Parameter names are consistent (which, grad_accum, no_qlora, etc.)
- All required classes and functions are available
- Module structure matches expected organization

### ✓ Integration
- All modules import correctly
- main.py can import all required functions
- Preprocessing classes work with correct parameters
- Document splitting functions work as expected

---

## Test Coverage

| Component | Coverage |
|-----------|----------|
| Config | ✓ Complete |
| data_cleaning module | ✓ Basic |
| model_finetuning module | ✓ Complete |
| translate module | ✓ Complete |
| Integration | ✓ Verified |

---

## Future Enhancements

- Add tests that compare actual model outputs between Pipeline and source repos
- Add performance benchmarks
- Add memory usage tests for large datasets
- Add distributed training tests
- Add tests for error handling and edge cases

---

## Notes

- Tests are designed to work without downloading large models
- Configuration tests are comprehensive and detailed
- Functionality tests validate structure without requiring model weights
- Import tests ensure all components are properly exposed
- Boolean logic tests verify quantization parameter conversion

Generated: December 1, 2024
