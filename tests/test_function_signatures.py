import sys
import os
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def get_function_params(func):
    """Extract function parameter names and defaults"""
    sig = inspect.signature(func)
    params = {}
    for param_name, param in sig.parameters.items():
        default = param.default if param.default != inspect.Parameter.empty else "NO_DEFAULT"
        params[param_name] = default
    return params


def compare_signatures(func1, func2, func_name):
    """Compare two function signatures"""
    params1 = get_function_params(func1)
    params2 = get_function_params(func2)

    print(f"  {func_name}:")
    print(f"    Pipeline params: {list(params1.keys())[:5]}... (first 5)")
    print(f"    Source params:   {list(params2.keys())[:5]}... (first 5)")

    if params1 == params2:
        print(f"    [OK] Signatures match exactly")
        return True
    else:
        only_in_pipeline = set(params1.keys()) - set(params2.keys())
        only_in_source = set(params2.keys()) - set(params1.keys())

        if only_in_pipeline:
            print(f"    ! Pipeline has extra params: {only_in_pipeline}")
        if only_in_source:
            print(f"    ! Source has extra params: {only_in_source}")

        return False


def test_data_cleaning_pipeline():
    """Compare data_cleaning_pipeline with DataCleaning repo"""
    print("\nTesting data_cleaning_pipeline...")

    try:
        from data_cleaning import data_cleaning_pipeline
        print("  [OK] data_cleaning_pipeline imported successfully")

        sig = inspect.signature(data_cleaning_pipeline)
        params = list(sig.parameters.keys())

        assert len(params) > 0, "data_cleaning_pipeline should have parameters"
        print(f"  [OK] data_cleaning_pipeline has {len(params)} parameters")

        return True
    except ImportError as e:
        print(f"  ! Could not import: {e}")
        return False
    except Exception as e:
        print(f"  ! Error: {e}")
        return False


def test_finetuning_pipeline():
    """Compare finetuning_pipeline with FineTuning repo"""
    print("\nTesting finetuning_pipeline...")

    try:
        from model_finetuning import finetune_model, finetuning_pipeline

        sig = inspect.signature(finetune_model)
        params = list(sig.parameters.keys())

        print(f"  finetune_model parameters (first 8):")
        for i, p in enumerate(params[:8]):
            print(f"    {i+1}. {p}")

        # Verify key parameters match FineTuning repo
        assert params[0] == "which", f"First param should be 'which', got {params[0]}"
        assert "grad_accum" in params, "Should have 'grad_accum' parameter"
        assert "no_qlora" in params, "Should have 'no_qlora' parameter"
        assert "max_source_len" in params, "Should have 'max_source_len' parameter"
        assert "max_target_len" in params, "Should have 'max_target_len' parameter"
        assert "bf16" in params, "Should have 'bf16' parameter"
        assert "fp16" in params, "Should have 'fp16' parameter"

        print("  [OK] finetune_model has correct parameter names matching FineTuning repo")

        # Check finetuning_pipeline
        sig2 = inspect.signature(finetuning_pipeline)
        params2 = list(sig2.parameters.keys())
        print(f"  finetuning_pipeline parameters: {params2}")

        assert "data_path" in params2, "finetuning_pipeline should have 'data_path'"
        assert "model_names" in params2, "finetuning_pipeline should have 'model_names'"

        print("  [OK] finetuning_pipeline signature is correct")

        return True
    except ImportError as e:
        print(f"  ! Could not import: {e}")
        return False
    except AssertionError as e:
        print(f"  [FAIL] Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ! Error: {e}")
        return False


def test_translation_pipeline():
    """Verify translation_pipeline from translate module"""
    print("\nTesting translation_pipeline...")

    try:
        from translate import translation_pipeline

        sig = inspect.signature(translation_pipeline)
        params = list(sig.parameters.keys())

        print(f"  translation_pipeline parameters: {params}")

        assert "with_preferential_translation" in params, "Should have 'with_preferential_translation'"
        assert "input_text_file" in params, "Should have 'input_text_file'"
        assert "output_text_file" in params, "Should have 'output_text_file'"
        assert "source_lang" in params, "Should have 'source_lang'"

        print("  [OK] translation_pipeline signature is correct")

        return True
    except ImportError as e:
        print(f"  ! Could not import: {e}")
        return False
    except AssertionError as e:
        print(f"  [FAIL] Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ! Error: {e}")
        return False


def test_translate_models():
    """Verify translation model classes are available"""
    print("\nTesting translation model classes...")

    try:
        from translate import (
            BaseTranslationModel,
            OpusTranslationModel,
            M2M100TranslationModel,
            MBART50TranslationModel,
            TranslationManager,
        )

        models = [
            ("BaseTranslationModel", BaseTranslationModel),
            ("OpusTranslationModel", OpusTranslationModel),
            ("M2M100TranslationModel", M2M100TranslationModel),
            ("MBART50TranslationModel", MBART50TranslationModel),
            ("TranslationManager", TranslationManager),
        ]

        for name, cls in models:
            assert inspect.isclass(cls), f"{name} should be a class"
            print(f"  [OK] {name} is available")

        return True
    except ImportError as e:
        print(f"  ! Could not import: {e}")
        return False
    except AssertionError as e:
        print(f"  [FAIL] Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ! Error: {e}")
        return False


def test_preprocessing_classes():
    """Verify preprocessing classes are available"""
    print("\nTesting preprocessing classes...")

    try:
        from model_finetuning import Preprocessor, M2MDataCollator

        assert inspect.isclass(Preprocessor), "Preprocessor should be a class"
        assert inspect.isclass(M2MDataCollator), "M2MDataCollator should be a class"

        print("  [OK] Preprocessor class is available")
        print("  [OK] M2MDataCollator class is available")

        return True
    except ImportError as e:
        print(f"  ! Could not import: {e}")
        return False
    except AssertionError as e:
        print(f"  [FAIL] Assertion failed: {e}")
        return False
    except Exception as e:
        print(f"  ! Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("FUNCTION SIGNATURE CONSISTENCY TESTS")
    print("=" * 60)

    results = []

    results.append(("data_cleaning_pipeline", test_data_cleaning_pipeline()))
    results.append(("finetuning_pipeline", test_finetuning_pipeline()))
    results.append(("translation_pipeline", test_translation_pipeline()))
    results.append(("translate_models", test_translate_models()))
    results.append(("preprocessing_classes", test_preprocessing_classes()))

    print("\n" + "=" * 60)
    print("SIGNATURE TESTS SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")

    if passed == total:
        print("ALL SIGNATURE TESTS PASSED [OK]\n")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED [FAIL]\n")
        sys.exit(1)
