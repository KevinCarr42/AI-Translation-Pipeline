import pandas as pd


def check_match_quality(file1, file2):
    with open(file1, encoding='utf-8') as f1, open(file2, encoding='utf-8') as f2:
        lines1 = list(f1)
        lines2 = list(f2)
        
        if lines1 == lines2:
            print("Lists match")
        elif sorted(lines1) == sorted(lines2):
            print("Sorted lists match")
        elif set(lines1) == set(lines2):
            print("Sets match")
        else:
            print("DO NOT MATCH")


def count_matches(file1, file2):
    with open(file1, encoding='utf-8') as f1, open(file2, encoding='utf-8') as f2:
        lines1 = list(f1)
        lines2 = list(f2)
        print(f"Total rows in file1: {len(lines1)}")
        print(f"Total rows in file2: {len(lines2)}")
        
        lines2 = set(lines2)
        matches = sum(1 for line in lines1 if line in lines2)
        no_match = len(lines1) - matches
        
        print(f"Rows from file1 found in file2: {matches}")
        print(f"Rows from file1 NOT in file2: {no_match}")


def check_match_quality_pickle(df1, df2):
    data1 = [tuple(row) for row in df1.values]
    data2 = [tuple(row) for row in df2.values]
    
    if data1 == data2:
        print("Lists match")
    elif sorted(data1) == sorted(data2):
        print("Sorted lists match")
    elif set(data1) == set(data2):
        print("Sets match")
    else:
        print("DO NOT MATCH")


def count_matches_pickle(df1, df2):
    data1 = [tuple(row) for row in df1.values]
    data2 = [tuple(row) for row in df2.values]
    
    print(f"Total rows in file1: {len(data1)}")
    print(f"Total rows in file2: {len(data2)}")
    
    data2_set = set(data2)
    matches = sum(1 for item in data1 if item in data2_set)
    no_match = len(data1) - matches
    
    print(f"Rows from file1 found in file2: {matches}")
    print(f"Rows from file1 NOT in file2: {no_match}")


if __name__ == '__main__':
    # # Sorted lists match
    # # Total rows in file1: 887164
    # # Total rows in file2: 887164
    # # Rows from file1 found in file2: 887164
    # # Rows from file1 NOT in file2: 0
    # old_file = "../../Data/matched_data.pickle"
    # new_file = "../../Data/pipe_recalc/pipeline_matched_data.pickle"
    
    # # DO NOT MATCH
    # # Total rows in file1: 778951
    # # Total rows in file2: 887164
    # # Rows from file1 found in file2: 137090
    # # Rows from file1 NOT in file2: 641861
    # old_file = "../../Data/df_with_features.pickle"
    # new_file = "../../Data/pipe_recalc/pipeline_df_with_features.pickle"
    # old_df = pd.read_pickle(old_file)
    # new_df = pd.read_pickle(new_file)
    # check_match_quality_pickle(old_df, new_df)
    # count_matches_pickle(old_df, new_df)
    # # FIXME: this was saved after with more features (1:07)
    
    old_file = "../../Data/df_with_features.pickle"
    new_file = "../../Data/pipe_recalc2/pipeline_df_with_features.pickle"
    old_df = pd.read_pickle(old_file)
    new_df = pd.read_pickle(new_file)
    check_match_quality_pickle(old_df, new_df)
    count_matches_pickle(old_df, new_df)
    
    # # DO NOT MATCH
    # # Total rows in file1: 778951
    # # Total rows in file2: 887164
    # # Rows from file1 found in file2: 135187
    # # Rows from file1 NOT in file2: 643764
    # old_file = "../../Data/df_with_more_features.pickle"
    # new_file = "../../Data/pipe_recalc/pipeline_df_with_more_features.pickle"
    # old_df = pd.read_pickle(old_file)
    # new_df = pd.read_pickle(new_file)
    # check_match_quality_pickle(old_df, new_df)
    # count_matches_pickle(old_df, new_df)
    # # FIXME: this was saved before with features (1:02)
    
    # # DO NOT MATCH
    # # Total rows in file1: 527420
    # # Total rows in file2: 618484
    # # Rows from file1 found in file2: 102280
    # # Rows from file1 NOT in file2: 425140
    # old_file = "../../Data/training_data.jsonl"
    # new_file = "../../Data/pipe_recalc/pipeline_training_data.jsonl"
    # check_match_quality(old_file, new_file)
    # count_matches(old_file, new_file)
