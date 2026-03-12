import json
import os
import sys

import pandas as pd
import openpyxl
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from scitrans import config

OLD_REPO = os.path.join(os.path.dirname(__file__), '..', '..', 'RuleBasedTranslationMatching')
SPREADSHEET_FILE = os.path.join(OLD_REPO, 'translations_spreadsheet.xlsx')
PLACE_NAMES_CSV = os.path.join(OLD_REPO, 'reference', 'vw_Place_Names_Noms_Lieux_APCA_V2_FGP.csv')
OUTPUT_FILE = config.INTERNAL_DATA_DIR / 'preferential_translations.json'


def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean(value):
    if pd.notna(value):
        s = str(value).strip()
        if s:
            return s
    return None


def extract_technical_terms(file_path):
    df = pd.read_excel(file_path, sheet_name="Technical Terms")
    
    translations = []
    for _, row in df.iterrows():
        english = clean(row.get('Term (E)'))
        french = clean(row.get('Term (F)'))
        
        if not english or not french:
            continue
        
        entry = {
            'english': english,
            'french': french,
            'french_informal': clean(row.get('Alternate (F)')),
            'french_to_avoid': clean(row.get('French to avoid')),
            'context': clean(row.get('Context')),
            'comments': clean(row.get('Comments')),
        }
        translations.append(entry)
    
    return translations


def extract_species_names(file_path):
    df = pd.read_excel(file_path, sheet_name="Species Names")
    
    translations = []
    for _, row in df.iterrows():
        english = clean(row.get('Species Name (E)'))
        french = clean(row.get('Species Name (F)'))
        
        if not english or not french:
            continue
        
        entry = {
            'english': english,
            'french': french,
            'scientific': clean(row.get('Scientific Name ')),
            'terms_to_avoid': clean(row.get('Terms to Avoid (F) ')),
        }
        translations.append(entry)
    
    return translations


def extract_acronyms_abbreviations(file_path):
    df = pd.read_excel(file_path, sheet_name="Aconyms & Abbreviations")
    
    translations = []
    for _, row in df.iterrows():
        en_acronym = clean(row.get('Acronym/\nAbbreviation (E) '))
        fr_acronym = clean(row.get('Acronym/\nAbbreviation (F) '))
        en_full = clean(row.get('Full Name/\nMeaning (E)'))
        fr_full = clean(row.get('Full Name/\nMeaning (F)'))
        
        if not en_acronym and not en_full:
            continue
        
        entry = {
            'english_acronym': en_acronym,
            'french_acronym': fr_acronym,
            'english_full': en_full,
            'french_full': fr_full,
            'comments': clean(row.get('Comments ')),
        }
        translations.append(entry)
    
    return translations


def extract_place_names(csv_path):
    place_translations = []
    
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found")
        return place_translations
    
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        english = clean(row.get('Name_e'))
        french = clean(row.get('Nom_f'))
        
        if not english or not french or english == french:
            continue
        
        place_translations.append({
            'english': english,
            'french': french,
        })
    
    return place_translations


def get_place_names_sources(file_path):
    wb = openpyxl.load_workbook(file_path)
    ws = wb["Place Names"]
    
    links = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.hyperlink:
                links.append({
                    'url': cell.hyperlink.target,
                    'description': cell.value
                })
    
    return links


def generate_all_translations(spreadsheet_file=SPREADSHEET_FILE,
                              place_names_csv=PLACE_NAMES_CSV,
                              output_file=OUTPUT_FILE):
    print(f"Generating translation dictionaries from {spreadsheet_file}...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    technical_terms = extract_technical_terms(spreadsheet_file)
    species_names = extract_species_names(spreadsheet_file)
    acronyms_abbreviations = extract_acronyms_abbreviations(spreadsheet_file)
    place_names = extract_place_names(place_names_csv)
    place_names_sources = get_place_names_sources(spreadsheet_file)
    
    all_translations = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_spreadsheet': os.path.basename(spreadsheet_file),
            'total_categories': 4
        },
        'translations': {
            'nomenclature': technical_terms,
            'taxon': species_names,
            'acronym': acronyms_abbreviations,
            'site': place_names
        },
        'sources': {
            'place_names_links': place_names_sources
        },
        'statistics': {
            'technical_terms_count': len(technical_terms),
            'species_names_count': len(species_names),
            'acronyms_abbreviations_count': len(acronyms_abbreviations),
            'place_names_count': len(place_names),
            'total_translations': len(technical_terms) + len(species_names) + len(acronyms_abbreviations) + len(place_names)
        }
    }
    
    save_json(all_translations, output_file)
    
    print("\n" + "=" * 50)
    print("TRANSLATION STATISTICS")
    print("=" * 50)
    stats = all_translations['statistics']
    print(f"Technical Terms: {stats['technical_terms_count']}")
    print(f"Species Names: {stats['species_names_count']}")
    print(f"Acronyms & Abbreviations: {stats['acronyms_abbreviations_count']}")
    print(f"Place Names: {stats['place_names_count']}")
    print("-" * 50)
    print(f"Total Translations: {stats['total_translations']}")
    print(f"\nSaved to: {output_file}")
    
    return all_translations


if __name__ == "__main__":
    generate_all_translations()
