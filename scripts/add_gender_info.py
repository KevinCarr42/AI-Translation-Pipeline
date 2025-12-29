import json
import re
import spacy

nlp = spacy.load('fr_core_news_lg')

FEMININE_ENDINGS = [
    'tion', 'sion', 'ité', 'té', 'ure', 'ence', 'ance', 'ie', 'ée',
    'esse', 'ette', 'elle', 'ienne', 'euse', 'trice', 'ère'
]
MASCULINE_ENDINGS = [
    'ment', 'age', 'isme', 'eur', 'teur', 'ier', 'er', 'et', 'eau',
    'al', 'ail', 'eil', 'euil', 'ois', 'ais'
]

# Common French geographic/place prefixes with known gender
PLACE_PREFIX_GENDERS = {
    'pic': 'm',  # peak
    'mont': 'm',  # mountain
    'lac': 'm',  # lake
    'canyon': 'm',  # canyon
    'col': 'm',  # pass
    'glacier': 'm',  # glacier
    'ruisseau': 'm',  # stream
    'fleuve': 'm',  # river (large)
    'cap': 'm',  # cape
    'golfe': 'm',  # gulf
    'chenal': 'm',  # channel
    'détroit': 'm',  # strait
    'bassin': 'm',  # basin
    'havre': 'm',  # harbor
    'haut-fond': 'm',  # shoal
    'hauts-fond': 'm',  # shoals
    'banc': 'm',  # bank
    'récif': 'm',  # reef
    'bief': 'm',  # reach (water)
    'pont': 'm',  # bridge
    'quai': 'm',  # dock
    'square': 'm',  # square
    'îlot': 'm',  # islet
    'ilot': 'm',  # islet (no accent)
    'ílot': 'm',  # islet (accent variant)
    'rapides': 'm',  # rapids
    'pique-nique': 'm',  # picnic area
    'île': 'f',  # island
    'îles': 'f',  # islands
    'baie': 'f',  # bay
    'anse': 'f',  # cove
    'rivière': 'f',  # river
    'chute': 'f',  # waterfall (singular)
    'chutes': 'f',  # waterfalls
    'pointe': 'f',  # point
    'passe': 'f',  # pass (water)
    'crique': 'f',  # creek
    'vallée': 'f',  # valley
    'plage': 'f',  # beach
    'montagne': 'f',  # mountain
    'mer': 'f',  # sea
    'côte': 'f',  # coast
    'presqu\'île': 'f',  # peninsula
    'péninsule': 'f',  # peninsula
    'fosse': 'f',  # trench/pit
    'écluse': 'f',  # lock (water)
    'mare': 'f',  # pond/pool
    'caserne': 'f',  # barrack
}

# Known species/taxon genders (common ones that spacy misses)
KNOWN_TAXON_GENDERS = {
    'béluga': 'm',
    'hareng': 'm',
    'saumon': 'm',
    'homard': 'm',
    'aiglefin': 'm',
    'flétan': 'm',
    'copépode': 'm',
    'cténophore': 'm',
    'cténophores': 'm',
    'zooplancton': 'm',
    'chalut': 'm',
    'goberge': 'f',
    'scophthalmidé': 'm',
}

# Known nomenclature terms that are not easily detected
KNOWN_NOMENCLATURE_GENDERS = {
    'infaune': 'f',
    'dispersant chimique': 'm',
    'planktopiscivore': 'm',
    'chalut': 'm',
    'zooplancton': 'm',
    'bioregion (less formal)': 'f',
}

# Terms that are adjectives (gender matches the noun they modify)
ADJECTIVES = {
    'abiotiques', 'benthiques', 'benthivores', 'écologique', 'juvénile',
    'adulte', 'exponentiel(le)',
}

# Brand names / proper nouns that don't need gender
BRAND_NAMES = {
    'electric green®', 'galactic purple®', 'glofish®', 'cosmic blue®',
}

# Standalone place terms (not prefixes)
STANDALONE_PLACE_GENDERS = {
    'caserne': 'f',
}

ARTICLE_MAP = {
    'm': {'definite': 'le', 'indefinite': 'un'},
    'f': {'definite': 'la', 'indefinite': 'une'},
    'unknown': {'definite': 'le/la', 'indefinite': 'un/une'},
    'adjective': {'definite': None, 'indefinite': None},
    'proper_noun': {'definite': None, 'indefinite': None},
}


def get_gender_from_spacy(text):
    doc = nlp(text)
    
    for token in doc:
        if token.pos_ == 'NOUN':
            gender = token.morph.get('Gender')
            if gender:
                return 'm' if gender[0] == 'Masc' else 'f'
    
    for token in doc:
        gender = token.morph.get('Gender')
        if gender:
            return 'm' if gender[0] == 'Masc' else 'f'
    
    return None


def get_gender_from_place_prefix(text):
    text_lower = text.lower()
    for prefix, gender in PLACE_PREFIX_GENDERS.items():
        if text_lower.startswith(prefix + ' '):
            return gender
    return None


def get_gender_from_known_taxon(text):
    text_lower = text.lower()
    for taxon, gender in KNOWN_TAXON_GENDERS.items():
        if text_lower == taxon or text_lower.startswith(taxon + ' ') or text_lower.endswith(' ' + taxon):
            return gender
    return None


def get_gender_from_known_nomenclature(text):
    text_lower = text.lower()
    if text_lower in KNOWN_NOMENCLATURE_GENDERS:
        return KNOWN_NOMENCLATURE_GENDERS[text_lower]
    return None


def get_gender_from_heuristics(text):
    words = text.lower().split()
    
    nouns = [w for w in words if not w in ['de', 'du', 'des', 'le', 'la', 'les', 'un', 'une', 'et', 'ou', 'à', 'en', 'pour', 'sur', 'dans', 'par']]
    
    if not nouns:
        return None
    
    head_noun = nouns[0]
    
    for ending in FEMININE_ENDINGS:
        if head_noun.endswith(ending):
            return 'f'
    
    for ending in MASCULINE_ENDINGS:
        if head_noun.endswith(ending):
            return 'm'
    
    return None


def detect_gender(french_term, category=None):
    term_lower = french_term.lower()
    
    if term_lower in ADJECTIVES:
        return 'adjective', 'adjective'
    
    if term_lower in BRAND_NAMES:
        return 'proper_noun', 'brand_name'
    
    if term_lower in STANDALONE_PLACE_GENDERS:
        return STANDALONE_PLACE_GENDERS[term_lower], 'standalone_place'
    
    gender = get_gender_from_spacy(french_term)
    if gender:
        return gender, 'spacy'
    
    gender = get_gender_from_place_prefix(french_term)
    if gender:
        return gender, 'place_prefix'
    
    if category == 'taxon':
        gender = get_gender_from_known_taxon(french_term)
        if gender:
            return gender, 'known_taxon'
    
    if category == 'nomenclature':
        gender = get_gender_from_known_nomenclature(french_term)
        if gender:
            return gender, 'known_nomenclature'
    
    gender = get_gender_from_heuristics(french_term)
    if gender:
        return gender, 'heuristic'
    
    return 'unknown', 'none'


def is_likely_proper_noun(term):
    if term[0].isupper() and not term.isupper():
        words = term.split()
        if len(words) > 1 and all(w[0].isupper() for w in words if w[0].isalpha()):
            return True
    return False


def process_translations(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    translations = data.get('translations', data)
    new_translations = {}
    
    stats = {
        'spacy': 0, 'heuristic': 0, 'place_prefix': 0, 'standalone_place': 0,
        'known_taxon': 0, 'known_nomenclature': 0, 'adjective': 0, 'brand_name': 0,
        'none': 0, 'skipped': 0
    }
    unknown_terms = []
    
    for category, terms in translations.items():
        new_translations[category] = {}
        print(f"\nProcessing {category} ({len(terms)} terms)...")
        
        for french_term, english_trans in terms.items():
            if category == 'acronym' and french_term.isupper():
                new_translations[category][french_term] = english_trans
                stats['skipped'] += 1
                continue
            
            gender, source = detect_gender(french_term, category)
            stats[source] += 1
            
            if gender == 'unknown':
                unknown_terms.append((category, french_term, english_trans))
            
            new_translations[category][french_term] = {
                'en': english_trans,
                'gender': gender,
                'articles': ARTICLE_MAP[gender]
            }
    
    output_data = {
        'metadata': data.get('metadata', {}),
        'translations': new_translations,
        'sources': data.get('sources', {}),
        'statistics': data.get('statistics', {})
    }
    
    output_data['metadata']['gender_detection_stats'] = stats
    output_data['metadata']['format_version'] = '2.0'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n--- Statistics ---")
    print(f"SpaCy detected: {stats['spacy']}")
    print(f"Place prefix detected: {stats['place_prefix']}")
    print(f"Standalone place detected: {stats['standalone_place']}")
    print(f"Known taxon detected: {stats['known_taxon']}")
    print(f"Known nomenclature detected: {stats['known_nomenclature']}")
    print(f"Adjectives (no inherent gender): {stats['adjective']}")
    print(f"Brand names (proper nouns): {stats['brand_name']}")
    print(f"Heuristic detected: {stats['heuristic']}")
    print(f"Unknown (needs review): {stats['none']}")
    print(f"Skipped (acronyms): {stats['skipped']}")
    
    if unknown_terms:
        unknown_file = output_file.replace('.json', '_unknown.txt')
        with open(unknown_file, 'w', encoding='utf-8') as f:
            f.write("Terms with unknown gender (needs manual review):\n\n")
            for cat, fr, en in unknown_terms:
                f.write(f"[{cat}] {fr} -> {en}\n")
        print(f"\nUnknown terms written to: {unknown_file}")
    
    print(f"\nOutput written to: {output_file}")


if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else '../Data/preferential_translations.json'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '../Data/preferential_translations_v2.json'
    
    process_translations(input_file, output_file)
