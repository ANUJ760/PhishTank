"""Pytest configuration ensuring test database isolation."""
import os

# Isolate test database so test resets never wipe live development/user database
os.environ["DATABASE_URL"] = "sqlite:///data/test_gecompose.db"
