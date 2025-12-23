# Refactoring Guide: Token Replacement → Lexically Constrained Decoding

This guide walks through refactoring your translation pipeline from the current token-based `use_find_replace` approach to Hugging Face's native `force_words_ids` constrained decoding.

## Overview

### Current Approach (Token Replacement)
```
Source text → apply_preferential_translations() → Text with tokens → Model → Output with tokens → reverse_preferential_translations() → Final text
```

**Problems:**
- Tokens can be corrupted or dropped by the model
- Requires retry logic with multiple beam configurations
- Gender agreement issues (model doesn't see real words)
- Validation failures when tokens are missing

### New Approach (Lexically Constrained Decoding)
```
Source text → Find terminology matches → Model generates with force_words_ids → Final text (constraints guaranteed)
```

**Benefits:**
- Constraints are guaranteed to appear in output
- Model sees real words, enabling proper agreement
- No post-processing replacement step
- Simpler error handling

---

## Step 1: Create a Terminology Manager

Create a new file `translate/terminology.py`:

```python
import re
import json
from typing import Dict, List, Tuple, Optional


class TerminologyManager:
    """
    Manages bilingual terminology dictionaries and constraint generation.
    Replaces the token-based preferential_translations module.
    """
    
    def __init__(self, terminology_path: Optional[str] = None):
        # Structure: {source_lang: {target_lang: {source_term: target_term}}}
        self.terminology: Dict[str, Dict[str, Dict[str, str]]] = {
            "en": {"fr": {}},
            "fr": {"en": {}}
        }
        self.patterns: Dict[str, re.Pattern] = {}
        
        if terminology_path:
            self.load_from_json(terminology_path)
    
    def load_from_json(self, path: str):
        """
        Load terminology from JSON file.
        Expected format:
        {
            "en_to_fr": {"table": "la table", "dog": "le chien"},
            "fr_to_en": {"la table": "the table", "le chien": "the dog"}
        }
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "en_to_fr" in data:
            self.terminology["en"]["fr"] = data["en_to_fr"]
        if "fr_to_en" in data:
            self.terminology["fr"]["en"] = data["fr_to_en"]
        
        self._rebuild_patterns()
    
    def add_term(self, source_term: str, target_term: str, 
                 source_lang: str, target_lang: str):
        """Add a single terminology pair."""
        if source_lang not in self.terminology:
            self.terminology[source_lang] = {}
        if target_lang not in self.terminology[source_lang]:
            self.terminology[source_lang][target_lang] = {}
        
        self.terminology[source_lang][target_lang][source_term.lower()] = target_term
        self._rebuild_patterns()
    
    def _rebuild_patterns(self):
        """Rebuild regex patterns for all language pairs."""
        for source_lang in self.terminology:
            for target_lang in self.terminology[source_lang]:
                terms = self.terminology[source_lang][target_lang]
                if terms:
                    # Sort by length (longest first) to avoid partial matches
                    sorted_terms = sorted(terms.keys(), key=len, reverse=True)
                    pattern = re.compile(
                        r'\b(' + '|'.join(re.escape(t) for t in sorted_terms) + r')\b',
                        re.IGNORECASE
                    )
                    self.patterns[f"{source_lang}_{target_lang}"] = pattern
    
    def find_constraints(self, text: str, source_lang: str, 
                         target_lang: str) -> List[str]:
        """
        Find all terminology matches in source text and return target constraints.
        
        Returns list of target language phrases that should appear in output.
        """
        pattern_key = f"{source_lang}_{target_lang}"
        if pattern_key not in self.patterns:
            return []
        
        terms = self.terminology[source_lang][target_lang]
        pattern = self.patterns[pattern_key]
        
        matches = pattern.findall(text)
        constraints = []
        seen = set()
        
        for match in matches:
            target = terms.get(match.lower())
            if target and target not in seen:
                constraints.append(target)
                seen.add(target)
        
        return constraints
    
    def get_constraint_token_ids(self, constraints: List[str], 
                                  tokenizer) -> List[List[int]]:
        """
        Convert constraint phrases to token IDs for force_words_ids.
        
        Each constraint becomes a list of token IDs that must appear
        contiguously in the output.
        """
        if not constraints:
            return []
        
        force_words_ids = []
        for phrase in constraints:
            # Tokenize without special tokens
            token_ids = tokenizer.encode(phrase, add_special_tokens=False)
            if token_ids:
                force_words_ids.append(token_ids)
        
        return force_words_ids
    
    def save_to_json(self, path: str):
        """Export terminology to JSON."""
        data = {
            "en_to_fr": self.terminology.get("en", {}).get("fr", {}),
            "fr_to_en": self.terminology.get("fr", {}).get("en", {})
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
```

---

## Step 2: Modify Base Translation Models

Update each model class to accept `force_words_ids` in their `translate_text` method.

### M2M100TranslationModel

```python
class M2M100TranslationModel(BaseTranslationModel):
    LANGUAGE_CODES = {"en": "en", "fr": "fr"}
    
    def translate_text(self, input_text, input_language="en", target_language="fr", 
                       generation_kwargs=None, force_words_ids=None):
        tokenizer = self.load_tokenizer()
        model = self.load_model()
        
        source_code = self.LANGUAGE_CODES[input_language]
        target_code = self.LANGUAGE_CODES[target_language]
        tokenizer.src_lang = source_code
        
        model_inputs = tokenizer(input_text, return_tensors="pt", padding=True)
        model_inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) 
                        for k, v in model_inputs.items()}
        
        generation_arguments = {
            "max_new_tokens": 256,
            "num_beams": 5,  # Beam search required for force_words_ids
            "do_sample": False,
            "pad_token_id": tokenizer.pad_token_id,
            "forced_bos_token_id": tokenizer.get_lang_id(target_code),
        }
        
        # Add lexical constraints if provided
        if force_words_ids:
            generation_arguments["force_words_ids"] = force_words_ids
            # Ensure sufficient beams for constrained generation
            generation_arguments["num_beams"] = max(
                generation_arguments.get("num_beams", 5), 
                len(force_words_ids) + 2
            )
        
        if generation_kwargs:
            generation_arguments.update(generation_kwargs)
        
        output_token_ids = model.generate(**model_inputs, **generation_arguments)
        text_output = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0].strip()
        return self.clean_output(text_output)
```

### OpusTranslationModel

```python
class OpusTranslationModel(BaseTranslationModel):
    # ... existing code ...
    
    def translate_text(self, input_text, input_language="en", target_language="fr",
                       generation_kwargs=None, force_words_ids=None):
        tokenizer, model = self._load_directional(input_language, target_language)
        
        model_inputs = tokenizer(input_text, return_tensors="pt", padding=True)
        model_inputs = {k: (v.to(model.device) if hasattr(v, "to") else v) 
                        for k, v in model_inputs.items()}
        
        generation_arguments = {
            "max_new_tokens": 256,
            "num_beams": 5,
            "do_sample": False,
            "pad_token_id": tokenizer.pad_token_id,
        }
        
        if force_words_ids:
            generation_arguments["force_words_ids"] = force_words_ids
            generation_arguments["num_beams"] = max(
                generation_arguments.get("num_beams", 5),
                len(force_words_ids) + 2
            )
        
        if generation_kwargs:
            generation_arguments.update(generation_kwargs)
        
        output_token_ids = model.generate(**model_inputs, **generation_arguments)
        text_output = tokenizer.batch_decode(output_token_ids, skip_special_tokens=True)[0].strip()
        return self.clean_output(text_output)
```

### MBART50TranslationModel

Apply the same pattern to MBART50.

---

## Step 3: Update TranslationManager

Replace the token-based translation logic with constraint-based logic:

```python
from translate.terminology import TerminologyManager


class TranslationManager:
    def __init__(self, all_models, embedder=None, debug=False, 
                 terminology_path=None):
        self.all_models = all_models
        self.embedder = embedder
        self.debug = debug
        self.loaded_models = {}
        self.constraint_errors = {}  # Track constraint issues
        
        # Initialize terminology manager
        self.terminology = TerminologyManager(terminology_path)
    
    def load_models(self, model_names=None):
        # ... existing code unchanged ...
        pass
    
    def get_tokenizer_for_model(self, model_name, source_lang, target_lang):
        """Get the appropriate tokenizer for a model."""
        model = self.loaded_models[model_name]
        
        # Handle models with directional caching
        if hasattr(model, '_load_directional'):
            tokenizer, _ = model._load_directional(source_lang, target_lang)
            return tokenizer
        else:
            return model.load_tokenizer()
    
    def translate_single(self, text, model_name, source_lang="en", target_lang="fr",
                         use_terminology=True, generation_kwargs=None, idx=None,
                         target_text=None, debug=False):
        """
        Translate text with optional terminology constraints.
        
        Args:
            use_terminology: If True, apply lexical constraints from terminology dict
        """
        model = self.loaded_models[model_name]
        force_words_ids = None
        constraints_applied = []
        
        if use_terminology:
            # Find what constraints apply
            constraints_applied = self.terminology.find_constraints(
                text, source_lang, target_lang
            )
            
            if constraints_applied:
                # Get tokenizer and convert constraints to token IDs
                tokenizer = self.get_tokenizer_for_model(
                    model_name, source_lang, target_lang
                )
                force_words_ids = self.terminology.get_constraint_token_ids(
                    constraints_applied, tokenizer
                )
        
        # Translate with constraints
        translated_text = model.translate_text(
            text, source_lang, target_lang,
            generation_kwargs=generation_kwargs,
            force_words_ids=force_words_ids
        )
        
        # Validate constraints appeared (they should, but verify)
        constraint_error = False
        if constraints_applied:
            for constraint in constraints_applied:
                if constraint.lower() not in translated_text.lower():
                    constraint_error = True
                    if debug:
                        self.constraint_errors[f"{model_name}_{idx}"] = {
                            "text": text,
                            "expected_constraints": constraints_applied,
                            "translation": translated_text
                        }
                    break
        
        # Compute embeddings if available
        similarity_vs_source = None
        similarity_vs_target = None
        if self.embedder:
            source_embedding = self.embedder.encode(text, convert_to_tensor=True)
            translated_embedding = self.embedder.encode(translated_text, convert_to_tensor=True)
            from sentence_transformers.util import pytorch_cos_sim
            similarity_vs_source = pytorch_cos_sim(source_embedding, translated_embedding).item()
            
            if target_text:
                target_embedding = self.embedder.encode(target_text, convert_to_tensor=True)
                similarity_vs_target = pytorch_cos_sim(target_embedding, translated_embedding).item()
        
        return {
            "translated_text": translated_text,
            "constraints_applied": constraints_applied,
            "constraint_error": constraint_error,
            "similarity_vs_source": similarity_vs_source,
            "similarity_vs_target": similarity_vs_target,
            "model_name": model_name,
        }
    
    def translate_with_all_models(self, text, source_lang="en", target_lang="fr",
                                  use_terminology=True, generation_kwargs=None,
                                  idx=None, target_text=None, debug=False):
        """Translate with all models and select best."""
        model_names = list(self.loaded_models.keys())
        
        all_results = {}
        best_result = None
        best_similarity = float('-inf')
        
        for model_name in model_names:
            result = self.translate_single(
                text, model_name, source_lang, target_lang,
                use_terminology, generation_kwargs, idx, target_text, debug
            )
            all_results[model_name] = result
            
            # Select best based on similarity
            if (result["similarity_vs_source"] is not None 
                    and result["similarity_vs_source"] > best_similarity
                    and not result["constraint_error"]):
                best_similarity = result["similarity_vs_source"]
                best_result = result.copy()
                best_result["model_name"] = "best_model"
                best_result["best_model_source"] = model_name
        
        if best_result is None:
            best_result = {
                "error": "No valid translations from any model",
                "translated_text": "[NO VALID TRANSLATIONS]",
                "model_name": "best_model",
                "best_model_source": None
            }
        
        all_results['best_model'] = best_result
        return all_results
    
    def translate_with_best_model(self, *args, **kwargs):
        return self.translate_with_all_models(*args, **kwargs)["best_model"]
```

---

## Step 4: Update Factory Function

```python
def create_translator(use_finetuned=True, models_to_use=None, use_embedder=True, 
                      load_models=True, debug=False, terminology_path=None):
    from sentence_transformers import SentenceTransformer
    
    all_models = get_model_config(use_finetuned, models_to_use)
    
    embedder = None
    if use_embedder:
        embedder = SentenceTransformer('sentence-transformers/LaBSE')
    
    # Use config path if not specified
    if terminology_path is None:
        terminology_path = getattr(config, 'TERMINOLOGY_JSON_PATH', None)
    
    manager = TranslationManager(
        all_models, embedder, debug=debug,
        terminology_path=terminology_path
    )
    
    if load_models:
        manager.load_models()
    
    return manager
```

---

## Step 5: Update document.py

Change `use_find_replace` to `use_terminology`:

```python
def translate_document(
        input_text_file,
        output_text_file=None,
        source_lang="en",
        chunk_by="sentences",
        models_to_use=None,
        use_terminology=True,  # Renamed from use_find_replace
        use_finetuned=True,
        translation_manager=None,
        start_idx=0
):
    # ... setup code unchanged ...
    
    if not translation_manager:
        translation_manager = create_translator(
            use_finetuned=use_finetuned,
            models_to_use=models_to_use,
            use_embedder=True,
            load_models=True
        )
    
    translated_chunks = []
    for i, (chunk, metadata) in enumerate(zip(chunks, chunk_metadata), start_idx + 1):
        if metadata.get('is_empty', False):
            translated_chunks.append('')
            continue
        
        result = translation_manager.translate_with_best_model(
            text=chunk,
            source_lang=source_lang,
            target_lang=target_lang,
            use_terminology=use_terminology,  # Renamed
            idx=i
        )
        
        translated_text = result.get("translated_text", "[TRANSLATION FAILED]")
        translated_text = normalize_apostrophes(translated_text)
        translated_chunks.append(translated_text)
        next_idx = i
    
    # ... rest unchanged ...
```

---

## Step 6: Update translation_pipeline.py

```python
def translation_pipeline(input_text_file, output_text_file, 
                         with_terminology=True,  # Renamed
                         source_lang="en", chunk_by="sentences", 
                         models_to_use=None, use_finetuned=True, debug=False):
    print("\n" + "=" * 60)
    print("Translation Pipeline")
    print("=" * 60)
    print(f"Using terminology constraints: {with_terminology}\n")
    
    translate_document(
        input_text_file=input_text_file,
        output_text_file=output_text_file,
        source_lang=source_lang,
        chunk_by=chunk_by,
        models_to_use=models_to_use,
        use_terminology=with_terminology,  # Renamed
        use_finetuned=use_finetuned
    )
    
    return {"status": "complete", "output_file": output_text_file}
```

---

## Step 7: Migrate Your Existing Dictionary

Convert your existing `PREFERENTIAL_JSON_PATH` data to the new format:

```python
# migration_script.py
import json

def migrate_terminology(old_path, new_path):
    """
    Migrate from old token-based format to new constraint format.
    
    Old format typically had source->token mappings.
    New format has source->target mappings with proper gender/articles.
    """
    with open(old_path, 'r') as f:
        old_data = json.load(f)
    
    new_data = {
        "en_to_fr": {},
        "fr_to_en": {}
    }
    
    # You'll need to manually add the correct French translations
    # with proper articles for gender agreement
    # 
    # Example transformation:
    # Old: {"table": "NOMENCLATURE_001"}
    # New: {"table": "la table"}
    
    for source_term, token in old_data.get("en_to_fr", {}).items():
        # This requires manual review - add proper French with articles
        print(f"Need French translation for: {source_term}")
        # new_data["en_to_fr"][source_term] = "la/le " + french_translation
    
    with open(new_path, 'w') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"Migration template saved to {new_path}")
    print("Please manually add correct French translations with articles.")

# Run: migrate_terminology(config.PREFERENTIAL_JSON_PATH, "terminology.json")
```

---

## Handling Gender Agreement

The key advantage of this approach is that you can include articles in your terminology:

```json
{
  "en_to_fr": {
    "table": "la table",
    "dog": "le chien", 
    "computer": "l'ordinateur",
    "meeting": "la réunion",
    "machine learning": "l'apprentissage automatique"
  }
}
```

The model will be forced to include "la table" as a unit, ensuring correct gender.

**Caveats:**
- If the sentence structure requires different case (e.g., after a preposition), you may need variants
- For terms that could be plural, consider adding both forms:
  ```json
  {
    "table": "la table",
    "tables": "les tables"
  }
  ```

---

## Removing Old Code

Once the refactoring is complete, you can remove:

1. `rules_based_replacements/preferential_translations.py` (the old module)
2. The import in models.py:
   ```python
   # Remove this line:
   from rules_based_replacements.preferential_translations import apply_preferential_translations, reverse_preferential_translations
   ```
3. `TranslationManager.translate_with_retries()` method (no longer needed)
4. `TranslationManager.TOKEN_PREFIXES` constant
5. `TranslationManager.check_token_prefix_error()` method
6. Error tracking for token-related issues

---

## Testing Checklist

- [ ] Create `terminology.json` with test entries including gendered nouns
- [ ] Test single sentence with one constraint
- [ ] Test sentence with multiple constraints
- [ ] Test sentence with no terminology matches (should work normally)
- [ ] Test with each model type (M2M100, OPUS, MBART50)
- [ ] Verify gender agreement ("la table" not "le table")
- [ ] Test document-level translation
- [ ] Compare output quality with old token-based approach
- [ ] Benchmark performance (constrained decoding is slower)

---

## Performance Considerations

Constrained decoding is slower than unconstrained because:
- Requires beam search (can't use greedy)
- More beams needed for more constraints
- Additional bookkeeping during generation

Mitigations:
- Only apply constraints when terminology is detected
- Batch sentences by constraint count
- Consider caching constraint token IDs

---

## Rollback Plan

Keep the old code available during transition:

```python
def translate_single(self, text, model_name, source_lang="en", target_lang="fr",
                     use_terminology=True, use_legacy_find_replace=False,
                     generation_kwargs=None, idx=None, target_text=None, debug=False):
    
    if use_legacy_find_replace:
        # Old token-based approach
        return self._translate_with_find_replace(...)
    else:
        # New constraint-based approach
        return self._translate_with_constraints(...)
```

This allows A/B testing and quick rollback if issues arise.
