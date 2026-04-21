"""Tests for biopro.core.project_manager functionality."""

import os
import json
import pytest
from pathlib import Path
from biopro.core.project_manager import ProjectManager, ProjectLockedError

@pytest.fixture
def empty_project_dir(tmp_path):
    """Fixture for an empty project directory."""
    return tmp_path / "test_project"

@pytest.fixture
def open_project(empty_project_dir):
    """Fixture for an initialized and open project."""
    pm = ProjectManager(empty_project_dir)
    pm.create_new("Test Project")
    return pm

class TestProjectManager:
    """Test suite for ProjectManager."""

    def test_create_new_project(self, empty_project_dir):
        """Verifies that a new project creates the expected folder structure and files."""
        pm = ProjectManager(empty_project_dir)
        pm.create_new("My Project")
        
        assert empty_project_dir.exists()
        assert (empty_project_dir / "project.biopro").exists()
        assert (empty_project_dir / "assets").exists()
        assert (empty_project_dir / ".biopro.lock").exists()
        assert pm.data["project_name"] == "My Project"

    def test_open_project_locks(self, empty_project_dir):
        """Verifies that opening an existing project correctly acquires a lock."""
        # Setup: Create and close a project
        pm1 = ProjectManager(empty_project_dir)
        pm1.create_new("New Project")
        pm1.close() # Release lock
        
        # Re-open in instance 1
        pm1.open_project()
        
        # Instance 2 should fail to open
        pm2 = ProjectManager(empty_project_dir)
        with pytest.raises(ProjectLockedError):
            pm2.open_project()

    def test_asset_addition_single(self, open_project, tmp_path):
        """Tests adding a single image to the project assets."""
        pm = open_project
        img_path = tmp_path / "test_image.png"
        img_path.write_text("fake binary content")
        
        file_hash = pm.add_image(img_path, copy_to_workspace=True)
        
        assert file_hash in pm.data["assets"]
        asset = pm.data["assets"][file_hash]
        assert asset["filename"] == "test_image.png"
        assert asset["copied_to_workspace"] is True
        
        local_path = pm.project_dir / asset["local_path"]
        assert local_path.exists()

    def test_batch_add_images_with_subfolder(self, open_project, tmp_path):
        """Tests the new batch loading feature with subdirectory support."""
        pm = open_project
        
        # Create 3 dummy files
        files = []
        for i in range(3):
            p = tmp_path / f"experiment_{i}.tiff"
            p.write_text(f"data_{i}")
            files.append(p)
            
        hashes = pm.batch_add_images(files, copy_to_workspace=True, subfolder="cohort_a")
        
        assert len(hashes) == 3
        # Check that the subdirectory was created
        assert (pm.assets_dir / "cohort_a").exists()
        
        for h in hashes:
            asset = pm.data["assets"][h]
            # Verify paths are relative and correct
            assert "assets/cohort_a" in asset["local_path"]
            assert (pm.project_dir / asset["local_path"]).exists()

    def test_validate_assets_pruning(self, open_project, tmp_path):
        """Tests that records for manually deleted files are correctly pruned."""
        pm = open_project
        
        # Add a file
        p = tmp_path / "to_delete.png"
        p.write_text("temp")
        h = pm.add_image(p, copy_to_workspace=True)
        
        asset = pm.data["assets"][h]
        local_file = pm.project_dir / asset["local_path"]
        assert local_file.exists()
        
        # 1. Manual deletion (delete BOTH original and local to trigger pruning)
        local_file.unlink()
        p.unlink()
        assert not local_file.exists()
        assert not p.exists()
        
        # 2. Record still exists before validation
        assert h in pm.data["assets"]
        
        # 3. RUN VALIDATION
        pm.validate_assets()
        
        # 4. Record should be gone
        assert h not in pm.data["assets"]

    def test_save_workflow_persistence(self, open_project):
        """Verifies that workflows can be saved and listed."""
        pm = open_project
        payload = {"data": [1, 2, 3]}
        metadata = {"name": "Test Workflow", "timestamp": "2026-04-19"}
        
        filename = pm.save_workflow("test_module", payload, metadata)
        assert filename.endswith(".json")
        
        # Try to list it
        workflows = pm.list_workflows()
        assert len(workflows) > 0
        assert workflows[0]["name"] == "Test Workflow"
        assert workflows[0]["module"] == "test_module"

    def test_open_corrupted_json_handles_gracefully(self, empty_project_dir):
        """Verifies that the manager doesn't crash on corrupted project files."""
        # Setup with a fixed name for predictable assertion
        proj_dir = empty_project_dir
        proj_dir.mkdir()
        with open(proj_dir / "project.biopro", "w") as f:
            f.write("{ \"project_name\": \"Broken\", corrupted... }")
            
        pm = ProjectManager(proj_dir)
        pm.open_project()
        
        # Verify it didn't crash and returns the name through the property
        assert pm.project_name == proj_dir.name

    def test_save_to_readonly_failure_caught(self, open_project):
        """Verifies behavior when the filesystem prevents saving (PermissionError)."""
        pm = open_project
        from unittest.mock import patch
        
        # Mock built-in open to raise PermissionError specifically for the project file
        original_open = open
        def side_effect(file, *args, **kwargs):
            if "project.biopro" in str(file):
                raise PermissionError("Access Denied")
            return original_open(file, *args, **kwargs)

        with patch("biopro.core.project_manager.open", side_effect=side_effect):
            # This should log a warning but NOT raise an exception that crashes the UI
            pm.save()
            # Success reach here means no crash

