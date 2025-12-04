old_file = "../../Data/training_data.jsonl"
new_file = "../../Data/pipeline_training_data.jsonl"


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
        lines2 = set(f2)
        
        matches = sum(1 for line in lines1 if line in lines2)
        no_match = len(lines1) - matches
        
        print(f"Total rows in file1: {len(lines1)}")
        print(f"Rows from file1 found in file2: {matches}")
        print(f"Rows from file1 NOT in file2: {no_match}")


if __name__ == '__main__':
    check_match_quality(old_file, new_file)
    count_matches(old_file, new_file)
    
    # TODO: DO NOT MATCH
    #     Total rows in file1: 527420
    #     Rows from file1 found in file2:   284428
    #     Rows from file1 NOT in file2:     242992
    