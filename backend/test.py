# import unittest
# from tests.appointments_db_test import TestAppointmentsDb

# if __name__ == "__main__":
#     print("Starting test suite: TestAppointmentsDb...\n")
#     suite = unittest.TestLoader().loadTestsFromTestCase(TestAppointmentsDb)
#     runner = unittest.TextTestRunner(verbosity=2)  # verbosity=2 shows detailed output
#     result = runner.run(suite)
    
#     print("\nTest run finished.")
#     print(f"Tests run: {result.testsRun}")
#     print(f"Failures: {len(result.failures)}")
#     print(f"Errors: {len(result.errors)}")

#     if result.wasSuccessful():
#         print("✅ All tests passed.")
#     else:
#         print("❌ Some tests failed.")


#!/usr/bin/env python3
import sys
import os
import pytest

# Add the project root to Python path so imports work
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_config_mgr_tests():
    """Run the ConfigYamlManager tests"""
    test_file = os.path.join(project_root, "tests", "config_mgr_tests.py")
    
    # Run pytest with various options
    args = [
        test_file,
        "-v",                    # Verbose output
        "--tb=short",           # Short traceback format
        "--color=yes",          # Colored output
        "--durations=10",       # Show 10 slowest tests
        # "--cov=common",       # Coverage (if you have pytest-cov installed)
        # "--cov-report=html",  # HTML coverage report
    ]
    
    print(f"Running tests from: {test_file}")
    exit_code = pytest.main(args)
    return exit_code

def run_all_tests():
    """Run all tests in tests directory"""
    test_dir = os.path.join(project_root, "tests")
    
    args = [
        test_dir,
        "-v",
        "--tb=short",
        "--color=yes",
    ]
    
    print(f"Running all tests from: {test_dir}")
    exit_code = pytest.main(args)
    return exit_code

def run_specific_test():
    """Run a specific test method"""
    test_file = os.path.join(project_root, "tests", "config_mgr_tests.py")
    
    args = [
        f"{test_file}::TestConfigYamlManager::test_config_file_change_detection",
        "-v",
        "-s",  # Don't capture output (useful for debugging)
    ]
    
    print("Running specific test...")
    exit_code = pytest.main(args)
    return exit_code

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run pytest for the project")
    parser.add_argument("--config-mgr", action="store_true", help="Run ConfigYamlManager tests")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--specific", action="store_true", help="Run specific test")
    
    args = parser.parse_args()
    
    if args.config_mgr:
        exit_code = run_config_mgr_tests()
    elif args.all:
        exit_code = run_all_tests()
    elif args.specific:
        exit_code = run_specific_test()
    else:
        # Default: run config manager tests
        exit_code = run_config_mgr_tests()
    
    sys.exit(exit_code)