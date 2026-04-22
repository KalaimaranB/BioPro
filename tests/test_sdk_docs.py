import pytest
from biopro.sdk.core.docs import PluginDocumentation

def test_plugin_documentation_registration():
    docs = PluginDocumentation()
    docs.register_page("flow_cytometry", "index", "/path/to/docs/index.md")
    
    page = docs.get_page("flow_cytometry", "index")
    assert page == "/path/to/docs/index.md"

def test_plugin_documentation_missing_page():
    docs = PluginDocumentation()
    page = docs.get_page("flow_cytometry", "missing")
    assert page is None
