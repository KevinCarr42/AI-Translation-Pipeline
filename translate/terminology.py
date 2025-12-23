import re
import json


class TerminologyManager:
    
    def __init__(self, terminology_path=None):
        self.terminology = {
            "en": {"fr": {}},
            "fr": {"en": {}}
        }
        self.patterns = {}
        
        if terminology_path:
            self.load_from_json(terminology_path)
    
    def load_from_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "en_to_fr" in data:
            self.terminology["en"]["fr"] = data["en_to_fr"]
        if "fr_to_en" in data:
            self.terminology["fr"]["en"] = data["fr_to_en"]
        
        self._rebuild_patterns()
    
    def add_term(self, source_term, target_term, source_lang, target_lang):
        if source_lang not in self.terminology:
            self.terminology[source_lang] = {}
        if target_lang not in self.terminology[source_lang]:
            self.terminology[source_lang][target_lang] = {}
        
        self.terminology[source_lang][target_lang][source_term.lower()] = target_term
        self._rebuild_patterns()
    
    def _rebuild_patterns(self):
        for source_lang in self.terminology:
            for target_lang in self.terminology[source_lang]:
                terms = self.terminology[source_lang][target_lang]
                if terms:
                    sorted_terms = sorted(terms.keys(), key=len, reverse=True)
                    pattern = re.compile(
                        r'\b(' + '|'.join(re.escape(t) for t in sorted_terms) + r')\b',
                        re.IGNORECASE
                    )
                    self.patterns[f"{source_lang}_{target_lang}"] = pattern
    
    def find_constraints(self, text, source_lang, target_lang):
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
    
    def get_constraint_token_ids(self, constraints, tokenizer):
        if not constraints:
            return []
        
        force_words_ids = []
        for phrase in constraints:
            token_ids = tokenizer.encode(phrase, add_special_tokens=False)
            if token_ids:
                force_words_ids.append(token_ids)
        
        return force_words_ids
    
    def save_to_json(self, path):
        data = {
            "en_to_fr": self.terminology.get("en", {}).get("fr", {}),
            "fr_to_en": self.terminology.get("fr", {}).get("en", {})
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
