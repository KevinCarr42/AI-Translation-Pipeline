import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from translate.models import TranslationManager


def _make_manager():
    manager = TranslationManager(all_models={}, embedder=None, debug=False)
    manager.loaded_models = {"mock_model": MagicMock()}
    return manager


def _fake_all_models_result(text):
    return {
        "best_model": {
            "translated_text": f"translated_{text}",
            "similarity_vs_source": 0.9,
            "model_name": "best_model",
            "best_model_source": "mock_model",
        }
    }


class TestTranslationCache:
    def test_cache_hit_skips_translate_with_all_models(self):
        manager = _make_manager()
        manager.translate_with_all_models = MagicMock(
            side_effect=lambda *a, **kw: _fake_all_models_result(kw["text"])
        )

        result1 = manager.translate_with_best_model(text="Hello world", source_lang="en", target_lang="fr")
        result2 = manager.translate_with_best_model(text="Hello world", source_lang="en", target_lang="fr")

        assert manager.translate_with_all_models.call_count == 1
        assert result1 is result2

    def test_different_text_not_cached(self):
        manager = _make_manager()
        manager.translate_with_all_models = MagicMock(
            side_effect=lambda *a, **kw: _fake_all_models_result(kw["text"])
        )

        result1 = manager.translate_with_best_model(text="Hello", source_lang="en", target_lang="fr")
        result2 = manager.translate_with_best_model(text="Goodbye", source_lang="en", target_lang="fr")

        assert manager.translate_with_all_models.call_count == 2
        assert result1["translated_text"] == "translated_Hello"
        assert result2["translated_text"] == "translated_Goodbye"

    def test_clear_errors_empties_cache(self):
        manager = _make_manager()
        manager.translate_with_all_models = MagicMock(
            side_effect=lambda *a, **kw: _fake_all_models_result(kw["text"])
        )

        manager.translate_with_best_model(text="Hello", source_lang="en", target_lang="fr")
        assert len(manager.translation_cache) == 1

        manager.clear_errors()
        assert len(manager.translation_cache) == 0

    def test_use_cache_false_bypasses_cache(self):
        manager = _make_manager()
        manager.translate_with_all_models = MagicMock(
            side_effect=lambda *a, **kw: _fake_all_models_result(kw["text"])
        )

        manager.translate_with_best_model(text="Hello", source_lang="en", target_lang="fr", use_cache=False)
        manager.translate_with_best_model(text="Hello", source_lang="en", target_lang="fr", use_cache=False)

        assert manager.translate_with_all_models.call_count == 2
        assert len(manager.translation_cache) == 0

    def test_cache_isolated_between_documents(self):
        manager = _make_manager()
        manager.translate_with_all_models = MagicMock(
            side_effect=lambda *a, **kw: _fake_all_models_result(kw["text"])
        )

        # Simulate document 1
        manager.translate_with_best_model(text="Government of Canada", source_lang="en", target_lang="fr")
        assert len(manager.translation_cache) == 1

        # Clear between documents (as translate_documents.py does)
        manager.clear_errors()

        # Simulate document 2 - same text should trigger a fresh translation
        manager.translate_with_best_model(text="Government of Canada", source_lang="fr", target_lang="en")

        assert manager.translate_with_all_models.call_count == 2

    def test_cache_init_empty(self):
        manager = _make_manager()
        assert manager.translation_cache == {}
