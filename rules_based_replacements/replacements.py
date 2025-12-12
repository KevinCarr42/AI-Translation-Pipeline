import re

from rules_based_replacements.token_utils import create_replacement_token, load_translations, get_search_patterns


def replace_whole_word(text, word, replacement):
    pattern = r'(?<!\S)' + re.escape(word) + r'(?=\s|[.,;:!?]|$)'
    return re.sub(pattern, replacement, text)


def find_translation_matches(source, target, source_lang, french_index, english_index):
    matches = []
    
    if source_lang == 'en':
        for english_term in english_index:
            if english_term in source:
                category, french_term, _ = english_index[english_term]
                if french_term in target:
                    matches.append((category, french_term, english_term))
    else:
        for french_term in french_index:
            if french_term in source:
                category, _, english_term = french_index[french_term]
                if english_term in target:
                    matches.append((category, french_term, english_term))
    
    return matches


def preprocess_for_translation(text, translations_file):
    translations_data = load_translations(translations_file)
    
    if 'translations' in translations_data:
        translations = translations_data['translations']
    else:
        translations = translations_data
    
    patterns = get_search_patterns(translations)
    
    processed_text = text
    token_mapping = {}
    token_counters = {}
    
    for category in translations.keys():
        token_counters[category] = 0
    
    for category, terms in patterns.items():
        for term in terms:
            if ' ' in term:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
            else:
                pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            
            matches = list(pattern.finditer(processed_text))
            
            for match in reversed(matches):
                original_text = match.group()
                start, end = match.span()
                
                token_counters[category] += 1
                token = create_replacement_token(category, token_counters[category])
                
                translation_key = None
                for original_key in translations[category].keys():
                    if original_key.lower() == term.lower():
                        translation_key = original_key
                        break
                
                token_mapping[token] = {
                    'original_text': original_text,
                    'category': category,
                    'translation': translations[category].get(translation_key, None) if translation_key else None,
                    'should_translate': True
                }
                
                processed_text = processed_text[:start] + token + processed_text[end:]
    
    return processed_text, token_mapping


def preserve_capitalization(original_text, replacement_text, is_sentence_start=False):
    if not original_text or not replacement_text:
        return replacement_text
    
    if is_sentence_start:
        if replacement_text and replacement_text[0].isalpha():
            return replacement_text[0].upper() + replacement_text[1:]
        return replacement_text
    
    if original_text.isupper():
        return replacement_text.upper()
    elif original_text.islower():
        return replacement_text.lower()
    elif original_text[0].isupper():
        return replacement_text.capitalize()
    else:
        return replacement_text


def postprocess_translation(translated_text, token_mapping):
    result_text = translated_text
    
    for token in token_mapping.keys():
        if token in result_text:
            mapping = token_mapping[token]
            
            token_position = result_text.find(token)
            is_sentence_start = False
            if token_position == 0:
                is_sentence_start = True
            elif token_position > 0:
                preceding_text = result_text[:token_position].rstrip()
                if preceding_text and preceding_text[-1] in '.!?':
                    is_sentence_start = True
            
            if mapping['should_translate'] and mapping['translation'] and mapping['translation'] != 'None':
                replacement = preserve_capitalization(mapping['original_text'], mapping['translation'], is_sentence_start)
            else:
                replacement = mapping['original_text']
            
            result_text = result_text.replace(token, replacement)
    
    return result_text


def validate_tokens_replaced(text, token_mapping):
    for token in token_mapping.keys():
        if token in text:
            return False
    return True
