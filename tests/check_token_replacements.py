import csv
import json
import os
import random
import re
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
        
        test_paragraphs_dir = os.path.join(os.path.dirname(__file__), 'paragraphs')
        os.makedirs(test_paragraphs_dir, exist_ok=True)
        
        for para_idx, cleaned_paragraph in enumerate(cleaned_paragraphs):
            base_filename = f"{os.path.splitext(os.path.basename(random_file))[0]}_para{para_idx}_{p_lang}.txt"
            filepath = os.path.join(test_paragraphs_dir, base_filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(cleaned_paragraph)
            
            output_list.append((filepath, p_lang))
            
            if p_lang == 'en':
                n_en -= 1
            else:
                n_fr -= 1
    
    print('total paragraphs =', len(output_list))
    return output_list


if __name__ == '__main__':
    use_finetuned = False
    file_list = get_paragraphs(r"..\Data\ParsedPublications\2024", 2)
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
    
    error_data = translation_manager.find_replace_errors
    
    if error_data:
        with open('find_replace_errors.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['key', 'original_text', 'preprocessed_text', 'translated_text', 'applied_replacements'])
            
            for key, value in error_data.items():
                writer.writerow([
                    key,
                    value.get('original_text', ''),
                    value.get('preprocessed_text', ''),
                    value.get('translated_text', ''),
                    str(value.get('applied_replacements', {}))
                ])
        print(f"Saved {len(error_data)} find/replace errors to find_replace_errors.csv")
