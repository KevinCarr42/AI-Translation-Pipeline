from data_cleaning import data_cleaning_pipeline
from model_finetuning import finetuning_pipeline
from translate import translation_pipeline


if __name__ == "__main__":
    clean_data = True
    finetune_models = False
    translate_data = False
    with_preferential_translation = True
    
    if clean_data:
        data_cleaning_pipeline()
    
    if finetune_models:
        finetuning_pipeline()
    
    if translate_data:
        translation_pipeline(with_preferential_translation=with_preferential_translation)
