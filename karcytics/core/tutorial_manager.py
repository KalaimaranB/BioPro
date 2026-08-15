"""Thin Hub instantiation of the Karcytics Academy engine.

The real state machine (`AcademyManager`) now lives in the SDK
(`karcytics_sdk.plugin.academy`) so both the Hub and isolated plugins run
the exact same class — see that module's docstring for why the event bus
and persistence directory became constructor arguments instead of direct
Hub-only imports. This file only supplies the Hub-specific pieces: a real
`AcademyManager` instance wired to the Hub's own `event_bus`/`AppConfig`,
a small adapter translating between the SDK's plain string topic names and
the Hub's `KarcyticsEvent` enum (every `ACADEMY_*` string here is exactly
that enum member's name, so `KarcyticsEvent[topic]` always resolves), and
`start_core_intro()`, which is Hub-only content the SDK class has no
business knowing about.
"""

import contextlib
import logging
from typing import Any

from karcytics_sdk.plugin.academy import AcademyEventBus, AcademyManager

from karcytics.core.config import AppConfig
from karcytics.core.event_bus import KarcyticsEvent, event_bus

logger = logging.getLogger(__name__)

# Re-exported so existing `from karcytics.core.tutorial_manager import
# AcademyManager` call sites (if any) keep resolving to the same class the
# module-level singleton below is built from.
__all__ = ["AcademyManager", "global_tutorial_manager"]


class _HubAcademyEventBus(AcademyEventBus):
    """Bridges the SDK's plain-string topics to the Hub's real, enum-keyed `event_bus`.

    Every topic that ever reaches this adapter is either one of
    `academy.py`'s own `ACADEMY_*` constants or a `WaitForEventStep.event_name`
    — both are always valid `KarcyticsEvent` member names.
    """

    def subscribe(self, topic: str, callback: Any) -> None:
        try:
            event_bus.subscribe(KarcyticsEvent[topic], callback)
        except KeyError:
            logger.error(f"Academy event bus: unknown topic {topic!r}")

    def unsubscribe(self, topic: str, callback: Any) -> None:
        with contextlib.suppress(KeyError):
            event_bus.unsubscribe(KarcyticsEvent[topic], callback)

    def emit(self, topic: str, *args: Any) -> None:
        try:
            event_bus.emit(KarcyticsEvent[topic], *args)
        except KeyError:
            logger.error(f"Academy event bus: unknown topic {topic!r}")


class HubAcademyManager(AcademyManager):
    """The Hub's own `AcademyManager`, plus `start_core_intro()`.

    That method is Hub-only content, so it has no place in the SDK's
    process-agnostic class.
    """

    def start_core_intro(self) -> bool:
        """Starts the core onboarding tour directly (no ACADEMY_COURSE_PREPARE_PROJECT event).

        Safe to call before any module is loaded.  Registers the course on
        the ``"core"`` sentinel module ID if it hasn't been registered yet.
        Returns True on success.
        """
        from karcytics.tutorials.core_intro import core_intro_course

        if "core" not in self.courses_by_module:
            self.register_storyboard("core", core_intro_course)

        return self.start_course_confirmed("core_intro_v1")


# Shared by every Hub-side `TutorialOverlay(academy_manager, event_bus)`
# construction call site (see workspace_window.py, plugin_store.py,
# project_launcher.py) — one adapter instance per process, matching
# `global_tutorial_manager` itself being a singleton.
hub_academy_event_bus = _HubAcademyEventBus()

global_tutorial_manager = HubAcademyManager(
    event_bus=hub_academy_event_bus, persistence_dir=AppConfig.APP_DATA_DIR / "academy"
)
