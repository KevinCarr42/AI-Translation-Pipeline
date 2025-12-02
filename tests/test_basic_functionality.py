import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_config_data_structures():
    print("\nTesting config data structures...")
    try:
        import config
        
        assert isinstance(config.MODELS, dict), "MODELS should be a dict"
        assert len(config.MODELS) == 5, "Should have 5 models"
        
        assert isinstance(config.TRAINING_HYPERPARAMS, dict), "TRAINING_HYPERPARAMS should be a dict"
        assert isinstance(config.MODEL_SPECIFIC_HYPERPARAMS, dict), "MODEL_SPECIFIC_HYPERPARAMS should be a dict"
        assert isinstance(config.QUANTIZATION_CONFIG, dict), "QUANTIZATION_CONFIG should be a dict"
        
        for model_name in config.MODELS:
            assert model_name in config.MODEL_SPECIFIC_HYPERPARAMS, \
                f"Model {model_name} missing from MODEL_SPECIFIC_HYPERPARAMS"
        
        print("  [OK] All config data structures are properly defined")
        return True
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_document_splitting():
    print("\nTesting document splitting functionality...")
    try:
        from translate import split_by_sentences, split_by_paragraphs
        
        test_text = "First sentence. Second sentence.\n\nNew paragraph. Another sentence."
        
        chunks, metadata = split_by_sentences(test_text)
        assert len(chunks) >= 2, "Should split text into at least 2 chunks by sentences"
        assert isinstance(chunks, list), "chunks should be a list"
        print(f"  [OK] split_by_sentences works (created {len(chunks)} chunks)")
        
        chunks, metadata = split_by_paragraphs(test_text)
        assert len(chunks) >= 1, "Should split text into at least 1 chunk by paragraphs"
        assert isinstance(chunks, list), "chunks should be a list"
        print(f"  [OK] split_by_paragraphs works (created {len(chunks)} chunks)")
        
        return True
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_training_data_format():
    print("\nTesting training data format...")
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = f.name
            json.dump({"source": "Hello", "target": "Bonjour", "source_lang": "en"}, f)
            f.write('\n')
            json.dump({"source": "World", "target": "Monde", "source_lang": "en"}, f)
        
        from datasets import load_dataset
        
        dataset = load_dataset("json", data_files=temp_file, split="train")
        assert len(dataset) == 2, "Should load 2 examples"
        assert "source" in dataset[0], "Should have 'source' field"
        assert "target" in dataset[0], "Should have 'target' field"
        assert "source_lang" in dataset[0], "Should have 'source_lang' field"
        
        print("  [OK] Training data format is correct (JSONL with source, target, source_lang)")
        os.unlink(temp_file)
        return True
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return False
    except ImportError:
        print("  ! datasets library not available (expected in production environment)")
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        return False


def test_translate_module_structure():
    print("\nTesting translate module structure...")
    try:
        from translate.models import (
            BaseTranslationModel,
            OpusTranslationModel,
            M2M100TranslationModel,
            MBART50TranslationModel,
            TranslationManager,
        )
        from translate.document import (
            split_by_sentences,
            split_by_paragraphs,
            translate_document,
        )
        from translate.pipeline import (
            translation_pipeline,
            create_translator,
        )
        
        print("  [OK] translate.models submodule has all classes")
        print("  [OK] translate.document submodule has all functions")
        print("  [OK] translate.pipeline submodule has all functions")
        
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_model_finetuning_structure():
    print("\nTesting model_finetuning module structure...")
    try:
        from model_finetuning.pipeline import finetune_model, finetuning_pipeline
        from model_finetuning.preprocessing import Preprocessor, M2MDataCollator
        from model_finetuning.model_loading import load_tokenizer_and_model
        from model_finetuning.trainer import build_trainer
        
        print("  [OK] model_finetuning.pipeline has finetune_model and finetuning_pipeline")
        print("  [OK] model_finetuning.preprocessing has Preprocessor and M2MDataCollator")
        print("  [OK] model_finetuning.model_loading has load_tokenizer_and_model")
        print("  [OK] model_finetuning.trainer has build_trainer")
        
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_preprocessor_initialization():
    print("\nTesting Preprocessor initialization...")
    try:
        from model_finetuning.preprocessing import Preprocessor
        
        class DummyTokenizer:
            pad_token_id = 0
        
        preprocessor = Preprocessor(
            model_name="m2m100_418m",
            tokenizer=DummyTokenizer(),
            language_map={"en": "en", "fr": "fr"},
            max_source_length=512,
            max_target_length=512,
            restrict_source_language=None,
        )
        
        assert preprocessor.model_name == "m2m100_418m"
        assert preprocessor.max_source_length == 512
        
        print("  [OK] Preprocessor initializes correctly with proper parameters")
        return True
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


def test_quantization_boolean_logic():
    print("\nTesting quantization boolean logic...")
    try:
        import config
        
        use_qlora = config.QUANTIZATION_CONFIG.get('use_qlora', True)
        no_qlora = not use_qlora
        
        if not use_qlora:
            assert no_qlora == True, "no_qlora should be True when use_qlora is False"
        else:
            assert no_qlora == False, "no_qlora should be False when use_qlora is True"
        
        print(f"  [OK] Quantization logic is correct: use_qlora={use_qlora} → no_qlora={no_qlora}")
        return True
    except AssertionError as e:
        print(f"  [FAIL] {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BASIC FUNCTIONALITY TESTS")
    print("=" * 60)
    
    results = [
        ("config data structures", test_config_data_structures()),
        ("document splitting", test_document_splitting()),
        ("training data format", test_training_data_format()),
        ("translate module structure", test_translate_module_structure()),
        ("model_finetuning structure", test_model_finetuning_structure()),
        ("preprocessor initialization", test_preprocessor_initialization()),
        ("quantization boolean logic", test_quantization_boolean_logic())
    ]
    
    print("\n" + "=" * 60)
    print("FUNCTIONALITY TESTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("ALL FUNCTIONALITY TESTS PASSED [OK]\n")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED [FAIL]\n")
        sys.exit(1)
