import pandas as pd


def load_data(source, is_pickle=False):
    if is_pickle:
        df = pd.read_pickle(source)
        return [tuple(row) for row in df.values]
    else:
        with open(source, encoding='utf-8') as f:
            return list(f)


def check_match_quality(source1, source2, is_pickle=False, only_print_if_unmatched=True):
    print(f'\n===== {source1.split("/")[-1]} =====')
    
    data1 = load_data(source1, is_pickle)
    data2 = load_data(source2, is_pickle)
    
    print_counts = not only_print_if_unmatched
    
    if data1 == data2:
        print("Lists match")
    elif sorted(data1) == sorted(data2):
        print("Sorted lists match")
    elif set(data1) == set(data2):
        print("Sets match")
        print_counts = True
    else:
        print("DO NOT MATCH")
        print_counts = True
    
    if print_counts:
        count_matches(data1, data2)


def count_matches(data1, data2):
    print(f"Total rows in file1: {len(data1)}")
    print(f"Total rows in file2: {len(data2)}")
    
    data2_set = set(data2)
    matches = sum(1 for item in data1 if item in data2_set)
    no_match = len(data1) - matches
    
    print(f"Rows from file1 found in file2: {matches}")
    print(f"Rows from file1 NOT in file2: {no_match}")


if __name__ == '__main__':
    old_file = "../../Data/matched_data_wo_linebreaks.pickle"
    new_file = "../../Data/pipe_recalc2/pipeline_matched_data_wo_linebreaks.pickle"
    check_match_quality(old_file, new_file, is_pickle=True)
    
    old_file = "../../Data/df_with_features.pickle"
    new_file = "../../Data/pipe_recalc2/pipeline_df_with_features.pickle"
    check_match_quality(old_file, new_file, is_pickle=True)
    
    old_file = "../../Data/df_with_features.pickle"
    new_file = "../../Data/pipe_recalc2/pipeline_df_with_features.pickle"
    check_match_quality(old_file, new_file, is_pickle=True)
    
    old_file = "../../Data/df_with_more_features.pickle"
    new_file = "../../Data/pipe_recalc2/pipeline_df_with_more_features.pickle"
    check_match_quality(old_file, new_file, is_pickle=True)
    
    old_file = "../../Data/training_data.jsonl"
    new_file = "../../Data/pipe_recalc2/pipeline_training_data.jsonl"
    check_match_quality(old_file, new_file)
