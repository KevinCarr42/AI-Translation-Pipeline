import json
from scipy.stats import pareto


def create_replacement_token(category, counter):
    return f"{category.upper()}{counter:04d}"


def choose_random_int(max_n=999):
    n = int(pareto(b=1.16, scale=1).rvs())
    if n <= max_n:
        return n
    return choose_random_int(max_n)


def load_translations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def get_translation_value(term_data):
    if isinstance(term_data, dict):
        return term_data.get('en')
    return term_data


def get_gender_info(term_data):
    if isinstance(term_data, dict):
        return {
            'gender': term_data.get('gender'),
            'articles': term_data.get('articles', {})
        }
    return {'gender': None, 'articles': {}}


def build_term_index(translations):
    french_to_info = {}
    english_to_info = {}
    
    for category, terms in translations.items():
        for french_term, term_data in terms.items():
            english_term = get_translation_value(term_data)
            french_to_info[french_term] = (category, french_term, english_term)
            if english_term:
                english_to_info[english_term] = (category, french_term, english_term)
    
    return french_to_info, english_to_info


def build_english_to_french_lookup(translations):
    lookup = {}
    for category, terms in translations.items():
        for french_key, term_data in terms.items():
            en_term = get_translation_value(term_data)
            if en_term:
                en_lower = en_term.lower()
                lookup[en_lower] = (category, french_key, term_data)
    return lookup


def get_search_patterns(translations, source_lang='fr'):
    patterns = {}
    
    for category, terms in translations.items():
        if source_lang == 'en':
            # When source is English, search for English terms (the "en" values)
            english_terms = []
            for french_key, term_data in terms.items():
                en_term = get_translation_value(term_data)
                if en_term:
                    english_terms.append(en_term)
            sorted_terms = sorted(english_terms, key=len, reverse=True)
        else:
            # When source is French, search for French terms (the dict keys)
            sorted_terms = sorted(terms.keys(), key=len, reverse=True)
        patterns[category] = sorted_terms
    
    return patterns
