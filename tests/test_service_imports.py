"""Smoke tests to ensure milestone 3.x services are importable."""

import importlib
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI

# Ensure the repository root is importable when pytest runs from any location.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


SERVICE_MODULES = [
    "backend.alignment_qa.main",
    "backend.reinforcement.main",
    "backend.evaluation.main",
    "backend.feedback.main",
    "backend.monitoring.main",
    "backend.security_guardrails.main",
    "backend.license_audit.main",
]


@pytest.mark.parametrize("module_path", SERVICE_MODULES)
def test_main_app_importable(module_path: str) -> None:
    module = importlib.import_module(module_path)
    app = getattr(module, "app", None)
    assert isinstance(app, FastAPI), f"{module_path} missing FastAPI app"
