import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_config_import():
    """Test config module import"""
    print("\nTesting config import...")
    try:
        import config
        assert hasattr(config, 'MODELS'), "config should have MODELS"
        assert hasattr(config, 'TRAINING_HYPERPARAMS'), "config should have TRAINING_HYPERPARAMS"
        assert hasattr(config, 'QUANTIZATION_CONFIG'), "config should have QUANTIZATION_CONFIG"
        print("  [OK] config module imports successfully")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import config: {e}")
        return False


def test_data_cleaning_import():
    """Test data_cleaning module import"""
    print("\nTesting data_cleaning import...")
    try:
        from data_cleaning import data_cleaning_pipeline
        assert callable(data_cleaning_pipeline), "data_cleaning_pipeline should be callable"
        print("  [OK] data_cleaning module imports successfully")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import data_cleaning: {e}")
        return False


def test_model_finetuning_imports():
    """Test model_finetuning module imports"""
    print("\nTesting model_finetuning imports...")
    try:
        from model_finetuning import (
            finetune_model,
            finetuning_pipeline,
            Preprocessor,
            M2MDataCollator,
            load_tokenizer_and_model,
            build_trainer,
        )
        print("  [OK] finetune_model imported")
        print("  [OK] finetuning_pipeline imported")
        print("  [OK] Preprocessor imported")
        print("  [OK] M2MDataCollator imported")
        print("  [OK] load_tokenizer_and_model imported")
        print("  [OK] build_trainer imported")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import model_finetuning: {e}")
        return False


def test_translate_imports():
    """Test translate module imports"""
    print("\nTesting translate imports...")
    try:
        from translate import (
            BaseTranslationModel,
            OpusTranslationModel,
            M2M100TranslationModel,
            MBART50TranslationModel,
            TranslationManager,
            split_by_sentences,
            split_by_paragraphs,
            translate_document,
            translation_pipeline,
            create_translator,
        )
        print("  [OK] BaseTranslationModel imported")
        print("  [OK] OpusTranslationModel imported")
        print("  [OK] M2M100TranslationModel imported")
        print("  [OK] MBART50TranslationModel imported")
        print("  [OK] TranslationManager imported")
        print("  [OK] split_by_sentences imported")
        print("  [OK] split_by_paragraphs imported")
        print("  [OK] translate_document imported")
        print("  [OK] translation_pipeline imported")
        print("  [OK] create_translator imported")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import translate: {e}")
        return False


def test_main_imports():
    """Test that main.py imports work"""
    print("\nTesting main.py imports...")
    try:
        from data_cleaning import data_cleaning_pipeline
        from model_finetuning import finetuning_pipeline
        from translate import translation_pipeline

        assert callable(data_cleaning_pipeline)
        assert callable(finetuning_pipeline)
        assert callable(translation_pipeline)

        print("  [OK] main.py can import all required functions")
        return True
    except Exception as e:
        print(f"  [FAIL] Failed to import for main.py: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MODULE IMPORT TESTS")
    print("=" * 60)

    results = []

    results.append(("config", test_config_import()))
    results.append(("data_cleaning", test_data_cleaning_import()))
    results.append(("model_finetuning", test_model_finetuning_imports()))
    results.append(("translate", test_translate_imports()))
    results.append(("main integration", test_main_imports()))

    print("\n" + "=" * 60)
    print("IMPORT TESTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")

    if passed == total:
        print("ALL IMPORT TESTS PASSED [OK]\n")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED [FAIL]\n")
        sys.exit(1)
