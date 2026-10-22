"""Compatibility test entry point; implementations live in tests/test_solver.py.

No computations or artifact writes occur on import. Run the entire foundation
suite with: python -m unittest discover -s tests -v
"""
import unittest


def main():
    from pathlib import Path
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).with_name('tests')),pattern='test_solver.py')
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
