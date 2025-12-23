# Plan: Preserve Language Classification Metadata in match_languages

## Problem

The `match_languages.py` pipeline currently:
1. Splits text into blocks using `split_text()` (sophisticated abbreviation-aware regex)
2. Classifies each block with `clf.classify(block)`
3. Concatenates classified blocks into single strings: `text_fr` and `text_en`
4. Re-splits these concatenated strings using simpler regex in `create_sentences()`
5. **Language metadata is lost** during concatenation

This creates inefficiency:
- Blocks are split, concatenated, then split again
- Language classification metadata is discarded
- Can't track which sentences came from which classified blocks

## Solution

Adopt the **parallel lists pattern** from `translate/document.py` (recently implemented in commit eb6beca):
- Keep sentences and metadata in parallel lists
- Eliminate the concatenate-and-resplit step
- Preserve language classification throughout the pipeline

## Implementation Steps

### 1. Create `split_and_classify_text()` function

**Purpose:** Replace the split-concatenate pattern with split-and-preserve pattern.

```python
def split_and_classify_text(json_file, clf, min_block_length=10, max_block_length=500):
    text_blocks = load_and_split_text(json_file)
    sentences = []
    sentence_metadata = []

    for block_idx, block in enumerate(text_blocks):
        block = clean_text(block)
        if len(block) < min_block_length or len(block) > max_block_length:
            continue

        lang = clf.classify(block)
        block_sentences = split_text(block)

        for sent_idx, sentence in enumerate(block_sentences):
            sentence = sentence.strip()
            if sentence:
                sentences.append(sentence)
                sentence_metadata.append({
                    'block_idx': block_idx,
                    'lang': lang,
                    'sent_idx': sent_idx,
                    'is_last_in_block': sent_idx == len(block_sentences) - 1
                })

    return sentences, sentence_metadata
```

**Key decisions:**
- Use `split_text()` exclusively (has abbreviation handling), not the simpler regex
- Classify once per block, apply to all sentences from that block
- Use dict metadata matching the pattern in `document.py`

### 2. Create `filter_by_language()` helper

**Purpose:** Extract sentences matching a target language.

```python
def filter_by_language(sentences, sentence_metadata, target_language):
    filtered_sentences = []
    filtered_metadata = []

    for sentence, metadata in zip(sentences, sentence_metadata):
        lang = metadata['lang']
        if lang == target_language or lang == 'mixed':
            filtered_sentences.append(sentence)
            filtered_metadata.append(metadata)

    return filtered_sentences, filtered_metadata
```

**Edge case handling:**
- Include 'mixed' blocks in both FR and EN (may contain both languages)
- Skip 'unknown' blocks entirely

### 3. Update `extract_text_from_single_file()`

**Before:** Returns concatenated string `" ".join(text)`

**After:** Returns parallel lists `(sentences, metadata)`

```python
def extract_text_from_single_file(json_file, target_language, clf):
    sentences, sentence_metadata = split_and_classify_text(json_file, clf)
    return filter_by_language(sentences, sentence_metadata, target_language)
```

### 4. Update `extract_both_languages_from_single_file()`

**Before:** Returns `(text_fr_string, text_en_string)`

**After:** Returns nested tuples `((sentences_fr, metadata_fr), (sentences_en, metadata_en))`

```python
def extract_both_languages_from_single_file(json_file, clf):
    sentences, sentence_metadata = split_and_classify_text(json_file, clf)

    sentences_fr, metadata_fr = filter_by_language(sentences, sentence_metadata, "fr")
    sentences_en, metadata_en = filter_by_language(sentences, sentence_metadata, "en")

    return (sentences_fr, metadata_fr), (sentences_en, metadata_en)
```

### 5. Update `extract_both_languages_from_two_files()`

**Before:** Returns `(text_fr_string, text_en_string)`

**After:** Returns nested tuples for consistency

```python
def extract_both_languages_from_two_files(json_file_fr, json_file_en, clf):
    sentences_fr, metadata_fr = extract_text_from_single_file(json_file_fr, "fr", clf)
    sentences_en, metadata_en = extract_text_from_single_file(json_file_en, "en", clf)

    return (sentences_fr, metadata_fr), (sentences_en, metadata_en)
```

### 6. Delete `create_sentences()` function

**Lines 122-126** - This function becomes obsolete. It currently re-splits concatenated text, but we're already splitting in step 1.

### 7. Update `correlate_text()` function

**Before:** Accepts `(text_fr, text_en)` strings, calls `create_sentences()` to split them

**After:** Accepts pre-split parallel lists, no splitting needed

```python
def correlate_text(sentences_fr, metadata_fr, sentences_en, metadata_en, pub_number, sentence_encoder, device):
    similarity_matrix = create_similarity_matrix(sentences_fr, sentences_en, sentence_encoder, device)
    aligned_pairs = align_sentences(similarity_matrix)

    return text_from_coordinates(aligned_pairs, sentences_fr, sentences_en, pub_number)
```

**Changes:**
- 4 parameters instead of 2 (parallel lists pattern)
- Remove `create_sentences()` call
- Metadata available if needed for future enhancements

### 8. Update `process_row()` function

**Lines 210-227** - Update to handle new return format and quality checks

```python
if filename_fr == filename_en:
    (sentences_fr, metadata_fr), (sentences_en, metadata_en) = extract_both_languages_from_single_file(fr_link, language_classifier)
else:
    en_link = get_json_file_link(parsed_docs_folder, filename_en)
    if en_link is None:
        return None
    (sentences_fr, metadata_fr), (sentences_en, metadata_en) = extract_both_languages_from_two_files(fr_link, en_link, language_classifier)

# Quality checks on sentence lists instead of concatenated strings
min_char = 1000
len_fr = sum(len(s) for s in sentences_fr)
len_en = sum(len(s) for s in sentences_en)

if len_fr == 0 or len_en == 0:
    return None
elif len_fr < min_char or len_en < min_char:
    return None

return correlate_text(sentences_fr, metadata_fr, sentences_en, metadata_en, pub_number, sentence_encoder, device)
```

**Changes:**
- Unpack nested tuples to get sentences and metadata
- Calculate total character length by summing sentence lengths (instead of `len(text_fr)`)
- Pass metadata to `correlate_text()`

## Benefits

1. **Eliminates redundancy:** No more split-concatenate-split cycle
2. **Preserves metadata:** Language classification tracked throughout pipeline
3. **Better splitting:** Uses only the sophisticated `split_text()` with abbreviation handling
4. **Follows existing patterns:** Matches `document.py` parallel lists approach
5. **Enables future enhancements:** Can add classifier confidence, re-classify specific sentences, or trace back to original blocks
6. **Backward compatible:** Final output format unchanged - still returns `[(pub_number, sent_fr, sent_en, similarity), ...]`

## Edge Cases Handled

- **Mixed-language blocks:** Included in both FR and EN lists (captures bilingual content)
- **Unknown language blocks:** Filtered out entirely
- **Empty blocks after filtering:** Already handled by length checks
- **Single-file vs two-file processing:** Both return same data structure
- **Empty sentences after splitting:** Filtered with `if sentence:` check

## Critical File

- `C:\Users\CARRK\Documents\Repositories\AI\Pipeline\create_training_data\match_languages.py` - All changes in this single file
