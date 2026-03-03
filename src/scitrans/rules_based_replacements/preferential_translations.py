from rules_based_replacements.replacements import (
    preprocess_for_translation,
    postprocess_translation,
    validate_tokens_replaced,
)


def apply_preferential_translations(source_text, source_language, target_language, translations_file, use_replacements=True, validate_tokens=True):
    if not use_replacements:
        return source_text, {}
    
    preprocessed_text, token_mapping = preprocess_for_translation(source_text, translations_file, source_lang=source_language)
    
    return preprocessed_text, token_mapping


def reverse_preferential_translations(translated_text, token_mapping, validate_tokens_flag=True):
    if not token_mapping:
        return translated_text
    
    result_text = postprocess_translation(translated_text, token_mapping)
    
    if validate_tokens_flag:
        if not validate_tokens_replaced(result_text, token_mapping):
            return None
    
    return result_text


def compare_translations(source_text, translated_text_1, translated_text_2, translations_file, source_language='en', target_language='fr'):
    preprocessed_1, mapping_1 = preprocess_for_translation(source_text, translations_file, source_lang=source_language)
    preprocessed_2, mapping_2 = preprocess_for_translation(source_text, translations_file, source_lang=source_language)
    
    return {
        'source': source_text,
        'preprocessed_1': preprocessed_1,
        'preprocessed_2': preprocessed_2,
        'mapping_1': mapping_1,
        'mapping_2': mapping_2,
        'translations_match': mapping_1 == mapping_2
    }


def detect_mistranslations(source_text, translated_text, token_mapping, translations_file):
    issues = []
    
    for token, mapping in token_mapping.items():
        if token not in translated_text:
            issues.append({
                'token': token,
                'category': mapping['category'],
                'original_text': mapping['original_text'],
                'issue': 'token_missing_from_translation'
            })
    
    return issues
