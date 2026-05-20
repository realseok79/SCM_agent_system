# run_tests_verbose.py
import subprocess

def main():
    print("Running pytest on tests/test_data_parser.py...")
    res1 = subprocess.run(
        ["pytest", "tests/test_data_parser.py", "-vv"],
        capture_output=True,
        text=True
    )
    with open("tests_data_parser_output.txt", "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(res1.stdout)
        f.write("\n=== STDERR ===\n")
        f.write(res1.stderr)
        
    print("Running pytest on tests/test_demand_pipeline.py...")
    res2 = subprocess.run(
        ["pytest", "tests/test_demand_pipeline.py", "-vv"],
        capture_output=True,
        text=True
    )
    with open("tests_demand_pipeline_output.txt", "w", encoding="utf-8") as f:
        f.write("=== STDOUT ===\n")
        f.write(res2.stdout)
        f.write("\n=== STDERR ===\n")
        f.write(res2.stderr)
        
    print("Test runs completed. Captured logs in tests_data_parser_output.txt and tests_demand_pipeline_output.txt.")

if __name__ == "__main__":
    main()
