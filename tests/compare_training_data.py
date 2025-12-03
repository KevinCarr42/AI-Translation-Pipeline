old_file = "../../Data/training_data.jsonl"
new_file = "../../Data/pipeline_training_data.jsonl"

if __name__ == '__main__':
    with open(old_file, encoding='utf-8') as f1, open(new_file, encoding='utf-8') as f2:
        if list(f1) == list(f2):
            print("Lists match")
        elif set(f1) == set(f2):
            print("Sets match")
        else:
            print("DO NOT MATCH")
        