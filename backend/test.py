import unittest
from tests.appointments_db_test import TestAppointmentsDb

if __name__ == "__main__":
    print("Starting test suite: TestAppointmentsDb...\n")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAppointmentsDb)
    runner = unittest.TextTestRunner(verbosity=2)  # verbosity=2 shows detailed output
    result = runner.run(suite)
    
    print("\nTest run finished.")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ All tests passed.")
    else:
        print("❌ Some tests failed.")
