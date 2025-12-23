import json
import sys
import os


def migrate_terminology(old_path, new_path):
    if not os.path.exists(old_path):
        print(f"Error: Old terminology file not found at {old_path}")
        print("Creating empty template instead...")
        create_empty_template(new_path)
        return
    
    with open(old_path, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
    
    new_data = {
        "en_to_fr": {},
        "fr_to_en": {}
    }
    
    needs_manual_review = []
    
    if "en_to_fr" in old_data:
        for source_term, token in old_data["en_to_fr"].items():
            print(f"Found en->fr: {source_term} -> {token}")
            needs_manual_review.append({
                "source": source_term,
                "token": token,
                "direction": "en_to_fr",
                "note": "Please provide French translation with proper article (le/la/l'/les)"
            })
    
    if "fr_to_en" in old_data:
        for source_term, token in old_data["fr_to_en"].items():
            print(f"Found fr->en: {source_term} -> {token}")
            new_data["fr_to_en"][source_term] = source_term
    
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nMigration template saved to {new_path}")
    print(f"\nWARNING: {len(needs_manual_review)} entries require manual review!")
    print("\nEntries needing manual review:")
    for entry in needs_manual_review:
        print(f"  - {entry['source']} ({entry['direction']}): {entry['note']}")
    
    if needs_manual_review:
        review_file = new_path.replace('.json', '_review.json')
        with open(review_file, 'w', encoding='utf-8') as f:
            json.dump(needs_manual_review, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed review list saved to {review_file}")


def create_empty_template(new_path):
    template = {
        "en_to_fr": {
            "example term": "le terme exemple",
            "table": "la table",
            "dog": "le chien",
            "computer": "l'ordinateur"
        },
        "fr_to_en": {
            "le terme exemple": "the example term",
            "la table": "the table",
            "le chien": "the dog",
            "l'ordinateur": "the computer"
        }
    }
    
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    
    print(f"Empty template created at {new_path}")
    print("\nTemplate includes example entries. Please replace with your actual terminology.")
    print("\nIMPORTANT: For French translations, include the appropriate article:")
    print("  - le (masculine singular)")
    print("  - la (feminine singular)")
    print("  - l' (before vowel/silent h)")
    print("  - les (plural)")


if __name__ == "__main__":
    # FIXME no cli
    if len(sys.argv) < 3:
        print("Usage: python migrate_terminology.py <old_path> <new_path>")
        print("\nExample:")
        print("  python scripts/migrate_terminology.py ../Data/preferential_translations.json terminology.json")
        sys.exit(1)
    
    old_path = sys.argv[1]
    new_path = sys.argv[2]
    
    migrate_terminology(old_path, new_path)
