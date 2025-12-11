import re


def clean_text(text):
    allow_numbers = True
    
    if allow_numbers:
        allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ0-9.,;:!?()'\"-]"
    else:
        allowed_chars = r"[^a-zA-ZÀ-ÖØ-öø-ÿ.,;:!?()'\"-]"
    text = re.sub(allowed_chars, ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def clean_data(dataframe):
    # cleaning formerly done in create_matched_data()
    dataframe['fr'] = dataframe['fr'].apply(clean_text)
    dataframe['en'] = dataframe['en'].apply(clean_text)
    
    # NOTE: OCR errors are no longer being cleaned
    # they are just flagged for removal to improve data quality
    
    return dataframe
