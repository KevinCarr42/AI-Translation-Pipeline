import os

os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

import config
import logging
import torch
from sentence_transformers.util import pytorch_cos_sim
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM, BitsAndBytesConfig
from rules_based_replacements.preferential_translations import apply_preferential_translations, reverse_preferential_translations
from huggingface_hub import try_to_load_from_cache


def resolve_cached_model_path(model_id):
    if os.path.isabs(model_id) or os.path.isdir(model_id):
        return model_id
    cached_config = try_to_load_from_cache(model_id, 'config.json')
    if cached_config:
        return os.path.dirname(cached_config)
    return model_id


class BaseTranslationModel:
    def __init__(self, base_model_id, model_type="seq2seq", **parameters):
        self.base_model_id = base_model_id
        self.model_type = model_type
        self.parameters = parameters
        self.model = None
        self.tokenizer = None
        self.finetuned_model = None
        if self.parameters.get("debug"):
            logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
    
    def _tokenizer_kwargs(self):
        return {
            "use_fast": True,
            "local_files_only": self.parameters.get("local_files_only", False),
        }
    
    def _model_kwargs(self, allow_device_map=True):
        kwargs = {
            "trust_remote_code": True,
            "local_files_only": self.parameters.get("local_files_only", False),
            "torch_dtype": self.parameters.get("dtype", torch.bfloat16),
        }
        if allow_device_map:
            kwargs["device_map"] = self.parameters.get("device_map", "auto")
            kwargs["offload_folder"] = self.parameters.get("offload_folder", "./offload")
            if self.parameters.get("max_memory"):
                kwargs["max_memory"] = self.parameters["max_memory"]
        if self.parameters.get("revision"):
            kwargs["revision"] = self.parameters["revision"]
        if self.parameters.get("use_quantization"):
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=self.parameters.get("dtype", torch.bfloat16),
            )
        return kwargs
    
    def load_tokenizer(self):
        if self.tokenizer is None:
            tokenizer_path = self.parameters.get("merged_model_path", self.base_model_id)
            tokenizer_path = resolve_cached_model_path(tokenizer_path)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_path, **self._tokenizer_kwargs()
            )
            if getattr(self.tokenizer, "pad_token", None) is None and getattr(
                    self.tokenizer, "eos_token", None
            ):
                self.tokenizer.pad_token = self.tokenizer.eos_token
        return self.tokenizer
    
    def load_model(self):
        if self.model is None:
            loader = AutoModelForSeq2SeqLM if self.model_type == "seq2seq" else AutoModelForCausalLM
            
            model_path = self.parameters.get("merged_model_path", self.base_model_id)
            model_path = resolve_cached_model_path(model_path)
            
            self.model = loader.from_pretrained(
                model_path, **self._model_kwargs(allow_device_map=True)
            )
            tokenizer = self.load_tokenizer()
            if hasattr(self.model.config, "vocab_size") and len(tokenizer) > self.model.config.vocab_size:
                self.model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
        return self.model
    
    def translate_text(self, input_text, input_language="en", target_language="fr",
                       generation_kwargs=None):
        tokenizer = self.load_tokenizer()
        model = self.load_model()
    
    def clean_output(self, text):
        import re
        patterns = [
            r"^(Here is the translation|Voici la traduction)[:\s]*",
            r"^(Translation|Traduction)[:\s]*",
            r"^(The translation is|La traduction est)[:\s]*",
            r"\s*\([^)]*translation[^)]*\)\s*$",
        ]
        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned
    
    def clear_cache(self):
        self.model = None
        self.finetuned_model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class OpusTranslationModel(BaseTranslationModel):
    LANGUAGE_ALIASES = {"en": "en", "fr": "fr"}
    
    def __init__(self, base_model_id, model_type="seq2seq", **parameters):
        super().__init__(base_model_id, model_type, **parameters)
        self.directional_cache = {}
    
    def _root_model_id(self):
        parts = self.base_model_id.split("-")
        if parts[-2:] in (["en", "fr"], ["fr", "en"]):
            return "-".join(parts[:-2])
        return self.base_model_id
    
    def _directional_model_id(self, source_language, target_language):
        root_id = self._root_model_id()
        source_alias = self.LANGUAGE_ALIASES[source_language]
        target_alias = self.LANGUAGE_ALIASES[target_language]
        return f"{root_id}-{source_alias}-{target_alias}"
    
    def _load_directional(self, source_language, target_language):
        cache_key = f"{source_language}-{target_language}"
        if cache_key in self.directional_cache:
            return self.directional_cache[cache_key]
        
        merged_path = self.parameters.get(f"merged_model_path_{source_language}_{target_language}")
        model_id = merged_path if merged_path else self._directional_model_id(source_language, target_language)
        model_id = resolve_cached_model_path(model_id)
        
        tokenizer = AutoTokenizer.from_pretrained(model_id, **self._tokenizer_kwargs())
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id, **self._model_kwargs(allow_device_map=False)
        )
        if torch.cuda.is_available():
            model = model.cuda()
        if hasattr(model.config, "vocab_size") and len(tokenizer) > model.config.vocab_size:
            model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
        
        self.directional_cache[cache_key] = (tokenizer, model)
        return tokenizer, model
    
    def translate_text(
            self,
            input_text,
            input_language="en",
            target_language="fr",
            generation_kwargs=None,
    ):
        tokenizer, model = self._load_directional(input_language, target_language)
        
        model_inputs = tokenizer(input_text, return_tensors="pt", padding=True)
        model_inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in model_inputs.items()}
        
        generation_arguments = {
            "max_new_tokens": 256,
            "num_beams": 4,
            "do_sample": False,
            "pad_token_id": tokenizer.pad_token_id,
        }
        if generation_kwargs:
            generation_arguments.update(generation_kwargs)
        
        output_token_ids = model.generate(**model_inputs, **generation_arguments)
        text_output = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0].strip()
        return self.clean_output(text_output)


class M2M100TranslationModel(BaseTranslationModel):
    LANGUAGE_CODES = {"en": "en", "fr": "fr"}
    
    def translate_text(self, input_text, input_language="en", target_language="fr", generation_kwargs=None):
        tokenizer = self.load_tokenizer()
        model = self.load_model()
        
        source_code = self.LANGUAGE_CODES[input_language]
        target_code = self.LANGUAGE_CODES[target_language]
        tokenizer.src_lang = source_code
        
        model_inputs = tokenizer(input_text, return_tensors="pt", padding=True)
        model_inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in model_inputs.items()}
        
        generation_arguments = {
            "max_new_tokens": 256,
            "num_beams": 4,
            "do_sample": False,
            "pad_token_id": tokenizer.pad_token_id,
            "forced_bos_token_id": tokenizer.get_lang_id(target_code),
        }
        if generation_kwargs:
            generation_arguments.update(generation_kwargs)
        
        output_token_ids = model.generate(**model_inputs, **generation_arguments)
        text_output = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0].strip()
        return self.clean_output(text_output)


class MBART50TranslationModel(BaseTranslationModel):
    LANGUAGE_CODES = {"en": "en_XX", "fr": "fr_XX"}
    
    def __init__(self, base_model_id, model_type="seq2seq", **parameters):
        super().__init__(base_model_id, model_type, **parameters)
        self.directional_cache = {}
    
    def _get_directional_model_path(self, source_language, target_language):
        direction_key = f"merged_model_path_{source_language}_{target_language}"
        if direction_key in self.parameters:
            return self.parameters[direction_key]
        
        return self.base_model_id
    
    def _load_directional(self, source_language, target_language):
        cache_key = f"{source_language}-{target_language}"
        if cache_key in self.directional_cache:
            return self.directional_cache[cache_key]
        
        model_path = self._get_directional_model_path(source_language, target_language)
        model_path = resolve_cached_model_path(model_path)
        
        tokenizer = AutoTokenizer.from_pretrained(model_path, **self._tokenizer_kwargs())
        if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None):
            tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_path, **self._model_kwargs(allow_device_map=False)
        )
        if torch.cuda.is_available():
            model = model.cuda()
        
        if hasattr(model.config, "vocab_size") and len(tokenizer) > model.config.vocab_size:
            model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
        
        self.directional_cache[cache_key] = (tokenizer, model)
        return tokenizer, model
    
    def translate_text(self, input_text, input_language="en", target_language="fr",
                       generation_kwargs=None):
        tokenizer, model = self._load_directional(input_language, target_language)
        
        source_code = self.LANGUAGE_CODES[input_language]
        target_code = self.LANGUAGE_CODES[target_language]
        tokenizer.src_lang = source_code
        
        model_inputs = tokenizer(input_text, return_tensors="pt", padding=True)
        model_inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) for k, v in model_inputs.items()}
        
        target_id = getattr(tokenizer, "lang_code_to_id", {}).get(target_code) if hasattr(tokenizer, "lang_code_to_id") else None
        if target_id is None:
            target_id = tokenizer.convert_tokens_to_ids(target_code)
        
        generation_arguments = {
            "max_new_tokens": 256,
            "num_beams": 4,
            "do_sample": False,
            "pad_token_id": tokenizer.pad_token_id,
            "forced_bos_token_id": target_id,
        }
        if generation_kwargs:
            generation_arguments.update(generation_kwargs)
        
        output_token_ids = model.generate(**model_inputs, **generation_arguments)
        text_output = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0].strip()
        return self.clean_output(text_output)
    
    def clear_cache(self):
        self.directional_cache.clear()
        super().clear_cache()


class TranslationManager:
    TOKEN_PREFIXES = ['NOMENCLATURE', 'TAXON', 'ACRONYM', 'SITE', 'NAME']
    
    def __init__(self, all_models, embedder=None, debug=False):
        self.all_models = all_models
        self.embedder = embedder
        self.debug = debug
        self.loaded_models = {}
        self.find_replace_errors = {}
        self.extra_token_errors = {}
        self.token_retry_debug = {}
        self.translation_cache = {}
    
    def load_models(self, model_names=None):
        if model_names is None:
            model_names = list(self.all_models.keys())
        
        for name in model_names:
            config = self.all_models[name]
            model_instance = config['cls'](**config.get('params', {}))
            _ = model_instance.translate_text("Test", "en", "fr")
            self.loaded_models[name] = model_instance
    
    def translate_with_retries(self, model, text, source_lang, target_lang,
                               token_mapping=None, base_generation_kwargs=None,
                               model_name=None, idx=None, single_attempt=False):
        param_variations = [
            {"num_beams": 4},
            {"num_beams": 2},
            {"num_beams": 5},
            {"num_beams": 6},
            {"num_beams": 7},
            {"num_beams": 8},
            {"num_beams": 4, "length_penalty": 0.8},
            {"num_beams": 4, "length_penalty": 1.2},
            {"num_beams": 4, "repetition_penalty": 1.1},
        ]
        
        base_kwargs = base_generation_kwargs or {}
        
        debug_key = f"{model_name}_{idx}" if model_name and idx is not None else None
        retry_log = [] if self.debug and debug_key and token_mapping else None
        
        for i, params in enumerate(param_variations):
            generation_kwargs = {**base_kwargs, **params}
            
            translated = model.translate_text(
                text, source_lang, target_lang, generation_kwargs
            )
            
            if self.debug and retry_log is not None and token_mapping:
                missing_tokens = [token for token in token_mapping.keys() if token not in translated]
                if missing_tokens:
                    retry_log.append({
                        "attempt": i,
                        "all_tokens": list(token_mapping.keys()),
                        "missing_tokens": missing_tokens,
                        "params": params
                    })
            
            if self.is_valid_translation(translated, text, token_mapping):
                if i:
                    print(f"\tValid translation following {i} retries.")
                
                if self.debug and retry_log and debug_key:
                    print(f'entry added (success after {i + 1}):', model_name)
                    self.token_retry_debug[debug_key] = {
                        "total_attempts": i + 1,
                        "failed_attempts": retry_log,
                        "success": True,
                        "model_name": model_name,
                        "original_text": text
                    }
                
                return translated, i, params
            
            if single_attempt:
                return None, 1, None
        
        if self.debug and retry_log and debug_key:
            print(f'entry added (failed after {i + 1}):', model_name)
            self.token_retry_debug[debug_key] = {
                "total_attempts": len(param_variations),
                "failed_attempts": retry_log,
                "success": False,
                "model_name": model_name,
                "original_text": text
            }
        
        print(f"\tNo valid translations found following {i} attempted configs.")
        return None, len(param_variations), None
    
    def check_token_prefix_error(self, translated_text, original_text):
        if translated_text is None:
            return True
        
        for token_prefix in self.TOKEN_PREFIXES:
            if token_prefix in translated_text:
                if not original_text or token_prefix not in original_text:
                    return True
        return False
    
    def is_valid_translation(self, translated_text, original_text, token_mapping=None):
        if translated_text is None:
            return False
        
        if self.check_token_prefix_error(translated_text, original_text):
            return False
        
        if token_mapping:
            from rules_based_replacements.replacements import find_corrupted_token
            
            for key in token_mapping.keys():
                found, _, _ = find_corrupted_token(translated_text, key)
                if not found:
                    return False
        
        return True
    
    def translate_single(self, text, model_name, source_lang="en", target_lang="fr",
                         use_find_replace=True, generation_kwargs=None, idx=None,
                         target_text=None, debug=False, single_attempt=False):
        
        if not text or not text.strip():
            print(f"Skipping empty/whitespace text for model {model_name}")
            return {
                "find_replace_error": False,
                "token_prefix_error": False,
                "translated_text": text,
                "similarity_of_original_translation": None,
                "similarity_vs_source": None,
                "similarity_vs_target": None,
                "model_name": model_name,
                "retry_attempts": 0,
            }
        
        model = self.loaded_models[model_name]
        
        find_replace_error = False
        retry_attempts = 0
        retry_params = None
        
        if use_find_replace:
            preprocessed_text, token_mapping = apply_preferential_translations(
                text, source_lang, target_lang, config.PREFERENTIAL_JSON_PATH
            )
            
            translated_with_tokens, retry_attempts, retry_params = self.translate_with_retries(
                model, preprocessed_text, source_lang, target_lang,
                token_mapping, generation_kwargs, model_name, idx, single_attempt
            )
            
            if translated_with_tokens and self.is_valid_translation(
                    translated_with_tokens, preprocessed_text, token_mapping
            ):
                translated_text = reverse_preferential_translations(
                    translated_with_tokens, token_mapping
                )
                if translated_text is None:
                    find_replace_error = True
                    self.find_replace_errors[f"{model_name}_{idx}"] = {
                        "original_text": text,
                        "preprocessed_text": preprocessed_text,
                        "translated_with_tokens": translated_with_tokens,
                        "token_mapping": token_mapping,
                        "retry_attempts": retry_attempts,
                        "final_retry_params": retry_params,
                        "error_type": "reverse_translation_validation_failed",
                    }
                    translated_text = model.translate_text(
                        text, source_lang, target_lang, generation_kwargs
                    )
            else:
                find_replace_error = True
                self.find_replace_errors[f"{model_name}_{idx}"] = {
                    "original_text": text,
                    "preprocessed_text": preprocessed_text,
                    "translated_with_tokens": translated_with_tokens,
                    "token_mapping": token_mapping,
                    "retry_attempts": retry_attempts,
                    "final_retry_params": retry_params,
                }
                translated_text = model.translate_text(
                    text, source_lang, target_lang, generation_kwargs
                )
        else:
            preprocessed_text = None
            translated_with_tokens = None
            token_mapping = None
            translated_text = model.translate_text(
                text, source_lang, target_lang, generation_kwargs
            )
        
        token_prefix_error = self.check_token_prefix_error(translated_text, text)
        if token_prefix_error and debug:
            tokens_to_replace = [x for x in token_mapping.keys()] if token_mapping else None
            self.extra_token_errors[f"{model_name}_{idx}"] = {
                "original_text": text,
                "translated_text": translated_text,
                "use_find_replace": use_find_replace,
                "tokens_to_replace": tokens_to_replace,
                "preprocessed_text": preprocessed_text,
                "translated_with_tokens": translated_with_tokens,
                "retry_attempts": retry_attempts,
                "final_retry_params": retry_params,
            }
        
        if translated_text is None:
            print(f"Warning: Translation returned None for model {model_name} (idx={idx}). Using original text: '{text}'")
            translated_text = text
            token_prefix_error = False
        
        if self.embedder:
            source_embedding = self.embedder.encode(text, convert_to_tensor=True)
            translated_embedding = self.embedder.encode(translated_text, convert_to_tensor=True)
            similarity_vs_source = pytorch_cos_sim(source_embedding, translated_embedding).item()
            
            similarity_vs_target = None
            similarity_of_original_translation = None
            if target_text:
                target_embedding = self.embedder.encode(target_text, convert_to_tensor=True)
                similarity_vs_target = pytorch_cos_sim(target_embedding, translated_embedding).item()
                similarity_of_original_translation = pytorch_cos_sim(source_embedding, target_embedding).item()
        else:
            similarity_vs_source = None
            similarity_vs_target = None
            similarity_of_original_translation = None
        
        return {
            "find_replace_error": find_replace_error,
            "token_prefix_error": token_prefix_error,
            "translated_text": translated_text,
            "similarity_of_original_translation": similarity_of_original_translation,
            "similarity_vs_source": similarity_vs_source,
            "similarity_vs_target": similarity_vs_target,
            "model_name": model_name,
            "retry_attempts": retry_attempts if use_find_replace else 0,
        }
    
    def translate_with_all_models(self, text, source_lang="en", target_lang="fr",
                                  use_find_replace=True, generation_kwargs=None,
                                  idx=None, target_text=None, debug=False,
                                  single_attempt=False):
        model_names = list(self.loaded_models.keys())
        
        all_results = {}
        best_result = None
        best_similarity = float('-inf')
        
        for model_name in model_names:
            result = self.translate_single(
                text, model_name, source_lang, target_lang,
                use_find_replace, generation_kwargs, idx, target_text, debug,
                single_attempt
            )
            all_results[model_name] = result
            
            if self.is_valid_translation(result['translated_text'], text):
                if result["similarity_vs_source"] is None:
                    if best_result is None:
                        best_result = result.copy()
                        best_result["model_name"] = "best_model"
                        best_result["best_model_source"] = model_name
                elif result["similarity_vs_source"] > best_similarity:
                    best_similarity = result["similarity_vs_source"]
                    best_result = result.copy()
                    best_result["model_name"] = "best_model"
                    best_result["best_model_source"] = model_name
        
        if best_result is None:
            best_result = {
                "error": "No valid translations from any model",
                "translated_text": "[NO VALID TRANSLATIONS]",
                "similarity_vs_source": None,
                "similarity_vs_target": None,
                "model_name": "best_model",
                "best_model_source": None
            }
        
        all_results['best_model'] = best_result
        
        return all_results
    
    def translate_with_best_model(self, *args, use_cache=True, **kwargs):
        text = args[0] if args else kwargs.get("text")
        if use_cache and text in self.translation_cache:
            return self.translation_cache[text]
        result = self.translate_with_all_models(*args, **kwargs)["best_model"]
        if use_cache:
            self.translation_cache[text] = result
        return result
    
    def get_error_summary(self):
        return {
            "extra_token_errors": len(self.extra_token_errors),
            "find_replace_errors": len(self.find_replace_errors),
            "extra_token_error_details": self.extra_token_errors,
            "find_replace_error_details": self.find_replace_errors,
        }
    
    def clear_errors(self):
        self.extra_token_errors.clear()
        self.find_replace_errors.clear()
        self.token_retry_debug.clear()
        self.translation_cache.clear()


def get_model_config(use_finetuned=True, models_to_use=None):
    model_class_map = {
        "OpusTranslationModel": OpusTranslationModel,
        "M2M100TranslationModel": M2M100TranslationModel,
        "MBART50TranslationModel": MBART50TranslationModel,
    }
    
    all_models = {}
    for variant_name, variant_config in config.TRANSLATION_MODEL_VARIANTS.items():
        if not use_finetuned and variant_config["use_finetuned"]:
            continue
        
        base_model_key = variant_config["base_model_key"]
        base_model = config.MODELS[base_model_key]
        
        params = {
            "base_model_id": base_model["model_id"],
            "model_type": base_model["type"],
        }
        
        if "merged_model_names" in variant_config:
            for path_key, model_name in variant_config["merged_model_names"].items():
                params[path_key] = os.path.join(config.MERGED_MODEL_DIR, model_name)
        
        all_models[variant_name] = {
            "cls": model_class_map[variant_config["model_class"]],
            "params": params
        }
    
    if models_to_use:
        all_models = {k: v for k, v in all_models.items() if k in models_to_use}
    
    return all_models


def create_translator(use_finetuned=True, models_to_use=None, use_embedder=True, load_models=True, debug=False):
    from sentence_transformers import SentenceTransformer
    
    all_models = get_model_config(use_finetuned, models_to_use)
    
    embedder = None
    if use_embedder:
        model_path = resolve_cached_model_path('sentence-transformers/LaBSE')
        embedder = SentenceTransformer(model_path, local_files_only=True)
    
    manager = TranslationManager(all_models, embedder, debug=debug)
    
    if load_models:
        manager.load_models()
    
    return manager
