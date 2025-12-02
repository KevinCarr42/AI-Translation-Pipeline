import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_training_hyperparams_defaults():
    import config
    
    params = config.TRAINING_HYPERPARAMS
    
    print("Testing TRAINING_HYPERPARAMS defaults...")
    assert params['epochs'] == 1.0, f"epochs should be 1.0, got {params['epochs']}"
    assert params['lora_r'] == 32, f"lora_r should be 32, got {params['lora_r']}"
    assert params['lora_alpha'] == 64, f"lora_alpha should be 64, got {params['lora_alpha']}"
    assert params['batch_size'] == 8, f"batch_size should be 8, got {params['batch_size']}"
    assert params['learning_rate'] == 2e-4, f"learning_rate should be 2e-4, got {params['learning_rate']}"
    
    print("[OK] All TRAINING_HYPERPARAMS defaults match FineTuning repo")


def test_quantization_config():
    import config
    
    qconfig = config.QUANTIZATION_CONFIG
    
    print("Testing QUANTIZATION_CONFIG...")
    assert qconfig['use_qlora'] == False, f"use_qlora should be False (NO_QLORA=True), got {qconfig['use_qlora']}"
    assert qconfig['use_bfloat16'] == True, f"use_bfloat16 should be True (BF16=True), got {qconfig['use_bfloat16']}"
    assert qconfig['use_fp16'] == False, f"use_fp16 should be False (FP16=False), got {qconfig['use_fp16']}"
    
    print("[OK] QUANTIZATION_CONFIG matches finetune_all.py")


def test_model_specific_hyperparams():
    import config
    
    mshp = config.MODEL_SPECIFIC_HYPERPARAMS
    
    print("Testing MODEL_SPECIFIC_HYPERPARAMS...")
    
    expected_models = {
        "m2m100_418m": {"batch_size": 12, "learning_rate": 2e-4},
        "mbart50_mmt_fr": {"batch_size": 8, "learning_rate": 1.5e-4},
        "mbart50_mmt_en": {"batch_size": 8, "learning_rate": 1.5e-4},
        "opus_mt_en_fr": {"batch_size": 16, "learning_rate": 3e-4},
        "opus_mt_fr_en": {"batch_size": 16, "learning_rate": 3e-4},
    }
    
    for model_name, expected_params in expected_models.items():
        assert model_name in mshp, f"Model {model_name} not found in MODEL_SPECIFIC_HYPERPARAMS"
        actual = mshp[model_name]
        
        for param_name, expected_value in expected_params.items():
            actual_value = actual.get(param_name)
            assert actual_value == expected_value, \
                f"{model_name}.{param_name}: expected {expected_value}, got {actual_value}"
        
        # All models should have lora_r=32, lora_alpha=64
        assert actual.get('lora_r') == 32, f"{model_name}.lora_r should be 32"
        assert actual.get('lora_alpha') == 64, f"{model_name}.lora_alpha should be 64"
    
    print("[OK] All MODEL_SPECIFIC_HYPERPARAMS match finetune_all.py")


def test_models_config():
    import config
    
    models = config.MODELS
    
    print("Testing MODELS configuration...")
    
    expected_models = [
        "m2m100_418m",
        "mbart50_mmt_fr",
        "mbart50_mmt_en",
        "opus_mt_en_fr",
        "opus_mt_fr_en",
    ]
    
    for model_name in expected_models:
        assert model_name in models, f"Model {model_name} not found in MODELS"
        model_info = models[model_name]
        
        assert 'model_id' in model_info, f"{model_name} missing model_id"
        assert 'language_map' in model_info, f"{model_name} missing language_map"
        assert 'en' in model_info['language_map'], f"{model_name} missing 'en' in language_map"
        assert 'fr' in model_info['language_map'], f"{model_name} missing 'fr' in language_map"
    
    print("[OK] All MODELS configured correctly")


def test_data_paths():
    import config
    
    print("Testing data paths...")
    
    assert config.DATA_DIR == "../Data", f"DATA_DIR should be '../Data', got {config.DATA_DIR}"
    assert config.MODEL_OUTPUT_DIR == "../outputs", f"MODEL_OUTPUT_DIR should be '../outputs', got {config.MODEL_OUTPUT_DIR}"
    
    print("[OK] Data paths configured correctly")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CONFIGURATION CONSISTENCY TESTS")
    print("=" * 60 + "\n")
    
    try:
        test_training_hyperparams_defaults()
        test_quantization_config()
        test_model_specific_hyperparams()
        test_models_config()
        test_data_paths()
        
        print("\n" + "=" * 60)
        print("ALL CONFIGURATION TESTS PASSED [OK]")
        print("=" * 60 + "\n")
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}\n")
        sys.exit(1)
