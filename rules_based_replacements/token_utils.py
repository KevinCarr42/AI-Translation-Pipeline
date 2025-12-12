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


def build_term_index(translations):
    french_to_info = {}
    english_to_info = {}
    
    for category, terms in translations.items():
        for french_term, english_term in terms.items():
            french_to_info[french_term] = (category, french_term, english_term)
            english_to_info[english_term] = (category, french_term, english_term)
    
    return french_to_info, english_to_info


def get_search_patterns(translations):
    patterns = {}
    
    for category, terms in translations.items():
        sorted_terms = sorted(terms.keys(), key=len, reverse=True)
        patterns[category] = sorted_terms
    
    return patterns
