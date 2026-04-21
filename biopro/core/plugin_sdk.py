"""Plugin SDK — Compatibility shim for backward compatibility.

DEPRECATED: This module has been reorganized into biopro.sdk.
New plugins should import directly from biopro.sdk.

This file maintains backward compatibility by re-exporting from the new locations.
"""

# For backward compatibility, re-export everything from the new SDK location
from biopro.sdk.core import (
    PluginSignals,
    PluginState,
    AnalysisBase,
    AnalysisWorker,
    PluginBase,
    BioProPlugin
)

from biopro.sdk.ui import (
    StepIndicator,
    WizardStep,
    WizardPanel,
)

__all__ = [
    "PluginSignals",
    "PluginState",
    "AnalysisBase",
    "AnalysisWorker",
    "PluginBase",
    "StepIndicator",
    "WizardStep",
    "WizardPanel",
    "BioProPlugin"
]
