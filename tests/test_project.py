"""Tests for src/project.py — sanitization, traversal protection, and metadata I/O."""

import json
import os

import pytest

from project import ArduinoProject, ProjectMetadata, _safe_project_name


class TestSafeProjectName:
    def test_normalizes_spaces_and_dashes(self):
        assert _safe_project_name("My Cool-Project") == "my_cool_project"

    def test_strips_path_separators(self):
        assert _safe_project_name("../etc/passwd") == "etcpasswd"

    def test_rejects_dotdot(self):
        with pytest.raises(ValueError):
            _safe_project_name("..")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            _safe_project_name("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError):
            _safe_project_name("   ")

    def test_rejects_only_punctuation(self):
        with pytest.raises(ValueError):
            _safe_project_name("///")


class TestArduinoProject:
    def test_create_and_load(self, tmp_path):
        mgr = ArduinoProject(project_dir=str(tmp_path))
        result = mgr.create("Blinky", board="arduino:avr:uno")
        assert result["status"] == "created"
        assert os.path.isdir(result["project_dir"])
        assert os.path.isfile(result["sketch_path"])

        loaded = mgr.load("Blinky")
        assert loaded["status"] == "loaded"
        assert loaded["metadata"]["name"] == "Blinky"

    def test_traversal_create_stays_under_project_dir(self, tmp_path):
        mgr = ArduinoProject(project_dir=str(tmp_path))
        result = mgr.create("../escape")
        # Should not have escaped; created under tmp_path or returned error.
        if result["status"] == "created":
            assert str(tmp_path) in result["project_dir"]
        else:
            assert result["status"] == "error"

    def test_empty_name_rejected(self, tmp_path):
        mgr = ArduinoProject(project_dir=str(tmp_path))
        assert mgr.create("")["status"] == "error"
        assert mgr.save("")["status"] == "error"
        assert mgr.backup("")["status"] == "error"
        assert mgr.load("")["status"] == "error"
        assert mgr.delete("")["status"] == "error"


class TestMetadataLegacyMigration:
    def test_legacy_bt_rfcord_channel_migrates(self):
        legacy = {
            "name": "old",
            "bt_rfcord_channel": 3,
        }
        meta = ProjectMetadata.from_dict(legacy)
        assert meta.bt_rfcomm_channel == 3

    def test_unknown_keys_dropped(self):
        legacy = {"name": "old", "some_removed_field": "x"}
        # Should not raise even though the legacy key isn't on the dataclass.
        meta = ProjectMetadata.from_dict(legacy)
        assert meta.name == "old"
