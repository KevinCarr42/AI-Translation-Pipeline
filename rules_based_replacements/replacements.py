import re

from rules_based_replacements.token_utils import (
    create_replacement_token, load_translations, get_search_patterns,
    get_translation_value, get_gender_info, build_english_to_french_lookup
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
    
    # Build lookup for English->French when source is English
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
                    # term is English, look up French translation
                    lookup_result = en_to_fr_lookup.get(term.lower())
                    if not lookup_result:
                        continue
                    found_category, french_term, term_data = lookup_result
                    translation = french_term
                else:
                    # term is French (dict key), look up English translation
                    translation_key = None
                    for original_key in translations[category].keys():
                        if original_key.lower() == term.lower():
                            translation_key = original_key
                            break
                    term_data = translations[category].get(translation_key) if translation_key else None
                    translation = get_translation_value(term_data) if term_data else None
                
                gender_info = get_gender_info(term_data) if term_data else {'gender': None, 'articles': {}}
                
                token_counters[category] += 1
                token = create_replacement_token(category, token_counters[category])
                
                token_mapping[token] = {
                    'original_text': original_text,
                    'category': category,
                    'translation': translation,
                    'gender': gender_info['gender'],
                    'articles': gender_info['articles'],
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


ARTICLE_CORRECTIONS = {
    'm': {'le': 'le', 'la': 'le', 'un': 'un', 'une': 'un'},
    'f': {'le': 'la', 'la': 'la', 'un': 'une', 'une': 'une'},
}

ELIDED_ARTICLE_PATTERN = re.compile(r"\bl'(?=\s*[aeiouâêîôûàèùéëïüœæh])", re.IGNORECASE)


def correct_article_gender(text, token_mapping):
    result_text = text
    corrections_made = []
    
    for token, mapping in token_mapping.items():
        gender = mapping.get('gender')
        if gender not in ('m', 'f'):
            continue
        
        token_positions = [m.start() for m in re.finditer(re.escape(token), result_text)]
        
        for token_pos in reversed(token_positions):
            preceding_text = result_text[:token_pos].rstrip()
            
            for article in ['une', 'un', 'la', 'le']:
                if preceding_text.lower().endswith(article):
                    article_start = len(preceding_text) - len(article)
                    actual_article = preceding_text[article_start:]
                    correct_article = ARTICLE_CORRECTIONS[gender][article.lower()]
                    
                    if actual_article.lower() != correct_article:
                        if actual_article[0].isupper():
                            correct_article = correct_article.capitalize()
                        
                        whitespace_after_article = result_text[len(preceding_text):token_pos]
                        result_text = (
                                result_text[:article_start] +
                                correct_article +
                                whitespace_after_article +
                                result_text[token_pos:]
                        )
                        corrections_made.append({
                            'token': token,
                            'original_article': actual_article,
                            'corrected_article': correct_article,
                            'gender': gender
                        })
                    break
            
            if preceding_text.lower().endswith("l'"):
                article_start = len(preceding_text) - 2
                actual_article = preceding_text[article_start:]
                
                translation = mapping.get('translation', '')
                if translation and translation[0].lower() not in 'aeiouâêîôûàèùéëïüœæh':
                    correct_article = ARTICLE_CORRECTIONS[gender]['le' if gender == 'm' else 'la']
                    
                    if actual_article[0].isupper():
                        correct_article = correct_article.capitalize()
                    
                    whitespace_after_article = result_text[len(preceding_text):token_pos]
                    result_text = (
                            result_text[:article_start] +
                            correct_article + ' ' +
                            result_text[token_pos:]
                    )
                    corrections_made.append({
                        'token': token,
                        'original_article': actual_article,
                        'corrected_article': correct_article,
                        'gender': gender,
                        'note': 'expanded elision'
                    })
    
    return result_text, corrections_made
