import json


if __name__ == '__main__':
    with open("../../Data/preferential_translations.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    nomenclature_fr = data['translations']['nomenclature']
    taxon_fr = data['translations']['taxon']
    acronym_fr = data['translations']['acronym']
    site_fr = data['translations']['site']
    
    nomenclature_en = {v: k for k, v in nomenclature_fr.items()}
    taxon_en = {v: k for k, v in taxon_fr.items()}
    acronym_en = {v: k for k, v in acronym_fr.items()}
    site_en = {v: k for k, v in site_fr.items()}
    
    output_dict = {
        'fr_to_en': nomenclature_fr | taxon_fr | acronym_fr | site_fr,
        'en_to_fr': nomenclature_en | taxon_en | acronym_en | site_en
    }
    
    with open("../../Data/preferential_translations_simplified.json", 'w', encoding='utf-8') as f:
        json.dump(output_dict, f, ensure_ascii=False, indent=2)
