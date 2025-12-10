from create_training_data.match_languages import create_matched_data
from create_training_data.clean_data import clean_data
from create_training_data.add_features import add_features
from create_training_data.create_training_data import create_training_data, create_testing_data, save_jsonl


# FULL DATA-CLEANING PIPELINE
def create_training_data_pipeline(training_data_path, testing_data_path):
    print('creating training data')
    df_matched = create_matched_data()
    df_clean, accent_mapping = clean_data(df_matched)
    df_features = add_features(df_clean, accent_mapping)
    df_training = create_training_data(df_features)
    save_jsonl(df_training, training_data_path)
    df_testing = create_testing_data(df_features)
    save_jsonl(df_testing, testing_data_path)
