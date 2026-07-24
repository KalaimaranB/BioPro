"""Verification tests for Phase 5.5: Developer Path Smoothing."""


def _dict_to_toml(d):
    # Convert flat dict to pyproject.toml format
    lines = []

    lines.append("[project]")
    lines.append(f'name = "{d.get("name", "test")}"')
    lines.append(f'version = "{d.get("version", "1.0.0")}"')
    if "description" in d:
        lines.append(f'description = "{d["description"]}"')

    authors = d.get("authors", [])
    if authors:
        lines.append("authors = [")
        for a in authors:
            lines.append(f'  {{ name = "{a.get("name", "Test")}" }},')
        lines.append("]")

    lines.append("")
    lines.append("[tool.biopro.plugin]")
    lines.append(f'id = "{d.get("id", "test_id")}"')

    if authors:
        lines.append("authors = [")
        for a in authors:
            role = a.get("role", "Developer")
            perms = a.get("permissions", [])
            perms_str = '", "'.join(perms)
            if perms_str:
                lines.append(
                    f'  {{ name = "{a.get("name", "Test")}", role = "{role}", permissions = ["{perms_str}"] }},'
                )
            else:
                lines.append(f'  {{ name = "{a.get("name", "Test")}", role = "{role}" }},')
        lines.append("]")

    if "custom_exclusions" in d:
        ce_str = '", "'.join(d["custom_exclusions"])
        lines.append(f'custom_exclusions = ["{ce_str}"]')

    return "\n".join(lines)


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
    manifest_data = {
        "manifest_version": 2,
        "id": "excluded_plugin",
        "name": "Excluded Plugin",
        "version": "1.0.0",
        "description": "Excluded Plugin desc",
        "authors": [{"name": "Developer Alice", "role": "Developer"}],
        "custom_exclusions": ["custom_output/"],
    }
    (plugin_dir / "pyproject.toml").write_text(_dict_to_toml(manifest_data), encoding="utf-8")
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
