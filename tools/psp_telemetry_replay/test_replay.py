"""Expose the strict replay regression checks to unittest discovery.

Run: python -m unittest -v test_replay
Requires jsonschema[format] and the replay modules, schema, and fixtures.
"""

import unittest

from run_replay_regression import ReplayRegressionTests


if __name__ == "__main__":
    unittest.main(verbosity=2)
