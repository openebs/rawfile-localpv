import os
import sys

# `config` is parsed from the CLI and env on import: keep pytest's argv out of it
# and provide the required settings so driver modules can be imported in tests.
os.environ.setdefault("NAMESPACE", "rawfile-unit-test")
sys.argv = sys.argv[:1]
