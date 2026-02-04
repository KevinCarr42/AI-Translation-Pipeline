import re

from rules_based_replacements.token_utils import (
    create_replacement_token, load_translations, get_search_patterns,
    get_translation_value, build_english_to_french_lookup
)


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


def preprocess_for_translation(text, translations_file, source_lang='fr'):
    translations_data = load_translations(translations_file)
    
    if 'translations' in translations_data:
        translations = translations_data['translations']
    else:
        translations = translations_data
    
    patterns = get_search_patterns(translations, source_lang)
    
    en_to_fr_lookup = None
    if source_lang == 'en':
        en_to_fr_lookup = build_english_to_french_lookup(translations)
    
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
                
                if source_lang == 'en':
                    lookup_result = en_to_fr_lookup.get(term.lower())
                    if not lookup_result:
                        continue
                    found_category, french_term, term_data = lookup_result
                    translation = french_term
                else:
                    translation_key = None
                    for original_key in translations[category].keys():
                        if original_key.lower() == term.lower():
                            translation_key = original_key
                            break
                    term_data = translations[category].get(translation_key) if translation_key else None
                    translation = get_translation_value(term_data) if term_data else None
                
                token_counters[category] += 1
                token = create_replacement_token(category, token_counters[category])
                
                token_mapping[token] = {
                    'original_text': original_text,
                    'category': category,
                    'translation': translation,
                    'should_translate': True
                }
                
                processed_text = processed_text[:start] + token + processed_text[end:]
    
    return processed_text, token_mapping


def preserve_capitalization(original_text, replacement_text, is_sentence_start=False):
    if not original_text or not replacement_text:
        return replacement_text

    if original_text.isupper():
        return replacement_text.upper()
    if is_sentence_start and replacement_text[0].islower():
        return replacement_text[0].upper() + replacement_text[1:]
    if original_text.islower():
        return replacement_text.lower()

    return replacement_text


def find_corrupted_token(text, token):
    exact_pattern = r'\b' + re.escape(token) + r'\b'
    exact_match = re.search(exact_pattern, text)
    if exact_match:
        return (True, exact_match.start(), token)

    match = re.match(r'^([A-Z]+)(\d+)$', token)
    if not match:
        return (False, None, None)

    prefix, suffix = match.groups()

    spaced_pattern = re.escape(prefix) + r'\s+' + re.escape(suffix)
    spaced_match = re.search(spaced_pattern, text)
    if spaced_match:
        return (True, spaced_match.start(), spaced_match.group())

    plural_pattern = r'\b' + re.escape(token) + r'e?s\b'
    plural_match = re.search(plural_pattern, text)
    if plural_match:
        return (True, plural_match.start(), plural_match.group())

    return (False, None, None)


def postprocess_translation(translated_text, token_mapping):
    result_text = translated_text

    for token in token_mapping.keys():
        found, position, corrupted_form = find_corrupted_token(result_text, token)

        if found:
            mapping = token_mapping[token]

            is_sentence_start = False
            if position == 0:
                is_sentence_start = True
            elif position > 0:
                preceding_text = result_text[:position].rstrip()
                if preceding_text and preceding_text[-1] in '.!?':
                    is_sentence_start = True

            if mapping['should_translate'] and mapping['translation'] and mapping['translation'] != 'None':
                replacement = preserve_capitalization(mapping['original_text'], mapping['translation'], is_sentence_start)
            else:
                replacement = mapping['original_text']

            pattern = r'\b' + re.escape(corrupted_form) + r'\b'
            result_text = re.sub(pattern, replacement, result_text, count=1)

    return result_text


def validate_tokens_replaced(text, token_mapping):
    for token in token_mapping.keys():
        if token in text:
            return False
    return True
