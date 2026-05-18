import logging

from biopro_sdk.host.trust_manager import TrustManager

from biopro.core.module_manager import ModuleManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

print("🔍 Loading ModuleManager to discover and verify plugins...")
trust_manager = TrustManager()
manager = ModuleManager(trust_manager=trust_manager)

print("\n--- DISCOVERED MODULES ---")
for mod_id, mod_info in manager.modules.items():
    print(f"Plugin ID:   {mod_id}")
    print(f"Path:        {mod_info['path']}")
    print(f"Trust Level: {mod_info['trust_level']}")
    print(f"Trust Error: {mod_info['trust_error']}")
    print(f"Developer:   {mod_info['manifest'].get('developer_name')}")
    print(f"Key:         {mod_info['manifest'].get('developer_key')}")
    print("-" * 40)
