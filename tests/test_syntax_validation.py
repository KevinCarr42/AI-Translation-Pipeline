import sys
import os
import py_compile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_file_syntax(filepath):
    """Test that a Python file has valid syntax"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"    Syntax error: {e}")
        return False


def test_all_python_files():
    """Validate syntax of all Python files in Pipeline"""
    print("\nValidating Python syntax...")

    pipeline_dir = os.path.dirname(os.path.dirname(__file__))

    files_to_check = [
        "config.py",
        "main.py",
        "data_cleaning/__init__.py",
        "data_cleaning/pipeline.py",
        "model_finetuning/__init__.py",
        "model_finetuning/pipeline.py",
        "model_finetuning/model_loading.py",
        "model_finetuning/preprocessing.py",
        "model_finetuning/trainer.py",
        "translate/__init__.py",
        "translate/models.py",
        "translate/document.py",
        "translate/pipeline.py",
    ]

    passed = 0
    failed = 0

    for file_rel in files_to_check:
        filepath = os.path.join(pipeline_dir, file_rel)
        if os.path.exists(filepath):
            if test_file_syntax(filepath):
                print(f"  [OK] {file_rel}")
                passed += 1
            else:
                print(f"  [FAIL] {file_rel}")
                failed += 1
        else:
            print(f"  [MISS] {file_rel} (not found)")
            failed += 1

    return passed, failed


def test_directory_structure():
    """Validate directory structure"""
    print("\nValidating directory structure...")

    pipeline_dir = os.path.dirname(os.path.dirname(__file__))

    required_dirs = [
        "data_cleaning",
        "model_finetuning",
        "translate",
        "tests",
        "documentation",
    ]

    passed = 0
    failed = 0

    for dir_name in required_dirs:
        dir_path = os.path.join(pipeline_dir, dir_name)
        if os.path.isdir(dir_path):
            print(f"  [OK] {dir_name}/ exists")
            passed += 1
        else:
            print(f"  [FAIL] {dir_name}/ missing")
            failed += 1

    return passed, failed


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SYNTAX VALIDATION TESTS")
    print("=" * 60)

    dir_pass, dir_fail = test_directory_structure()
    syntax_pass, syntax_fail = test_all_python_files()

    total_pass = dir_pass + syntax_pass
    total_fail = dir_fail + syntax_fail

    print("\n" + "=" * 60)
    print("SYNTAX VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Directory structure: {dir_pass}/{dir_pass + dir_fail} passed")
    print(f"Python syntax:       {syntax_pass}/{syntax_pass + syntax_fail} passed")
    print(f"\nTotal: {total_pass}/{total_pass + total_fail} checks passed")
    print("=" * 60 + "\n")

    if total_fail == 0:
        print("ALL SYNTAX VALIDATION TESTS PASSED [OK]\n")
        sys.exit(0)
    else:
        print(f"SOME CHECKS FAILED [FAIL] ({total_fail} issues)\n")
        sys.exit(1)
