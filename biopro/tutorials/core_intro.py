"""BioPro Core Intro v2 — Active Hands-On Onboarding.

This module defines the ``core_intro_course`` — a Cyto-narrated tutorial that
guides the user through every core BioPro concept *by actually doing it*, not
just reading about it.

Journey:
  Hub
  ├── 1. Welcome
  ├── 2. What is a Project? (spotlight Create New Project)
  └── 3. [WaitForEvent: PROJECT_LOADED] — user creates their first project

  Workspace Home Screen
  ├── 4. You're in! Workspace overview
  ├── 5. The Marketplace explained (spotlight Store button)
  ├── 6. [WaitForEvent: STORE_OPENED] — user opens the Marketplace
  ├── 7. Inside the Marketplace: security / module signing
  ├── 8. Inside the Marketplace: updates & versioning
  ├── 9. Inside the Marketplace: Flow Cytometry module (adaptive message)
  ├── 10. [WaitForEvent: STORE_CLOSED] — user closes the Marketplace
  ├── 11. Module cards explained (spotlight Flow Cytometry card)
  └── 12. [WaitForEvent: MODULE_OPENED] — user opens the module

  Analysis Panel (Flow Cytometry)
  ├── 13. You're in the module! Overview
  ├── 14. File safety: hashing & why BioPro never modifies raw data
  ├── 15. Download the demo FCS file (GitHub link)
  ├── 16. [WaitForEvent: FILE_IMPORTED] — user imports the demo file
  ├── 17. Workflows explained — save your work
  └── 18. [WaitForEvent: WORKFLOW_SAVED] — user saves a workflow

  Back to Home
  ├── 19. Graduation summary — see the workflow card
  └── 20. [BranchingStep] "Let's Start Science! 🔬" → complete + badge

The course is registered on ``module_id = "core"`` — a reserved sentinel.
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


def _copy_demo_file(main_panel: Any) -> None:
    import contextlib
    import shutil
    from pathlib import Path

    # Find the bundled demo file in the repository
    base_dir = Path(__file__).parent.parent.parent
    src_file = base_dir / "biopro" / "tutorials" / "assets" / "demo_tutorial.fcs"

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
            # Check if sizes match to avoid overwriting a user's differently sized file of the same name
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
            "Hello! I'm Cyto 👋 — your intelligent assistant. Let's take a quick tour of BioPro before we dive into your analysis."
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="hub_orientation",
    ),
    InfoStep(
        id="hub_orientation",
        text=(
            "This is the Hub — BioPro's central dashboard. Your recent projects are listed on the left, and the primary actions to start new work are in the center."
        ),
        cyto_emotion="talking",
        target_widget_names=["list_recent", "btn_new", "btn_open"],
        next_step_id="hub_what_is_project",
    ),
    InfoStep(
        id="hub_what_is_project",
        text=(
            "In BioPro, all your work is organized into Projects. A project is a secure, isolated directory on your local machine that contains your raw data, analysis workflows, and results. This ensures your datasets remain neatly separated."
        ),
        cyto_emotion="talking",
        next_step_id="hub_project_storage",
    ),
    InfoStep(
        id="hub_project_storage",
        text=(
            "Within a project folder, you'll find: the `project.biopro` configuration file, an `assets/` directory for imported data, and your saved workflow files. BioPro operates strictly within this boundary to maintain data integrity."
        ),
        cyto_emotion="idle",
        next_step_id="hub_create_project_action",
    ),
    WaitForEventStep(
        id="hub_create_project_action",
        text=(
            "Let's create your first project. 👉 Click ✨ Create New Project, assign it a name, and select a destination folder."
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
            "🎉 Project successfully created! You are now in your Workspace — the command center for all activity within this specific project."
        ),
        cyto_emotion="happy",
        next_step_id="ws_header_bar",
    ),
    InfoStep(
        id="ws_header_bar",
        text=(
            "The header bar provides quick access to core utilities: the ☁️ Store for installing new modules, 🧠 AI Chat for your built-in scientific assistant, and 🎓 Academy for guided analysis tutorials."
        ),
        cyto_emotion="talking",
        target_widget_names=["btn_store", "btn_ai", "btn_academy"],
        next_step_id="ws_ai_chat_intro",
    ),
    InfoStep(
        id="ws_ai_chat_intro",
        text=(
            "The AI Chat utilizes a local Gemma model running directly on your machine, ensuring complete privacy — your data never leaves your computer. It serves as an intelligent assistant to help you navigate BioPro and consult documentation."
        ),
        cyto_emotion="happy",
        target_widget_names=["btn_ai"],
        next_step_id="ws_academy_intro",
    ),
    InfoStep(
        id="ws_academy_intro",
        text=(
            "The Academy is your learning center for BioPro. The global hub displays all available courses across your installed modules, along with the badges you've earned. You can launch tutorials directly from the hub or from within specific modules."
        ),
        cyto_emotion="pointing",
        target_widget_names=["btn_academy"],
        next_step_id="ws_store_intro",
    ),
    InfoStep(
        id="ws_store_intro",
        text=(
            "Let's explore the Store. BioPro is built with a modular architecture — you only install the specific tools you need. Modules are updated independently of the core application, ensuring you always have access to the latest features."
        ),
        cyto_emotion="happy",
        next_step_id="ws_store_open_action",
    ),
    WaitForEventStep(
        id="ws_store_open_action",
        text=("Click the ☁️ Store icon in the top-right corner to open the Marketplace."),
        cyto_emotion="pointing",
        target_widget_names=["btn_store"],
        event_name="STORE_OPENED",
        allow_interaction=True,
        next_step_id="ws_store_inside_catalog",
    ),
    InfoStep(
        id="ws_store_inside_catalog",
        text=(
            "The Store catalog lists all available modules. Modules with the 🛡️ VERIFIED badge have passed a rigorous security and code-quality review by the BioPro team."
        ),
        cyto_emotion="talking",
        target_widget_names=["store_card_flow_cytometry"],
        next_step_id="ws_store_security",
    ),
    InfoStep(
        id="ws_store_security",
        text=(
            "Security is a core principle: BioPro verifies the module developer's identity against our Root CA and validates the code signature to prevent tampering. For custom in-house tools, a manual trust override is available."
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_updates",
    ),
    InfoStep(
        id="ws_store_updates",
        text=(
            "The Store also tracks updates for your installed modules. When an update is available, clicking 'Update' will automatically download, verify, and seamlessly install the new version."
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_flow_details_action",
    ),
    WaitForEventStep(
        id="ws_store_flow_details_action",
        text=(
            "Locate the Flow Cytometry module card and click 'Details' to view its documentation."
        ),
        cyto_emotion="pointing",
        target_widget_names=["store_card_flow_cytometry"],
        event_name="STORE_MODULE_DETAILS_OPENED",
        allow_interaction=True,
        next_step_id="ws_store_details_explain",
    ),
    InfoStep(
        id="ws_store_details_explain",
        text=(
            "The details panel provides a comprehensive overview of the module's capabilities, along with information about its authors and contributors."
        ),
        cyto_emotion="talking",
        target_widget_names=["ModuleDetailsPanel"],
        next_step_id="ws_store_install_action",
    ),
    WaitForEventStep(
        id="ws_store_install_action",
        text=(
            "Ensure you have the latest version installed, and then close the Marketplace to return to your workspace."
        ),
        cyto_emotion="talking",
        event_name="STORE_CLOSED",
        allow_interaction=True,
        next_step_id="ws_layout_top",
    ),
    InfoStep(
        id="ws_layout_top",
        text=(
            "At the top of the dashboard, you will find your module cards. Each card acts as a gateway to a specialized analysis environment."
        ),
        cyto_emotion="talking",
        target_widget_names=["moduleCard"],
        next_step_id="ws_layout_bottom",
    ),
    InfoStep(
        id="ws_layout_bottom",
        text=(
            "Below are your Recent Sessions. All saved analysis workflows for the current project are displayed here, allowing you to resume your work with a single click."
        ),
        cyto_emotion="talking",
        target_widget_names=["workflows_container"],
        next_step_id="ws_module_card_explain",
    ),
    InfoStep(
        id="ws_module_card_explain",
        text=(
            "Notice that the Flow Cytometry module card is now available in your workspace. Each card displays the module's name, icon, and security trust level. Click the card to launch the analysis environment."
        ),
        cyto_emotion="talking",
        target_widget_names=["module_card_flow_cytometry_workspace"],
        next_step_id="ws_open_module_action",
    ),
    WaitForEventStep(
        id="ws_open_module_action",
        text=("Click the Flow Cytometry card to open the analysis environment."),
        cyto_emotion="pointing",
        target_widget_names=["module_card_flow_cytometry_workspace"],
        event_name="MODULE_OPENED",
        allow_interaction=True,
        next_step_id="analysis_landed",
    ),
    # ── PHASE 3: Analysis Panel ───────────────────────────────────────────────
    InfoStep(
        id="analysis_landed",
        text=(
            "Welcome to the Flow Cytometry analysis environment! 🧬 Each module provides a dedicated, purpose-built workspace like this one."
        ),
        cyto_emotion="cheering",
        next_step_id="analysis_toolbar",
    ),
    InfoStep(
        id="analysis_toolbar",
        text=(
            "The top toolbar allows you to navigate ← Home to the dashboard, close the current project, or access the AI Chat at any time."
        ),
        cyto_emotion="talking",
        target_widget_names=["analysisToolBar"],
        next_step_id="analysis_data_integrity",
    ),
    InfoStep(
        id="analysis_data_integrity",
        text=(
            "Before importing data, it's important to understand BioPro's approach to data integrity. Your raw files are never modified. Upon import, files are cryptographically hashed (SHA-256) and copied to the project's `assets/` directory, leaving the original source files completely untouched."
        ),
        cyto_emotion="talking",
        next_step_id="analysis_import_explain",
    ),
    InfoStep(
        id="analysis_import_explain",
        text=(
            "This means your analysis is always reproducible. If someone else opens your project, BioPro will verify the file hash matches — instantly flagging any data corruption."
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
            "Time to import data! A demo file (`demo_tutorial.fcs`) has been automatically placed in your Downloads folder.\n\n"
            "When prompted to copy the file to your workspace, click Yes to ensure data portability. "
            "While you can opt to skip copying for very large files, doing so links the original file to your project. If that original file is subsequently moved, BioPro will lose track of it."
        ),
        cyto_emotion="talking",
        next_step_id="analysis_import_action",
    ),
    InteractionStep(
        id="analysis_import_action",
        text=(
            "Let's load the demo data.\n\nClick ➕ Add Samples in the workspace ribbon and select the demo `.fcs` file from your Downloads folder."
        ),
        target_widget_name="ImportDataButton",
        event_trigger="clicked",
        cyto_emotion="pointing",
        next_step_id="analysis_import_wait",
    ),
    WaitForEventStep(
        id="analysis_import_wait",
        text="Choose the demo file and wait for the import to finish...",
        cyto_emotion="working",
        event_name="FILE_IMPORTED",
        allow_interaction=True,
        next_step_id="analysis_workflow_intro",
    ),
    InfoStep(
        id="analysis_workflow_intro",
        text=(
            "Your file is now loaded. A Workflow is a saved snapshot of your entire analysis session — all your settings, gates, and parameters. It lets you pick up exactly where you left off."
        ),
        cyto_emotion="talking",
        next_step_id="analysis_save_action",
    ),
    WaitForEventStep(
        id="analysis_save_action",
        text=("Let's save your current workspace state. Click 'Save Workflow' in the toolbar."),
        cyto_emotion="happy",
        target_widget_names=["SaveNewWorkflowButton"],
        event_name="WORKFLOW_SAVED",
        allow_interaction=True,
        next_step_id="analysis_return_home_action",
    ),
    InteractionStep(
        id="analysis_return_home_action",
        text=(
            "Your workflow is successfully saved. Let's return to the Dashboard to view it.\n\n"
            "Click ← Home in the toolbar."
        ),
        target_widget_name="btn_home",
        event_trigger="clicked",
        cyto_emotion="pointing",
        next_step_id="analysis_saved_confirm_spotlight",
    ),
    InfoStep(
        id="analysis_saved_confirm_spotlight",
        text=(
            "You have successfully returned to the dashboard. Notice that your saved session now appears under Recent Sessions. You can restore your analysis state with a single click."
        ),
        cyto_emotion="happy",
        target_widget_names=["workflows_container"],
        next_step_id="cleanup_explain",
    ),
    # ── PHASE 4: Graduation ───────────────────────────────────────────────────
    InfoStep(
        id="cleanup_explain",
        text=(
            "To manage a previous session — such as renaming or deleting it — click the ⚙️ gear icon on its Dashboard card. To delete an entire project, simply right-click it in the Hub's Recent Projects list."
        ),
        cyto_emotion="talking",
        next_step_id="graduation",
    ),
    InfoStep(
        id="graduation",
        text=(
            "🏆 That concludes the tour! You are now equipped to create projects, install modules via the Store, import data securely, and manage your analysis workflows."
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="finish",
    ),
    BranchingStep(
        id="finish",
        text=(
            "You have successfully earned the 🧭 BioPro Explorer badge! Click below to begin your independent exploration."
        ),
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
    estimated_minutes=12,
    badge_reward="BioPro Explorer",
    badge_icon="🧭",
    prerequisite_course_ids=[],
    steps=_steps,
)
