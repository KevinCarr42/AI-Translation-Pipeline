import config

from data_cleaning import create_matched_data
from add_features import add_features
from create_training_data import create_training_data, create_testing_data, save_jsonl


# FULL PIPELINE
def create_training_data_pipeline():
    df_matched = create_matched_data()
    
    df_features = add_features(df_matched)
    
    df_clean = create_training_data(df_features)
    save_jsonl(df_clean, config.TRAINING_DATA_OUTPUT)
    
    df_clean_relaxed = create_testing_data(df_features)
    save_jsonl(df_clean_relaxed, config.TESTING_DATA_OUTPUT)