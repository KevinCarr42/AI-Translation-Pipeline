import json
import os
import re


def clean_text(text, skip_cleaning=False):
    allow_numbers = True

    if not skip_cleaning:
        if allow_numbers:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
        else:
            allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ.,;:!?()'\"-]"
        text = re.sub(allowed_chars, ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

    return text


def get_files_for_publication(pub_number, correlation_dataframe):
    row = correlation_dataframe.loc[correlation_dataframe['pub_number'] == pub_number]
    if not row.empty:
        filename_fr = row['filename_fr'].values[0]
        filename_en = row['filename_en'].values[0]
        return filename_fr, filename_en
    return None, None


def get_json_file_link(parsed_docs_folder, pdf_filename):
    if pdf_filename.endswith(".pdf"):
        json_filename = pdf_filename + ".json"
        for root, _, files in os.walk(parsed_docs_folder):
            if json_filename in files:
                return os.path.join(root, json_filename)
    return None


def extract_text_from_single_file(json_file, target_language, language_classifier, skip_cleaning=False, linebreaks=True):
    min_block_length = 10
    max_block_length = 500

    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    if 'text' not in data:
        raise KeyError(f"The key 'text' is missing in the JSON file: {json_file}")

    full_text = clean_text(data['text'], skip_cleaning)
    if linebreaks:
        text_blocks = re.split(r'(?<![;,])[.?!]\s|\n\n', full_text)
    else:
        text_blocks = re.split(r'(?<![;,])[.?!]\s', full_text)
    text = []

    for block in text_blocks:
        block = block.strip()
        if len(block) < min_block_length or len(block) > max_block_length:
            continue

        if language_classifier.classify(block) == target_language:
            text.append(block + '. ')

    return " ".join(text)


def extract_both_languages_from_two_files(json_file_fr, json_file_en, language_classifier, linebreaks=True):
    return (extract_text_from_single_file(json_file_fr, "fr", language_classifier, linebreaks=linebreaks),
            extract_text_from_single_file(json_file_en, "en", language_classifier, linebreaks=linebreaks))


def extract_both_languages_from_single_file(json_file, language_classifier, linebreaks=True):
    min_block_length = 10
    max_block_length = 500

    with open(json_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    if 'text' not in data:
        raise KeyError(f"The key 'text' is missing in the JSON file: {json_file}")

    full_text = clean_text(data['text'], skip_cleaning=False)
    if linebreaks:
        text_blocks = re.split(r'(?<![;,])[.?!]\s|\n\n', full_text)
    else:
        text_blocks = re.split(r'(?<![;,])[.?!]\s', full_text)

    text_fr, text_en = [], []

    for block in text_blocks:
        block = block.strip()
        if len(block) < min_block_length or len(block) > max_block_length:
            continue

        lang = language_classifier.classify(block)
        if lang == "fr":
            text_fr.append(block + '. ')
        elif lang == "en":
            text_en.append(block + '. ')

    return " ".join(text_fr), " ".join(text_en)
