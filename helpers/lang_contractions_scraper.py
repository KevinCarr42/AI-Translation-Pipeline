from collections import defaultdict
import requests
from bs4 import BeautifulSoup

contraction_patterns_english = {
    't': ['don', 'doesn', 'didn', 'won', 'wouldn', 'couldn', 'shouldn',
          'isn', 'aren', 'wasn', 'weren', 'hasn', 'haven', 'hadn', 'can',
          'ain', 'it', 'that'],
    's': ['it', 'that', 'what', 'he', 'she', 'there', 'here', 'let',
          'where', 'who'],
    'm': ['i'],
    'd': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'who', 'what',
          'there'],
    'll': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'who', 'what',
           'there'],
    've': ['i', 'you', 'we', 'they', 'would', 'could', 'should', 'might',
           'must'],
    're': ['you', 'we', 'they', 'who', 'what', 'there', 'here', 'where'],
}

contraction_patterns_french = {
    'j': ['ai', 'avais', 'aurai', 'aurais', 'étais', 'en', 'y', 'irai',
          'irais', 'espère', 'aime', 'adore', 'habite', 'arrive',
          'entends', 'attends', 'ouvre', 'écoute', 'imagine', 'ignore',
          'accepte', 'apprends', 'appelle', 'essaie', 'essaye', 'entends'],
    'l': ['a', 'est', 'était', 'ont', 'avait', 'aura', 'aurait', 'on',
          'un', 'une', 'autre', 'homme', 'eau', 'air', 'or', 'argent',
          'amour', 'ami', 'amie', 'enfant', 'église', 'école', 'Europe',
          'Amérique', 'Afrique', 'Asie', 'Italie', 'Espagne', 'Allemagne',
          'Angleterre'],
    'd': ['un', 'une', 'abord', 'accord', 'autres', 'ailleurs', 'après',
          'autant', 'entre', 'eux', 'elle', 'elles', 'ici', 'où', 'avoir',
          'être'],
    'n': ['a', 'ai', 'as', 'avons', 'avez', 'ont', 'est', 'es', 'êtes',
          'y', 'en', 'importe', 'oublie', 'oubliez'],
    'm': ['a', 'as', 'avez', 'en', 'y', 'appelle', 'ont', 'est'],
    't': ['a', 'as', 'en', 'y', 'ont', 'es', 'est', 'aime', 'appelle',
          'inquiète', 'il', 'elle', 'on'],
    's': ['il', 'ils', 'en', 'y', 'est', 'était', 'appelle', 'agit',
          'avère'],
    'c': ['est', 'était', 'a', 'en'],
    'qu': ['il', 'ils', 'elle', 'elles', 'on', 'un', 'une', 'est', 'en',
           'à', 'au', 'aux', 'y'],
}

EN_CONTRACTION_SOURCE = "https://en.wikipedia.org/wiki/Wikipedia:List_of_English_contractions"

FRENCH_ELIDABLE_KEYS_CANONICAL = {
    "j", "m", "t", "s", "n", "d", "l", "qu", "c",
    "jusqu", "lorsqu", "puisqu", "quoiqu",
}

EN_SUFFIXES_OF_INTEREST = set(contraction_patterns_english.keys())


def fetch_english_contractions_from_wikipedia(url=EN_CONTRACTION_SOURCE):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    contractions = set()
    for table in soup.select("table.wikitable"):
        for row in table.select("tr")[1:]:
            cells = row.select("td")
            if not cells:
                continue
            raw = cells[0].get_text(strip=True)
            if not raw:
                continue
            first = raw.split()[0].split("/")[0]
            if "'" not in first:
                continue
            contractions.add(first.lower())
    return contractions


def build_suffix_prefix_map(contractions):
    patterns = defaultdict(set)
    for c in contractions:
        if not all(32 <= ord(ch) < 127 or ch == "’" for ch in c):
            continue
        c = c.replace("’", "'")
        if "'" not in c:
            continue
        idx = c.rfind("'")
        prefix = c[:idx]
        suffix = c[idx + 1:]
        if not prefix or not suffix:
            continue
        if suffix not in EN_SUFFIXES_OF_INTEREST:
            continue
        patterns[suffix].add(prefix)
    return patterns


def diff_english_patterns(static_patterns, reference_patterns):
    missing = {}
    extra = {}
    for suffix in EN_SUFFIXES_OF_INTEREST:
        static_set = set(static_patterns.get(suffix, []))
        ref_set = reference_patterns.get(suffix, set())
        miss = sorted(ref_set - static_set)
        ext = sorted(static_set - ref_set)
        if miss:
            missing[suffix] = miss
        if ext:
            extra[suffix] = ext
    return missing, extra


def diff_french_keys(static_patterns):
    static_keys = set(static_patterns.keys())
    missing_keys = FRENCH_ELIDABLE_KEYS_CANONICAL - static_keys
    extra_keys = static_keys - FRENCH_ELIDABLE_KEYS_CANONICAL
    return missing_keys, extra_keys


def main():
    print(f"English reference source: {EN_CONTRACTION_SOURCE}")
    print("Fetching English contractions from Wikipedia...")
    wiki_contractions = fetch_english_contractions_from_wikipedia()
    print(f"  Found {len(wiki_contractions)} contractions with apostrophes.")
    
    print("\nBuilding reference suffix->prefix map...")
    reference_map = build_suffix_prefix_map(wiki_contractions)
    
    print("\nComparing to your static contraction_patterns_english...")
    missing, extra = diff_english_patterns(contraction_patterns_english, reference_map)
    
    if not missing:
        print("  No missing prefixes.")
    else:
        print("  Missing prefixes:")
        for suffix, prefixes in sorted(missing.items()):
            print(f"    {suffix}: {', '.join(prefixes)}")
    
    if not extra:
        print("  No extra prefixes.")
    else:
        print("  Extra prefixes:")
        for suffix, prefixes in sorted(extra.items()):
            print(f"    {suffix}: {', '.join(prefixes)}")
    
    print("\nFrench elision sanity check...")
    missing_fr, extra_fr = diff_french_keys(contraction_patterns_french)
    
    if not missing_fr:
        print("  All canonical prefixes covered.")
    else:
        print("  Missing French elidable keys:", ", ".join(sorted(missing_fr)))
    
    if extra_fr:
        print("  Extra French keys:", ", ".join(sorted(extra_fr)))


if __name__ == "__main__":
    main()
