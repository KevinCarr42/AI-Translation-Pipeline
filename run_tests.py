import subprocess
import sys
from pathlib import Path

def run_tests():
    test_dir = Path(__file__).parent / "tests"
    test_files = sorted(test_dir.glob("test_*.py"))

    if not test_files:
        print("No test files found in tests/")
        return 1

    results = []
    failed_tests = []

    print(f"Running {len(test_files)} test files...\n")

    for test_file in test_files:
        print(f"Running {test_file.name}...", end=" ")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=True,
            text=True
        )

        passed = result.returncode == 0
        results.append((test_file.name, passed))

        if passed:
            print("✓ PASSED")
        else:
            print("✗ FAILED")
            failed_tests.append(test_file.name)

        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                print(f"  {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                print(f"  ERROR: {line}")

    print("\n" + "=" * 50)
    print(f"Results: {len(results) - len(failed_tests)}/{len(results)} passed")

    if failed_tests:
        print(f"\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(run_tests())