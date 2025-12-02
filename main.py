import os
import config

from data_cleaning import data_cleaning_pipeline
from model_finetuning import finetuning_pipeline
from translate import translation_pipeline

if __name__ == "__main__":
    clean_data = True
    finetune_models = False
    translate_data = False
    
    if clean_data:
        data_cleaning_pipeline()
    
    if finetune_models:
        finetuning_pipeline()
    
    if translate_data:
        # inputted
        with_preferential_translation = True
        input_text_filename = "input_file.txt"
        source_lang = "en"
        
        # calculated
        target_lang = "fr" if source_lang == "en" else "en"
        output_text_filename = input_text_filename.replace(".txt", f"_{target_lang}.txt")
        input_text_file = os.path.join(config.TRANSLATED_TEXT_DIR, input_text_filename)
        output_text_file = os.path.join(config.TRANSLATED_TEXT_DIR, output_text_filename)
        
        translation_pipeline(
            input_text_file=input_text_file,
            output_text_file=output_text_file,
            with_preferential_translation=with_preferential_translation,
            source_lang=source_lang,
        )
