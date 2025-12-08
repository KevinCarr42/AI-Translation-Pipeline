from create_training_data.data_cleaning import create_matched_data
from create_training_data.add_features import add_features
from create_training_data.create_training_data import create_training_data, create_testing_data, save_jsonl


# FULL DATA-CLEANING PIPELINE
def create_training_data_pipeline(training_data_path, testing_data_path):
    print('creating training data')
    df_matched = create_matched_data()
    df_features = add_features(df_matched)
    df_clean = create_training_data(df_features)
    save_jsonl(df_clean, training_data_path)
    df_clean_relaxed = create_testing_data(df_features)
    save_jsonl(df_clean_relaxed, testing_data_path)
