import json
import re


def load_translations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_preferential_translations(source_text, source_language, target_language, translations_data, use_replacements=True, validate_tokens=True):
    if not use_replacements:
        return source_text, {}
    
    if isinstance(translations_data, str):
        translations_data = load_translations(translations_data)
    
    if source_language == 'fr':
        replacements = translations_data.get('fr_to_en', {})
    elif source_language == 'en':
        replacements = translations_data.get('en_to_fr', {})
    else:
        return source_text, {}
    
    all_valid_matches = []
    replaced_chars = set()
    
    sorted_terms = sorted(replacements.keys(), key=len, reverse=True)
    
    for source_term in sorted_terms:
        target_term = replacements[source_term]
        
        if ' ' in source_term:
            pattern = re.compile(re.escape(source_term), re.IGNORECASE)
        else:
            pattern = re.compile(r'\b' + re.escape(source_term) + r'\b', re.IGNORECASE)
        
        matches = list(pattern.finditer(source_text))
        
        for match in matches:
            start, end = match.span()
            char_range = set(range(start, end))
            
            if not char_range.intersection(replaced_chars):
                all_valid_matches.append((start, end, match.group(), source_term, target_term))
                replaced_chars.update(char_range)
    
    all_valid_matches.sort(key=lambda x: x[0], reverse=True)
    
    processed_text = source_text
    applied_replacements = {}
    
    for start, end, original_text, source_term, target_term in all_valid_matches:
        processed_text = processed_text[:start] + target_term + processed_text[end:]
        
        applied_replacements[source_term] = {
            'original_text': original_text,
            'target_term': target_term
        }
    
    return processed_text, applied_replacements


def reverse_preferential_translations(translated_text, token_mapping, validate_tokens_flag=True):
    if not token_mapping:
        return translated_text
    
    if validate_tokens_flag:
        for source_term, info in token_mapping.items():
            target_term = info['target_term']
            
            if ' ' in target_term:
                target_pattern = re.compile(re.escape(target_term), re.IGNORECASE)
            else:
                target_pattern = re.compile(r'\b' + re.escape(target_term) + r'\b', re.IGNORECASE)
            
            if not target_pattern.search(translated_text):
                return None
            
            if ' ' in source_term:
                source_pattern = re.compile(re.escape(source_term), re.IGNORECASE)
            else:
                source_pattern = re.compile(r'\b' + re.escape(source_term) + r'\b', re.IGNORECASE)
            
            if source_pattern.search(translated_text):
                return None
    
    return translated_text
