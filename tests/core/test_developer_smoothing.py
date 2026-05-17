"""Verification tests for Phase 5.5: Developer Path Smoothing."""

import json

from biopro_sdk.host.trust_manager import TrustManager
from biopro_sdk.plugin.managed_task import FunctionalTask

from biopro.core.task_scheduler import task_scheduler

from .test_trust_architecture import PluginSigner


def test_functional_task_execution(qtbot):
    """Verify that FunctionalTask can run arbitrary callables on the scheduler."""
    scheduler = task_scheduler

    def my_func():
        return {"foo": "bar"}

    task = FunctionalTask(my_func, "test_plugin", name="My Test Task")

    # We can run it directly to verify logic
    result = task.run(None)
    assert result == {"foo": "bar"}

    # Submit to scheduler — just verify the scheduler accepted the task
    # (Don't check _active_workers immediately: thread pool may complete before the assertion)
    task_id = scheduler.submit(task, None)
    assert task_id is not None


def test_integrity_exclusions(tmp_path):
    """Verify that ignored and excluded directories don't break trust."""
    plugin_dir = tmp_path / "excluded_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text(
        json.dumps({"id": "excluded_plugin", "integrity": {"exclusions": ["custom_output/"]}})
    )
    (plugin_dir / "__init__.py").write_text("pass")

    # Sign it
    signer = PluginSigner()
    signer.sign_plugin(plugin_dir, signer.generate_developer_cert("dev_01"))

    manager = TrustManager(root_public_key=signer.root_public)

    # 1. Initial verify (should pass)
    assert manager.verify_plugin(plugin_dir).success is True

    # 2. Add file to DEFAULT IGNORE (results/)
    results_dir = plugin_dir / "results"
    results_dir.mkdir()
    (results_dir / "data.fcs").write_text("fake data")

    # Should still pass
    assert manager.verify_plugin(plugin_dir).success is True

    # 3. Add file to CUSTOM EXCLUSION (custom_output/)
    custom_dir = plugin_dir / "custom_output"
    custom_dir.mkdir()
    (custom_dir / "stats.json").write_text("{}")

    # Should still pass
    assert manager.verify_plugin(plugin_dir).success is True

    # 4. Add UNAUTHORIZED file in root (should fail)
    (plugin_dir / "malware.py").write_text("evil")
    assert manager.verify_plugin(plugin_dir).success is False
