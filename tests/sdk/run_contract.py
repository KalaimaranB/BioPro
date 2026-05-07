from tests.sdk.test_plugin_contract import TestPluginContract

test = TestPluginContract()
try:
    print("Running test_module_manager_validation_pass...")
    test.test_module_manager_validation_pass()
except Exception:
    import traceback

    traceback.print_exc()
