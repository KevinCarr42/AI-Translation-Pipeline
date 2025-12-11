import pandas as pd
from spellchecker import SpellChecker

legitimate_english = {'i', 'a'}
legitimate_french = {'à', 'a', 'y', 'ô', 'ù'}

contraction_patterns_english = {
    't': [
        'don', 'doesn', 'didn', 'won', 'wouldn', 'couldn', 'shouldn',
        'isn', 'aren', 'wasn', 'weren', 'hasn', 'haven', 'hadn',
        'ain', 'can',
    ],
    's': [
        'it', 'that', 'what', 'who', 'where', 'when', 'why', 'how',
        'there', 'here', 'everyone', 'everything', 'something',
        'nothing', 'he', 'she', 'this',
    ],
    'm': ['i'],
    'd': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'there', 'that', 'who', 'what'],
    'll': ['i', 'you', 'he', 'she', 'it', 'we', 'they', 'there', 'who', 'what'],
    've': ['i', 'you', 'we', 'they', 'would', 'could', 'should', 'might', 'must'],
    're': ['you', 'we', 'they', 'here', 'there', 'who', 'what'],
}

contraction_patterns_french = {
    'j': [
        'ai', 'avais', 'aurai', 'aurais', 'étais', 'avais', 'étais',
        'irai', 'irais', 'aime', 'adore', 'arrive', 'attends', 'entends',
        'espère', 'ignore', 'imagine', 'habite', 'ouvre'
    ],
    'l': [
        'a', 'est', 'avait', 'avait', 'avait', 'aurait', 'auront',
        'on', 'un', 'une', 'autre', 'homme', 'enfant', 'ami', 'amie',
        'air', 'eau', 'école', 'âge', 'indice'
    ],
    'd': [
        'un', 'une', 'abord', 'accord', 'ailleurs', 'après', 'autant',
        'entre', 'eux', 'elle', 'elles', 'ici', 'où'
    ],
    'n': [
        'a', 'ai', 'as', 'avons', 'avez', 'ont', 'es', 'est', 'êtes',
        'importe'
    ],
    'm': ['as', 'a', 'en', 'y', 'appelle', 'étais', 'étaient', 'étais'],
    't': ['as', 'a', 'es', 'est', 'y', 'en', 'il', 'elle', 'on'],
    's': ['il', 'ils', 'est', 'était', 'en', 'y'],
    'c': ['est', 'était', 'a', 'en'],
    'qu': ['il', 'ils', 'elle', 'elles', 'on', 'un', 'une', 'est', 'en'],
}


def has_single_letter_word(text):
    if not isinstance(text, str):
        return False
    words = text.split()
    for word in words:
        cleaned = word.strip('.,!?;:"\'-()[]{}')
        if len(cleaned) == 1:
            return True
    return False


def get_single_letter_words(text):
    if not isinstance(text, str):
        return []
    words = text.split()
    single_letters = []
    for i, word in enumerate(words):
        cleaned = word.strip('.,!?;:"\'-()[]{}')
        if len(cleaned) == 1:
            single_letters.append((i, cleaned.lower(), word))
    return single_letters


def is_legitimate_single_letter(letter, lang):
    letter_lower = letter.lower()
    if lang == 'en':
        return letter_lower in legitimate_english
    else:
        return letter_lower in legitimate_french


def check_missing_apostrophe(text, letter_info, lang):
    if not isinstance(text, str):
        return False, None
    words = text.split()
    idx, letter, original = letter_info
    letter_lower = letter.lower()
    
    if lang == 'en':
        patterns = contraction_patterns_english
    else:
        patterns = contraction_patterns_french
    
    if lang == 'en':
        if letter_lower in patterns:
            if idx > 0:
                prev_word = words[idx - 1].strip('.,!?;:"\'-()[]{}').lower()
                if prev_word in patterns[letter_lower]:
                    return True, f"{prev_word} {letter}"
        
        for pattern_letter, preceding_words in patterns.items():
            if letter_lower in preceding_words:
                if idx < len(words) - 1:
                    next_word = words[idx + 1].strip('.,!?;:"\'-()[]{}').lower()
                    if next_word == pattern_letter:
                        return True, f"{letter} {next_word}"
    else:
        if letter_lower in patterns:
            if idx < len(words) - 1:
                next_word = words[idx + 1].strip('.,!?;:"\'-()[]{}').lower()
                if next_word in patterns[letter_lower]:
                    return True, f"{letter} {next_word}"
    
    return False, None


def analyze_row(row):
    issues = []
    
    source_text = row['source']
    source_lang = row['source_lang']
    lang = 'en' if source_lang == 'en' else 'fr'
    
    singles = get_single_letter_words(source_text)
    for letter_info in singles:
        idx, letter, original = letter_info
        if not is_legitimate_single_letter(letter, lang):
            is_apostrophe, pattern = check_missing_apostrophe(source_text, letter_info, lang)
            if is_apostrophe:
                issues.append(('missing_apostrophe', pattern, source_text))
            else:
                issues.append(('ocr_or_other', letter, source_text))
    
    return issues


def create_filtered_dataframe(filename):
    df = pd.read_json(filename, lines=True)
    df['has_single_letter'] = df.apply(
        lambda row: has_single_letter_word(row['source']),
        axis=1
    )
    return df[df['has_single_letter']].copy()


def create_results_dataframe(dataframe):
    results = []
    for idx, row in dataframe.iterrows():
        issues = analyze_row(row)
        for issue in issues:
            results.append({
                'original_index': idx,
                'source': row['source'],
                'source_lang': row['source_lang'],
                'issue_type': issue[0],
                'pattern': issue[1],
                'text_with_issue': issue[2]
            })
    
    return pd.DataFrame(results)


def print_results(filtered_dataframe, results_dataframe, verbose=True):
    if not results_dataframe.empty:
        summary_df = results_dataframe.drop_duplicates(subset=['pattern']).sort_values('pattern').reset_index(drop=True)
        
        print(f"Total rows with single letter words: {len(filtered_dataframe)}")
        print(f"Total issues found: {len(results_dataframe)}")
        print(f"Unique patterns: {len(summary_df)}")
        print(f"Missing apostrophe issues: {len(results_dataframe[results_dataframe['issue_type'] == 'missing_apostrophe'])}")
        print(f"Potential OCR issues: {len(results_dataframe[results_dataframe['issue_type'] == 'ocr_or_other'])}")
        if verbose:
            print("\n--- Summary of Patterns ---")
            for _, row in summary_df.iterrows():
                print(f"{row['pattern']:<15}{row['text_with_issue']}")
    else:
        print("No issues found")


def extract_contractions_from_data(dataframe_pickle, lang='fr'):
    dataframe = pd.read_pickle(dataframe_pickle)
    
    contractions_found = {}
    spell = SpellChecker(language=lang)
    
    col_name = lang
    if col_name not in dataframe.columns:
        return {}
    
    for idx, row in dataframe.iterrows():
        if pd.notna(row[col_name]):
            text = row[col_name]
            words = text.split()
            
            for word in words:
                if "'" in word or "'" in word:
                    parts = word.replace("'", "'").split("'")
                    if len(parts) == 2:
                        before, after = parts
                        before = before.strip('.,!?;:"\'-()[]{}').lower()
                        after = after.strip('.,!?;:"\'-()[]{}').lower()
                        
                        if len(before) <= 2 and len(after) > 0 and len(before) > 0:
                            if any(c.isdigit() for c in before):
                                continue
                            if any(c.isdigit() for c in after):
                                continue
                            if spell.known([after]):
                                if before not in contractions_found:
                                    contractions_found[before] = set()
                                contractions_found[before].add(after)
    
    for letter in contractions_found:
        contractions_found[letter] = sorted(list(contractions_found[letter]))
    
    return contractions_found


def check_space_apostrophe_patterns(dataframe_pickle, lang='fr'):
    dataframe = pd.read_pickle(dataframe_pickle)
    
    patterns_found = []
    spell = SpellChecker(language=lang)
    
    col_name = lang
    if col_name not in dataframe.columns:
        return pd.DataFrame()
    
    for idx, row in dataframe.iterrows():
        if pd.notna(row[col_name]):
            text = row[col_name]
            words = text.split()
            
            for i in range(len(words)):
                if words[i].endswith("'") or words[i].endswith("'"):
                    if i < len(words) - 1:
                        pattern = words[i]
                        next_word = words[i + 1]
                        expanded_pattern = f"{pattern} {next_word}"
                        
                        next_word_clean = next_word.strip('.,!?;:"\'-()[]{}').lower()
                        if next_word_clean and spell.known([next_word_clean]):
                            cleaned = pattern + next_word
                        else:
                            cleaned = None
                        
                        patterns_found.append({
                            'original': text,
                            'pattern': pattern,
                            'expanded_pattern': expanded_pattern,
                            'cleaned': cleaned
                        })
                
                if words[i].startswith("'") or words[i].startswith("'"):
                    if i > 0:
                        prev_word = words[i - 1]
                        pattern = words[i]
                        expanded_pattern = f"{prev_word} {pattern}"
                        
                        word_clean = words[i][1:].strip('.,!?;:"\'-()[]{}').lower()
                        if word_clean and spell.known([word_clean]):
                            cleaned = prev_word + words[i]
                        else:
                            cleaned = None
                        
                        patterns_found.append({
                            'original': text,
                            'pattern': pattern,
                            'expanded_pattern': expanded_pattern,
                            'cleaned': cleaned
                        })
    
    return pd.DataFrame(patterns_found)


def create_cleaning_dict_from_space_patterns(space_patterns_df):
    cleaning_dict = {}
    
    for _, row in space_patterns_df.iterrows():
        if pd.notna(row['cleaned']) and row['cleaned'] is not None:
            cleaning_dict[row['expanded_pattern']] = row['cleaned']
    
    return cleaning_dict


def check_uncleaned_data(dataframe_pickle):
    dataframe = pd.read_pickle(dataframe_pickle)
    
    potential_patterns = []
    
    for idx, row in dataframe.iterrows():
        if 'en' in dataframe.columns and pd.notna(row['en']):
            text = row['en']
            singles = get_single_letter_words(text)
            for letter_info in singles:
                letter_idx, letter, original = letter_info
                if letter.isdigit():
                    continue
                if not is_legitimate_single_letter(letter, 'en'):
                    is_known, _ = check_missing_apostrophe(text, letter_info, 'en')
                    if not is_known:
                        words = text.split()
                        if letter_idx > 0:
                            prev_word = words[letter_idx - 1].strip('.,!?;:"\'-()[]{}').lower()
                            potential_patterns.append({
                                'language': 'en',
                                'letter': letter,
                                'other_word': prev_word,
                                'direction': 'after',
                                'pattern': f"{prev_word} {letter}",
                                'example_text': text
                            })
                        if letter_idx < len(words) - 1:
                            next_word = words[letter_idx + 1].strip('.,!?;:"\'-()[]{}').lower()
                            potential_patterns.append({
                                'language': 'en',
                                'letter': letter,
                                'other_word': next_word,
                                'direction': 'before',
                                'pattern': f"{letter} {next_word}",
                                'example_text': text
                            })
        
        if 'fr' in dataframe.columns and pd.notna(row['fr']):
            text = row['fr']
            singles = get_single_letter_words(text)
            for letter_info in singles:
                letter_idx, letter, original = letter_info
                if letter.isdigit():
                    continue
                if not is_legitimate_single_letter(letter, 'fr'):
                    is_known, _ = check_missing_apostrophe(text, letter_info, 'fr')
                    if not is_known:
                        words = text.split()
                        if letter_idx > 0:
                            prev_word = words[letter_idx - 1].strip('.,!?;:"\'-()[]{}').lower()
                            potential_patterns.append({
                                'language': 'fr',
                                'letter': letter,
                                'other_word': prev_word,
                                'direction': 'after',
                                'pattern': f"{prev_word} {letter}",
                                'example_text': text
                            })
                        if letter_idx < len(words) - 1:
                            next_word = words[letter_idx + 1].strip('.,!?;:"\'-()[]{}').lower()
                            potential_patterns.append({
                                'language': 'fr',
                                'letter': letter,
                                'other_word': next_word,
                                'direction': 'before',
                                'pattern': f"{letter} {next_word}",
                                'example_text': text
                            })
    
    results_df = pd.DataFrame(potential_patterns)
    
    if not results_df.empty:
        summary_df = results_df.groupby(['language', 'letter', 'other_word', 'direction', 'pattern']).agg({
            'example_text': 'first',
            'pattern': 'size'
        }).rename(columns={'pattern': 'count'}).reset_index()
        summary_df = summary_df.sort_values(['language', 'count'], ascending=[True, False])
        
        print(f"\nTotal potential patterns found: {len(summary_df)}")
        print(f"English patterns: {len(summary_df[summary_df['language'] == 'en'])}")
        print(f"French patterns: {len(summary_df[summary_df['language'] == 'fr'])}")
        
        return summary_df
    else:
        print("No potential patterns found")
        return pd.DataFrame()
