from config import TRAINING_DATA_OUTPUT, TESTING_DATA_OUTPUT
from create_training_data.training_data_pipeline import create_training_data_pipeline

if __name__ == '__main__':
    create_training_data_pipeline(TRAINING_DATA_OUTPUT, TESTING_DATA_OUTPUT)
