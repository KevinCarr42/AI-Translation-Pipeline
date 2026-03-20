import json
import os
import re
import sys
from collections import defaultdict

import pandas as pd
import openpyxl
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from scitrans import config

OLD_REPO = os.path.join(os.path.dirname(__file__), '..', '..', 'RuleBasedTranslationMatching')
SPREADSHEET_FILE = os.path.join(OLD_REPO, 'translations_spreadsheet.xlsx')
PLACE_NAMES_CSV = os.path.join(OLD_REPO, 'reference', 'vw_Place_Names_Noms_Lieux_APCA_V2_FGP.csv')
TABLE_TRANSLATIONS_FILE = config.INTERNAL_DATA_DIR / 'table_translations.json'
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


# --- Table translation processing ---

# Province abbreviation pairs to exclude (EN, FR)
PROVINCE_FR_FORMS = {
    ('NS', 'NÉ'), ('NS', 'N.-É.'),
    ('NB', 'N.-B.'),
    ('PE', 'ÎPÉ'), ('PE', 'Î.-P.-É.'),
    ('NL', 'T.-N.-L.'),
}

_ITALIC_RE = re.compile(r'/([^/]+)/')
_SUB_RE = re.compile(r'_\{([^}]*)\}')
_SUPER_RE = re.compile(r'\^\{([^}]*)\}')
_NUMERIC_RE = re.compile(r'^[\d.±]+$')


def _strip_formatting(text):
    # No spaces between parts — must match how python-docx concatenates runs
    plain = re.sub(r'/([^/]+)/', r'\1', text)
    plain = re.sub(r'[_^]\{([^}]*)\}', r'\1', plain)
    return plain


def _has_formatting(text):
    return bool(re.search(r'/[^/]+/|_\{|\^\{', text))


def _should_filter_entry(en, fr, count):
    if (en, fr) in PROVINCE_FR_FORMS:
        return True
    if len(en) == 1 and len(fr) == 1:
        return True
    if count < 3 and len(en) <= 2:
        return True
    if en.lower() == fr.lower():
        return True
    return False


def _extract_sub_parts(en_formatted, fr_formatted):
    pairs = []
    
    en_italics = _ITALIC_RE.findall(en_formatted)
    fr_italics = _ITALIC_RE.findall(fr_formatted)
    for en_part, fr_part in zip(en_italics, fr_italics):
        pairs.append((en_part, fr_part))
    
    en_subs = _SUB_RE.findall(en_formatted)
    fr_subs = _SUB_RE.findall(fr_formatted)
    for en_part, fr_part in zip(en_subs, fr_subs):
        en_clean = _ITALIC_RE.sub(r'\1', en_part)
        fr_clean = _ITALIC_RE.sub(r'\1', fr_part)
        pairs.append((en_clean, fr_clean))
    
    en_supers = _SUPER_RE.findall(en_formatted)
    fr_supers = _SUPER_RE.findall(fr_formatted)
    for en_part, fr_part in zip(en_supers, fr_supers):
        en_clean = _ITALIC_RE.sub(r'\1', en_part)
        fr_clean = _ITALIC_RE.sub(r'\1', fr_part)
        pairs.append((en_clean, fr_clean))
    
    seen = set()
    filtered = []
    for en_part, fr_part in pairs:
        if _NUMERIC_RE.match(en_part):
            continue
        if en_part.lower() == fr_part.lower():
            continue
        if len(en_part) == 1 and len(fr_part) == 1:
            continue
        key = (en_part, fr_part)
        if key not in seen:
            seen.add(key)
            filtered.append(key)
    
    return filtered


def _deduplicate_entries(raw_entries):
    groups = {}
    for entry in raw_entries:
        en = entry['en']
        fr = entry['fr']
        count = entry.get('count', 0)
        if en not in groups:
            groups[en] = {}
        groups[en][fr] = groups[en].get(fr, 0) + count
    
    results = []
    for en, fr_counts in groups.items():
        best_fr = max(fr_counts, key=fr_counts.get)
        best_count = fr_counts[best_fr]
        other_variants = [f for f in fr_counts if f != best_fr]
        entry = {'en': en, 'fr': best_fr, 'count': best_count}
        if other_variants:
            entry['fr_variants'] = other_variants
        results.append(entry)
    
    return results


def _align_dash_variants(entries):
    # When both CIOPSW and CIOPS-W exist, the no-dash form's French wins for both.
    nodash_lookup = {}
    for e in entries:
        nodash = e['en'].replace('-', '')
        if nodash == e['en']:
            nodash_lookup[nodash] = e
    
    for entry in entries:
        en = entry['en']
        nodash = en.replace('-', '')
        if nodash != en and nodash in nodash_lookup:
            entry['fr'] = nodash_lookup[nodash]['fr']
    
    return entries


def _merge_case_variants(entries):
    case_groups = defaultdict(list)
    for entry in entries:
        case_groups[entry['en'].lower()].append(entry)
    
    merged = []
    for key, group in case_groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue
        
        fr_lower_set = {e['fr'].lower() for e in group}
        if len(fr_lower_set) == 1:
            best = max(group, key=lambda e: e['count'])
            best['count'] = sum(e['count'] for e in group)
            case_vars = [e['en'] for e in group if e['en'] != best['en']]
            if case_vars:
                best['case_variants'] = case_vars
            all_fr_variants = set()
            for e in group:
                for v in e.get('fr_variants', []):
                    all_fr_variants.add(v)
            if all_fr_variants:
                best['fr_variants'] = sorted(all_fr_variants)
            merged.append(best)
        else:
            merged.extend(group)
    
    return merged


def extract_table_translations(json_path):
    if not os.path.exists(json_path):
        print(f"Warning: {json_path} not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    raw = [e for e in raw if e.get('en') and e.get('fr')]
    
    # Step 1: Deduplicate by exact English key, pick highest-count French
    deduped = _deduplicate_entries(raw)
    
    # Step 1b: Align dash variants (e.g., CIOPS-W uses CIOPSW's French)
    deduped = _align_dash_variants(deduped)
    
    # Step 2: Strip trailing comma artifacts, then filter junk
    filtered = []
    filtered_out = []
    for entry in deduped:
        entry['en'] = entry['en'].rstrip(',')
        entry['fr'] = entry['fr'].rstrip(',')
        en_plain = _strip_formatting(entry['en'])
        fr_plain = _strip_formatting(entry['fr'])
        if _should_filter_entry(en_plain, fr_plain, entry['count']):
            filtered_out.append(entry)
            continue
        filtered.append(entry)
    
    # Step 3: Merge case variants where they agree on French translation
    merged = _merge_case_variants(filtered)
    
    # Step 4: Build output entries and extract sub-parts
    translations = []
    sub_parts = {}  # (en, fr) -> max count
    
    for entry in merged:
        en_raw = entry['en']
        fr_raw = entry['fr']
        en_plain = _strip_formatting(en_raw)
        fr_plain = _strip_formatting(fr_raw)
        has_fmt = _has_formatting(en_raw)
        
        out = {
            'english': en_plain,
            'french': fr_plain,
            'en_formatted': en_raw,
            'fr_formatted': fr_raw,
        }
        if entry.get('case_variants'):
            out['case_variants'] = entry['case_variants']
        if entry.get('fr_variants'):
            out['fr_variants'] = entry['fr_variants']
        
        translations.append(out)
        
        # Extract sub-parts from formatted entries
        if has_fmt:
            for en_part, fr_part in _extract_sub_parts(en_raw, fr_raw):
                key = (en_part, fr_part)
                sub_parts[key] = max(sub_parts.get(key, 0), entry['count'])
    
    # Step 5: Add sub-part entries not already covered by a direct entry
    direct_en_keys = {t['english'].lower() for t in translations}
    sub_part_count = 0
    for (en_part, fr_part), count in sub_parts.items():
        if en_part.lower() in direct_en_keys:
            continue
        translations.append({
            'english': en_part,
            'french': fr_part,
            'source': 'sub-part',
            'count': count,
        })
        sub_part_count += 1
    
    print(f"  Table: {len(translations)} entries "
          f"({len(filtered_out)} filtered, {sub_part_count} sub-parts extracted)")
    
    return translations


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


def generate_preferential_translations_json(spreadsheet_file=SPREADSHEET_FILE,
                                            place_names_csv=PLACE_NAMES_CSV,
                                            table_translations_file=TABLE_TRANSLATIONS_FILE,
                                            output_file=OUTPUT_FILE):
    print(f"Generating translation dictionaries from {spreadsheet_file}...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    technical_terms = extract_technical_terms(spreadsheet_file)
    species_names = extract_species_names(spreadsheet_file)
    acronyms_abbreviations = extract_acronyms_abbreviations(spreadsheet_file)
    place_names = extract_place_names(place_names_csv)
    table_translations = extract_table_translations(table_translations_file)
    place_names_sources = get_place_names_sources(spreadsheet_file)
    
    all_translations = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source_spreadsheet': os.path.basename(spreadsheet_file),
            'total_categories': 5
        },
        'translations': {
            'nomenclature': technical_terms,
            'taxon': species_names,
            'acronym': acronyms_abbreviations,
            'site': place_names,
            'table': table_translations
        },
        'sources': {
            'place_names_links': place_names_sources
        },
        'statistics': {
            'technical_terms_count': len(technical_terms),
            'species_names_count': len(species_names),
            'acronyms_abbreviations_count': len(acronyms_abbreviations),
            'place_names_count': len(place_names),
            'table_translations_count': len(table_translations),
            'total_translations': len(technical_terms) + len(species_names) + len(acronyms_abbreviations) + len(place_names) + len(table_translations)
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
    print(f"Table Translations: {stats['table_translations_count']}")
    print("-" * 50)
    print(f"Total Translations: {stats['total_translations']}")
    print(f"\nSaved to: {output_file}")
    
    return all_translations


if __name__ == "__main__":
    generate_preferential_translations_json()
