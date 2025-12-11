import pandas as pd

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
        'air', 'eau', 'école', 'âge'
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
    
    if letter_lower in patterns:
        if idx > 0:
            prev_word = words[idx - 1].strip('.,!?;:"\'-()[]{}').lower()
            if prev_word in patterns[letter_lower]:
                return True, f"{prev_word} {letter}"
        if idx < len(words) - 1:
            next_word = words[idx + 1].strip('.,!?;:"\'-()[]{}').lower()
            if next_word in patterns[letter_lower]:
                return True, f"{letter} {next_word}"
    
    for pattern_letter, preceding_words in patterns.items():
        if letter_lower in preceding_words:
            if idx < len(words) - 1:
                next_word = words[idx + 1].strip('.,!?;:"\'-()[]{}').lower()
                if next_word == pattern_letter:
                    return True, f"{letter} {next_word}"
            if idx > 0:
                prev_word = words[idx - 1].strip('.,!?;:"\'-()[]{}').lower()
                if prev_word == pattern_letter:
                    return True, f"{prev_word} {letter}"
    
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


if __name__ == '__main__':
    # filename = "../../Data/training_data.jsonl"
    filename = "../../Data/pipe_recalc6/pipeline_training_data.jsonl"
    # filename = "../../Data/pipeline_testing_data.jsonl"
    
    filtered_df = create_filtered_dataframe(filename)
    results_df = create_results_dataframe(filtered_df)
    print_results(filtered_df, results_df)
