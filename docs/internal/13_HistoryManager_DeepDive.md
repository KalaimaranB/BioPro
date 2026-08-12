# HistoryManager Deep Dive

This page expands on `HistoryManager` and `ModuleHistory` semantics described in the API pages, explaining structural sharing, heavy resource handling, and common usage patterns.

## Goals

- Provide predictable undo/redo semantics across modules
- Avoid duplicating large binary data (images, arrays)
- Ensure project serialization is compact and safe

## Structural sharing strategy

- History snapshots copy light-weight configuration fields (numbers, strings) via `deepcopy`.
- Heavy resources are detected with `ResourceInspector.is_heavy()` and stored by reference to avoid memory bloat.

## Snapshot equality

- `ModuleHistory._is_equal()` performs a shallow comparison using identity for heavy objects and value equality for light fields. Consecutive identical snapshots are ignored.

## Memory caps and persistence

- Each `ModuleHistory` has a `max_steps` cap; older snapshots are dropped when exceeded.
- `HistoryManager.serialize_all()` packages history per-module for project persistence; heavy resources are not serialized directly and should be stored in project assets.

## Usage patterns

- Call `push_state()` from UI actions that change analysis parameters.
- On `undo()`, UI components should `set_state()` with the returned snapshot and refresh any derived views.

## Links

- Source: `biopro/core/history_manager.py`
