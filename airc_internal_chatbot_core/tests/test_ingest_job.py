"""Smoke tests for ingest job wiring (no Docling/Qdrant)."""
from pathlib import Path


def test_ingest_job_entrypoint_exists():
    source = (Path(__file__).resolve().parents[1] / "app" / "jobs" / "ingest.py").read_text(encoding="utf-8")
    assert "def process_dataset_file_job" in source
    assert "ProcessingService" in source
    assert "process_dataset_file" in source
