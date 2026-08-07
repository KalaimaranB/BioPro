"""BioPro Core Intro — Active Hands-On Onboarding.

This module defines the ``core_intro_course`` — a Cyto-narrated tutorial that
guides the user through every core BioPro concept *by actually doing it*, not
just reading about it.

Journey:
  Hub
  ├── 1. Welcome
  ├── 2. Orientation (recent projects + primary actions)
  ├── 3. What is a Project?
  └── 4. [WaitForEvent: PROJECT_LOADED] — user creates their first project
           (spotlight Create New Project)

  Workspace Home Screen
  ├── 5. You're in! Workspace overview
  ├── 6. Header bar (Store + Academy, no spotlight yet)
  ├── 7. The Marketplace explained
  ├── 8. [WaitForEvent: STORE_OPENED] — user opens the Marketplace (spotlight Store button)
  ├── 9. Inside the Marketplace: verified badge & security, in brief
  ├── 10. [WaitForEvent: STORE_MODULE_DETAILS_OPENED] — user views Flow Cytometry details
            (spotlight its card)
  ├── 11. Module details panel explained
  ├── 12. [WaitForEvent: STORE_CLOSED] — user closes the Marketplace
  ├── 13. Module cards & recent sessions, dashboard layout
  └── 14. [WaitForEvent: MODULE_OPENED] — user opens the module (spotlight the Flow Cytometry card)

  Analysis Panel (Flow Cytometry)
  ├── 15. You're in the module! Overview
  ├── 16. Toolbar
  ├── 17. File safety: hashing & reproducibility
  ├── 18. Download the demo FCS file (auto-placed in Downloads)
  ├── 19. [WaitForEvent: FILE_IMPORTED] — user imports the demo file
  ├── 20. Workflows explained — save your work
  └── 21. [WaitForEvent: WORKFLOW_SAVED] — user saves a workflow

  Back to Home
  ├── 22. Graduation summary — see the workflow card
  └── 23. [BranchingStep] "Let's Start Science! 🔬" → complete + badge

The course is registered on ``module_id = "core"`` — a reserved sentinel.
The ``Course.id`` (``core_intro_v1``) is a stable identifier referenced by
``progress.json`` and several UI call sites — it stays ``v1`` even as the
content evolves, so a version bump here should never rename it.
"""

from typing import Any

from biopro.core.models.tutorial_models import (
    ActionStep,
    BranchingStep,
    Course,
    InfoStep,
    InteractionStep,
    WaitForEventStep,
)


def _copy_demo_file(main_panel: Any) -> None:  # noqa: ARG001
    """Copy the bundled demo FCS file to the user's Downloads directory.

    If an identical demo file already exists, no copy is performed. Existing files
    with different contents are preserved by selecting a unique destination name.
    """
    import contextlib
    import shutil
    from pathlib import Path

    from biopro.core.resource_manager import resource_path

    # Find the bundled demo file in the repository or MEIPASS
    src_file = resource_path("biopro/tutorials/assets/demo_tutorial.fcs")

    if not src_file.exists():
        return

    # Use QStandardPaths to safely resolve the OS's real Downloads folder
    from PyQt6.QtCore import QStandardPaths

    download_loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
    downloads_dir = Path(download_loc) if download_loc else Path.home() / "Downloads"

    downloads_dir.mkdir(exist_ok=True, parents=True)

    dest_file = downloads_dir / "demo_tutorial.fcs"

    with contextlib.suppress(Exception):
        if dest_file.exists():
            # Check if sizes match to avoid overwriting a user's differently sized file of the same name  # noqa: E501
            if dest_file.stat().st_size == src_file.stat().st_size:
                return  # It's already our demo file

            # If size differs, create a unique filename so we don't overwrite their work
            suffix = 1
            while True:
                new_dest = downloads_dir / f"demo_tutorial_{suffix}.fcs"
                if not new_dest.exists():
                    dest_file = new_dest
                    break
                if new_dest.stat().st_size == src_file.stat().st_size:
                    return  # Already extracted previously
                suffix += 1

        shutil.copy(src_file, dest_file)


# Demo FCS logic now handled by `_copy_demo_file` action step.

# ── Step definitions ──────────────────────────────────────────────────────────

_steps = [
    # ── PHASE 1: Hub ──────────────────────────────────────────────────────────
    InfoStep(
        id="hub_welcome",
        text=(
            "Hey, I'm Cyto 👋 — think of me as your lab buddy. Give me two minutes and I'll show you around."  # noqa: E501
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="hub_orientation",
    ),
    InfoStep(
        id="hub_orientation",
        text=(
            "This is the Hub. Your recent projects live on the left — the buttons in the center are how you start new work."  # noqa: E501
        ),
        cyto_emotion="talking",
        target_widget_names=["list_recent"],
        next_step_id="hub_what_is_project",
    ),
    InfoStep(
        id="hub_what_is_project",
        text=(
            "Everything you do in BioPro lives inside a Project — its own folder on your machine, holding your data, your workflows, and your results. Keeps things tidy, and keeps datasets from bleeding into each other."  # noqa: E501
        ),
        cyto_emotion="idle",
        next_step_id="hub_create_project_action",
    ),
    WaitForEventStep(
        id="hub_create_project_action",
        text=(
            "Let's make your first one. 👉 Click ✨ Create New Project, give it a name, and pick a folder."  # noqa: E501
        ),
        cyto_emotion="pointing",
        target_widget_names=["btn_new"],
        event_name="PROJECT_LOADED",
        allow_interaction=True,
        next_step_id="ws_landed",
    ),
    # ── PHASE 2: Workspace Home Screen ────────────────────────────────────────
    InfoStep(
        id="ws_landed",
        text=(
            "🎉 Nice — that's your project. This is the Workspace, its command center for everything you do here."  # noqa: E501
        ),
        cyto_emotion="surprised",
        next_step_id="ws_header_bar",
    ),
    InfoStep(
        id="ws_header_bar",
        text=(
            "Up top: ☁️ Store, where you install new modules, and 🎓 Academy — actually where I live, along with more tutorials and badges for later. Let's go check out the Store."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_intro",
    ),
    InfoStep(
        id="ws_store_intro",
        text=(
            "BioPro only ships with the core app — you install the tools you actually need. Modules update on their own schedule, so you're never stuck waiting on a big release for one fix."  # noqa: E501
        ),
        cyto_emotion="happy",
        next_step_id="ws_store_open_action",
    ),
    WaitForEventStep(
        id="ws_store_open_action",
        text=("Click ☁️ Store, top-right, to open the Marketplace."),
        cyto_emotion="pointing",
        target_widget_names=["btn_store"],
        event_name="STORE_OPENED",
        allow_interaction=True,
        next_step_id="ws_store_catalog_explain",
    ),
    InfoStep(
        id="ws_store_catalog_explain",
        text=(
            "Every module here is signed and checked against our Root CA before it's allowed to show a 🛡️ VERIFIED badge — that's your guarantee it hasn't been tampered with. Updates get the same check, automatically."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_flow_details_action",
    ),
    WaitForEventStep(
        id="ws_store_flow_details_action",
        text=("Find the Flow Cytometry card and click 'Details' — let's see what it can do."),
        cyto_emotion="pointing",
        target_widget_names=["store_card_flow_cytometry"],
        event_name="STORE_MODULE_DETAILS_OPENED",
        allow_interaction=True,
        next_step_id="ws_store_details_explain",
    ),
    InfoStep(
        id="ws_store_details_explain",
        text=("This panel is the module's full story: what it does, and who built it."),
        cyto_emotion="talking",
        target_widget_names=["ModuleDetailsPanel"],
        next_step_id="ws_store_install_action",
    ),
    WaitForEventStep(
        id="ws_store_install_action",
        text=(
            "Grab the latest version if you haven't already, then close the Marketplace to head back."  # noqa: E501
        ),
        cyto_emotion="talking",
        target_widget_names=["store_card_flow_cytometry"],
        event_name="STORE_CLOSED",
        allow_interaction=True,
        next_step_id="ws_layout_top",
    ),
    InfoStep(
        id="ws_layout_top",
        text=(
            "Your module cards live up top — each one's a door into its own analysis environment."
        ),
        cyto_emotion="talking",
        target_widget_names=["moduleCard"],
        next_step_id="ws_layout_bottom",
    ),
    InfoStep(
        id="ws_layout_bottom",
        text=(
            "Down here: Recent Sessions — empty for now, but once you save a workflow it'll show up right here, one click from where you left off."  # noqa: E501
        ),
        cyto_emotion="talking",
        target_widget_names=["workflows_container"],
        next_step_id="ws_module_card_explain",
    ),
    InfoStep(
        id="ws_module_card_explain",
        text=(
            "Flow Cytometry just landed on your dashboard — that's what installing it a moment ago got you."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="ws_open_module_action",
    ),
    WaitForEventStep(
        id="ws_open_module_action",
        text=("Click the Flow Cytometry card to open it up."),
        cyto_emotion="pointing",
        target_widget_names=["module_card_flow_cytometry"],
        event_name="MODULE_OPENED",
        allow_interaction=True,
        next_step_id="analysis_landed",
    ),
    # ── PHASE 3: Analysis Panel ───────────────────────────────────────────────
    InfoStep(
        id="analysis_landed",
        text=(
            "🧬 Welcome to Flow Cytometry! Every module gets a workspace built just for what it does."  # noqa: E501
        ),
        cyto_emotion="surprised",
        next_step_id="analysis_toolbar",
    ),
    InfoStep(
        id="analysis_toolbar",
        text=(
            "Up top: ← Home takes you back to the dashboard any time, or close this project outright."  # noqa: E501
        ),
        cyto_emotion="talking",
        target_widget_names=["analysisToolBar"],
        next_step_id="analysis_data_integrity",
    ),
    InfoStep(
        id="analysis_data_integrity",
        text=(
            "One thing before you import anything: BioPro never touches your raw files. On import, it hashes the file (SHA-256) and copies it into this project's `assets/` folder — your original stays exactly where it was, and anyone who opens this project later gets a hash check for free, so silent corruption doesn't slip through."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="analysis_import_auto_download",
    ),
    ActionStep(
        id="analysis_import_auto_download",
        text="",
        action=_copy_demo_file,
        next_step_id="analysis_import_copy_warning",
    ),
    InfoStep(
        id="analysis_import_copy_warning",
        text=(
            "Time to import something! I've dropped a demo file (`demo_tutorial.fcs`) in your Downloads folder.\n\n"  # noqa: E501
            "When it asks whether to copy the file into your workspace, say yes — that's what keeps the project self-contained. "  # noqa: E501
            "Skipping the copy is fine for huge files, but it just links to the original — move that file later and BioPro loses track of it."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="analysis_import_action",
    ),
    InteractionStep(
        id="analysis_import_action",
        text=("Click ➕ Add Samples in the ribbon and pick that demo `.fcs` file from Downloads."),
        target_widget_name="ImportDataButton",
        event_trigger="clicked",
        cyto_emotion="pointing",
        next_step_id="analysis_import_wait",
    ),
    WaitForEventStep(
        id="analysis_import_wait",
        text="Pick the file and give it a second to load...",
        cyto_emotion="scanning",
        event_name="FILE_IMPORTED",
        allow_interaction=True,
        next_step_id="analysis_workflow_intro",
    ),
    InfoStep(
        id="analysis_workflow_intro",
        text=(
            "Loaded! A Workflow is a snapshot of everything right now — settings, gates, parameters — so you can pick this exact session back up later."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="analysis_save_action",
    ),
    WaitForEventStep(
        id="analysis_save_action",
        text=("Let's lock this in. Click 'Save Workflow' in the toolbar."),
        cyto_emotion="happy",
        target_widget_names=["SaveNewWorkflowButton"],
        event_name="WORKFLOW_SAVED",
        allow_interaction=True,
        next_step_id="analysis_return_home_action",
    ),
    InteractionStep(
        id="analysis_return_home_action",
        text=("Saved. Now click ← Home and let's see it show up on your dashboard."),
        target_widget_name="btn_home",
        event_trigger="clicked",
        cyto_emotion="pointing",
        next_step_id="analysis_saved_confirm_spotlight",
    ),
    InfoStep(
        id="analysis_saved_confirm_spotlight",
        text=(
            "There it is — the workflow you just built, sitting under Recent Sessions. One click and you're back in it."  # noqa: E501
        ),
        cyto_emotion="happy",
        target_widget_names=["workflows_container"],
        next_step_id="cleanup_explain",
    ),
    # ── PHASE 4: Graduation ───────────────────────────────────────────────────
    InfoStep(
        id="cleanup_explain",
        text=(
            "Quick housekeeping: the ⚙️ gear on a session card renames or deletes it. To remove a whole project, right-click it back in the Hub's recent list."  # noqa: E501
        ),
        cyto_emotion="talking",
        next_step_id="graduation",
    ),
    InfoStep(
        id="graduation",
        text=(
            "🏆 That's the tour! You've made a project, installed a module, imported real data, and saved your work."  # noqa: E501
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="finish",
    ),
    BranchingStep(
        id="finish",
        text=("You've earned the 🧭 BioPro Explorer badge. Go make something."),
        cyto_emotion="happy",
        options={
            "Let's Start Science! 🔬": "__complete__",
        },
    ),
]

# ── Course object ─────────────────────────────────────────────────────────────

core_intro_course = Course(
    id="core_intro_v1",
    title="BioPro Onboarding Tour",
    description=(
        "A hands-on walkthrough where you create a real project, explore the "
        "Marketplace, open the Flow Cytometry module, import data, and save "
        "your first workflow."
    ),
    estimated_minutes=10,
    badge_reward="BioPro Explorer",
    badge_icon="🧭",
    prerequisite_course_ids=[],
    steps=_steps,
)
