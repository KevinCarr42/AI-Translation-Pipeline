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
        correlation_csv_path = os.path.join(config.DATA_DIR, "fr_eng_correlation_data.csv")
        parsed_docs_folder = os.path.join(config.DATA_DIR, "ParsedPublications")
        
        data_cleaning_pipeline(
            correlation_csv_path=correlation_csv_path,
            parsed_docs_folder=parsed_docs_folder,
            linebreaks=True,
            add_features=True
        )
    
    if finetune_models:
        with_preferential_translation = True
        finetuning_pipeline()
    
    if translate_data:
        translation_pipeline(with_preferential_translation=with_preferential_translation)
