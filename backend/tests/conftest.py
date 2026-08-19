from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]


def pytest_configure():
    os.chdir(ROOT)
