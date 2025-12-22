import csv
import json
import os
import random
import re
import tempfile
from translate.document import translate_document
from translate.models import create_translator
from create_training_data.language_classifier.language_classifier import LanguageClassifier
from create_training_data.match_languages import clean_text


def get_paragraphs(folder, n_paragraphs_per_lang=10):
    def is_good_paragraph(paragraph_text):
        min_paragraph_char = 100
        min_alpha_proportion = 0.95
        minimum_periods = 2
        
        n_periods = sum(char == "." for char in paragraph_text)
        if n_periods < minimum_periods:
            return False
        
        n_alpha = sum(char.isalpha() or char.isspace() for char in paragraph_text)
        if n_alpha < min_paragraph_char:
            return False
        
        alpha_proportion = n_alpha / len(paragraph_text)
        return alpha_proportion >= min_alpha_proportion
    
    if not os.path.exists(folder):
        raise ValueError(f"Folder does not exist: {folder}")
    
    output_list = []
    min_char = 2000
    n_en, n_fr = n_paragraphs_per_lang, n_paragraphs_per_lang
    
    all_files = [os.path.join(folder, f) for f in os.listdir(folder)
                 if os.path.isfile(os.path.join(folder, f)) and f.endswith('.json')]
    
    if not all_files:
        raise ValueError(f"No JSON files found in folder: {folder}")
    
    classifier = LanguageClassifier()
    
    while n_en > 0 or n_fr > 0:
        if not all_files:
            break
        
        random_file = random.choice(all_files)
        all_files.remove(random_file)
        
        with open(random_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'text' not in data:
            continue
        
        content = data['text']
        
        if len(content) < min_char:
            continue
        
        paragraphs = re.split(r'\n\n+', content)
        
        cleaned_paragraphs = [clean_text(p) for p in paragraphs if is_good_paragraph(p)]
        
        if len(cleaned_paragraphs) < 2:
            continue
        
        p_lang = classifier.classify(cleaned_paragraphs[1])
        
        if p_lang == 'en' and n_en <= 0:
            continue
        if p_lang == 'fr' and n_fr <= 0:
            continue
        if p_lang not in ['en', 'fr']:
            continue
        
        for cleaned_paragraph in cleaned_paragraphs:
            temp_file = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False)
            temp_file.write(cleaned_paragraph)
            temp_file.close()
            
            output_list.append((temp_file.name, p_lang))
            
            if p_lang == 'en':
                n_en -= 1
            else:
                n_fr -= 1
    
    return output_list


if __name__ == '__main__':
    use_finetuned = False
    file_list = get_paragraphs(r"..\Data\ParsedPublications\2024")
    translation_manager = create_translator(use_finetuned=use_finetuned, debug=True)
    
    global_idx = 0
    for filepath, source_lang in file_list:
        global_idx = translate_document(
            input_text_file=filepath,
            output_text_file=None,
            source_lang=source_lang,
            chunk_by="paragraph",
            models_to_use=None,
            use_find_replace=True,
            use_finetuned=use_finetuned,
            translation_manager=translation_manager,
            start_idx=global_idx
        )
    
    error_data = translation_manager.extra_token_errors
    retry_debug_data = translation_manager.token_retry_debug
    
    if error_data:
        with open('token_errors.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'model_name', 'use_find_replace', 'tokens_to_replace',
                             'retry_attempts', 'original_text', 'translated_text'])
            
            for key, value in error_data.items():
                writer.writerow([
                    key,
                    value.get('model_name', ''),
                    value.get('use_find_replace', ''),
                    str(value.get('tokens_to_replace', [])),
                    value.get('retry_attempts', 0),
                    value.get('original_text', ''),
                    value.get('translated_text', '')
                ])
        print(f"Saved {len(error_data)} token errors to token_errors.csv")
    
    if retry_debug_data:
        with open('token_retry_debug.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'model_name', 'total_attempts', 'success',
                             'attempt_number', 'missing_tokens', 'params', 'original_text'])
            
            for key, value in retry_debug_data.items():
                model_name = value.get('model_name', '')
                total_attempts = value.get('total_attempts', 0)
                success = value.get('success', False)
                original_text = value.get('original_text', '')
                
                for failed_attempt in value.get('failed_attempts', []):
                    writer.writerow([
                        key,
                        model_name,
                        total_attempts,
                        success,
                        failed_attempt.get('attempt', ''),
                        ', '.join(failed_attempt.get('missing_tokens', [])),
                        str(failed_attempt.get('params', {})),
                        original_text
                    ])
                
                if not value.get('failed_attempts'):
                    writer.writerow([
                        key,
                        model_name,
                        total_attempts,
                        success,
                        '',
                        '',
                        '',
                        original_text
                    ])
        print(f"Saved {len(retry_debug_data)} retry debug entries to token_retry_debug.csv")
