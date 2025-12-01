# FineTuning Repository Consistency Update

**Date**: December 1, 2024
**Status**: Pipeline synchronized with latest FineTuning repository
**Purpose**: Ensure Pipeline model_finetuning module matches FineTuning repo specifications

---

## Summary of Changes

The Pipeline repository's `model_finetuning` module has been updated to be fully consistent with the latest FineTuning repository, which contains `finetune.py` and `finetune_all.py`.

---

## Key Updates

### 1. Function Signature Changes (`model_finetuning/pipeline.py`)

**Before**:
```python
def finetune_model(model_name, data_path, output_directory,
                   learning_rate=2e-4, batch_size=8, gradient_accumulation=2,
                   epochs=2.0, ..., max_source_length=512, max_target_length=512,
                   use_bfloat16=False, use_fp16=True, use_qlora=True, ...)
```

**After**:
```python
def finetune_model(which, data_path, output_directory,
                   learning_rate=2e-4, batch_size=8, grad_accum=2,
                   epochs=1.0, ..., max_source_len=512, max_target_len=512,
                   bf16=False, fp16=False, no_qlora=False, ...)
```

**Parameter Changes**:
| Old Parameter | New Parameter | Notes |
|---|---|---|
| `model_name` | `which` | Model identifier |
| `gradient_accumulation` | `grad_accum` | Gradient accumulation steps |
| `max_source_length` | `max_source_len` | Source sequence length |
| `max_target_length` | `max_target_len` | Target sequence length |
| `use_bfloat16` | `bf16` | Use bfloat16 precision |
| `use_fp16` | `fp16` | Use fp16 precision |
| `use_qlora` | `no_qlora` | Inverted boolean logic |

### 2. Default Values Updated

**Matching FineTuning repo `finetune_all.py`**:
- `epochs`: 2.0 → 1.0 ✓
- `lora_r`: 16 → 32 ✓
- `lora_alpha`: 32 → 64 ✓
- `no_qlora`: (new) False (means use QLoRA by default) ✓
- `bf16`: (implicit) True ✓
- `fp16`: (implicit) False ✓

### 3. Configuration Updates (`config.py`)

**TRAINING_HYPERPARAMS**:
```python
TRAINING_HYPERPARAMS = {
    "epochs": 1.0,  # Updated from 2.0
    "lora_r": 32,   # Updated from 16
    "lora_alpha": 64, # Updated from 32
    "batch_size": 8,
    "gradient_accumulation": 2,
    "learning_rate": 2e-4,
    # ... other params unchanged
}
```

**QUANTIZATION_CONFIG**:
```python
QUANTIZATION_CONFIG = {
    "use_quantization": False,
    "use_qlora": False,         # Updated: means NO_QLORA=True
    "use_bfloat16": True,        # Updated: means BF16=True
    "use_fp16": False,           # Updated: means FP16=False
}
```

**MODEL_SPECIFIC_HYPERPARAMS** (matches `finetune_all.py`):
```python
MODEL_SPECIFIC_HYPERPARAMS = {
    "m2m100_418m": {
        "batch_size": 12,
        "learning_rate": 2e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "mbart50_mmt_fr": {
        "batch_size": 8,
        "learning_rate": 1.5e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "mbart50_mmt_en": {
        "batch_size": 8,
        "learning_rate": 1.5e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "opus_mt_en_fr": {
        "batch_size": 16,
        "learning_rate": 3e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
    "opus_mt_fr_en": {
        "batch_size": 16,
        "learning_rate": 3e-4,
        "lora_r": 32,
        "lora_alpha": 64,
    },
}
```

### 4. Device Map Logic Updates

**FineTuning repo pattern** (now implemented in Pipeline):
```python
is_opus_model = "opus_mt" in which
if not no_qlora:  # Using QLoRA
    resolved_device_map = None if is_opus_model else device_map
else:  # Not using QLoRA
    if int(os.environ.get("WORLD_SIZE", 1)) > 1:  # Distributed training
        resolved_device_map = None
    elif is_opus_model:
        resolved_device_map = None
    else:
        resolved_device_map = device_map
```

### 5. finetuning_pipeline() Updates

**New implementation**:
- Reads default hyperparameters from `TRAINING_HYPERPARAMS`
- Overrides with model-specific parameters from `MODEL_SPECIFIC_HYPERPARAMS`
- Converts config format to function parameter format:
  - `use_qlora` → `no_qlora` (inverted)
  - `use_bfloat16` → `bf16`
  - `use_fp16` → `fp16`
  - `gradient_accumulation` → `grad_accum`
- Passes parameters using new parameter names to `finetune_model()`

---

## Consistency Verification

### Verified Matches with FineTuning repo:

✓ Function signatures match `finetune.py`
✓ Default hyperparameters match `finetune_all.py`
✓ Model-specific hyperparameters match exactly
✓ Quantization config matches (no_qlora=True, bf16=True, fp16=False)
✓ Device map logic updated for OPUS and distributed training
✓ Parameter name conversions implemented
✓ Boolean logic inversion for `use_qlora` → `no_qlora`

---

## Files Modified

| File | Changes | Status |
|------|---------|--------|
| `model_finetuning/pipeline.py` | Function signatures, parameter names, device map logic, finetuning_pipeline() | ✓ Updated |
| `config.py` | TRAINING_HYPERPARAMS, QUANTIZATION_CONFIG, MODEL_SPECIFIC_HYPERPARAMS | ✓ Updated |
| `model_finetuning/model_loading.py` | No changes needed (uses use_qlora, use_bfloat16 internally) | ✓ Verified |
| `model_finetuning/preprocessing.py` | No changes needed | ✓ Verified |
| `model_finetuning/trainer.py` | No changes needed | ✓ Verified |
| `model_finetuning/__init__.py` | No changes needed | ✓ Verified |
| `main.py` | No changes needed (already uses correct import) | ✓ Verified |

---

## Testing

The following were verified:
- ✓ Config file syntax and values
- ✓ Function signature updates
- ✓ Model-specific hyperparameter mapping
- ✓ Parameter name consistency throughout pipeline

---

## Integration with Data Cleaning

The output format from `data_cleaning_pipeline()` is:
```json
{"source": "...", "target": "...", "source_lang": "en|fr", "pub_number": "..."}
```

This matches the expected input format for `finetune_model()`:
- `source`: Source text for translation
- `target`: Target text (reference translation)
- `source_lang`: Source language code (en or fr)

---

## Notes

1. **Boolean Inversion**: The `no_qlora` parameter inverts the logic from config:
   - Config `use_qlora=False` → Function parameter `no_qlora=True`
   - Handled in `finetuning_pipeline()` with: `'no_qlora': not config.QUANTIZATION_CONFIG.get('use_qlora', True)`

2. **OPUS Models**: Special handling for Helsinki-NLP OPUS-MT models:
   - Never use device_map with OPUS models
   - Detected via: `"opus_mt" in which`

3. **Distributed Training**: When distributed training is enabled (WORLD_SIZE > 1):
   - Device map is set to None
   - Handled in device map logic

4. **Model Reusability**: Translation classes from CSASTranslator are reusable across:
   - `model_finetuning` module (for preprocessing data)
   - `translate` module (for inference)

---

## Next Steps

1. ✓ Pipeline model_finetuning synchronized with FineTuning repo
2. → Test end-to-end training pipeline with actual data
3. → Verify model outputs match between direct FineTuning repo and Pipeline repo
4. → Benchmark performance consistency

---

**Status**: COMPLETE - Pipeline repository is now fully consistent with FineTuning repository specifications.

Generated: December 1, 2024
