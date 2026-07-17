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
    WaitForEventStep,
)


def _copy_demo_file(main_panel: Any) -> None:
    import shutil
    from pathlib import Path

    # Find the bundled demo file in the repository
    base_dir = Path(__file__).parent.parent.parent
    src_file = base_dir / "biopro" / "tutorials" / "assets" / "demo_tutorial.fcs"

    # Copy to user's Downloads folder
    downloads_dir = Path.home() / "Downloads"
    dest_file = downloads_dir / "demo_tutorial.fcs"

    import contextlib

    with contextlib.suppress(Exception):
        shutil.copy(src_file, dest_file)


# Demo FCS logic now handled by `_copy_demo_file` action step.

# ── Step definitions ──────────────────────────────────────────────────────────

_steps = [
    # ── PHASE 1: Hub ──────────────────────────────────────────────────────────
    InfoStep(
        id="hub_welcome",
        text=(
            "Hey! I'm Cyto 👋 — I'll be your guide. Let me show you around BioPro before we dive in."
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="hub_orientation",
    ),
    InfoStep(
        id="hub_orientation",
        text=(
            "This is the Hub — BioPro's home screen. On the left, you'll see your recent projects. The big buttons in the centre are how you get started."
        ),
        cyto_emotion="talking",
        target_widget_names=["list_recent", "btn_new", "btn_open"],
        next_step_id="hub_what_is_project",
    ),
    InfoStep(
        id="hub_what_is_project",
        text=(
            "In BioPro, everything lives inside a Project. A project is a secure, isolated folder on your computer containing your raw data, analysis workflows, and results — nothing bleeds between projects."
        ),
        cyto_emotion="talking",
        next_step_id="hub_project_storage",
    ),
    InfoStep(
        id="hub_project_storage",
        text=(
            "Inside a project folder you'll find: `project.biopro` (config), `assets/` (your imported files), and workflow files (your saved analyses). BioPro never touches files outside this folder."
        ),
        cyto_emotion="idle",
        next_step_id="hub_create_project_action",
    ),
    WaitForEventStep(
        id="hub_create_project_action",
        text=(
            "Let's create your first one. 👉 Click ✨ Create New Project, give it a name, and pick a folder."
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
            "🎉 Project created! You've just entered your Workspace — this is where everything for this project happens."
        ),
        cyto_emotion="happy",
        next_step_id="ws_layout_top",
    ),
    InfoStep(
        id="ws_layout_top",
        text=(
            "At the top of the dashboard you'll see module cards — these are your analysis tools. Each card launches a different type of analysis environment."
        ),
        cyto_emotion="talking",
        target_widget_names=["moduleCard"],
        next_step_id="ws_layout_bottom",
    ),
    InfoStep(
        id="ws_layout_bottom",
        text=(
            "Below the modules is Recent Sessions — all your past saved analyses for this project appear here as cards. You can re-open them with one click."
        ),
        cyto_emotion="talking",
        target_widget_names=["workflowCard"],
        next_step_id="ws_header_bar",
    ),
    InfoStep(
        id="ws_header_bar",
        text=(
            "The header bar also has a few buttons: ☁️ Store to install new tools, 🧠 AI Chat for your built-in scientific assistant, and 🎓 Academy for guided analysis courses."
        ),
        cyto_emotion="talking",
        target_widget_names=["btn_store", "btn_ai", "btn_academy"],
        next_step_id="ws_store_intro",
    ),
    InfoStep(
        id="ws_store_intro",
        text=(
            "Let's explore the Store first. BioPro is fully modular — you only install the tools you actually need. Modules update independently of the core app, so you're always on the latest version of each tool."
        ),
        cyto_emotion="happy",
        next_step_id="ws_store_open_action",
    ),
    WaitForEventStep(
        id="ws_store_open_action",
        text=("Click ☁️ Store in the top-right to open the Marketplace."),
        cyto_emotion="pointing",
        target_widget_names=["btn_store"],
        event_name="STORE_OPENED",
        allow_interaction=True,
        next_step_id="ws_store_inside_catalog",
    ),
    InfoStep(
        id="ws_store_inside_catalog",
        text=(
            "Inside the Store you'll see a catalog of all available modules. Notice the 🛡️ VERIFIED ROOT badge on official modules — this means they've passed a rigorous review."
        ),
        cyto_emotion="talking",
        target_widget_names=["moduleCard"],
        next_step_id="ws_store_security",
    ),
    InfoStep(
        id="ws_store_security",
        text=(
            "Security is built-in: BioPro verifies the developer's identity against our Root CA, then checks the code signature to ensure no tampering occurred. If you write custom code, you can use a Manual Override key."
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_updates",
    ),
    InfoStep(
        id="ws_store_updates",
        text=(
            "In the Store you'll also see if any installed modules have updates available. Click Update to get the latest version — it downloads, verifies, and swaps in the new version automatically."
        ),
        cyto_emotion="talking",
        next_step_id="ws_store_install_action",
    ),
    WaitForEventStep(
        id="ws_store_install_action",
        text=("Find the Flow Cytometry module, install or update it, then close the Store."),
        cyto_emotion="pointing",
        event_name="STORE_CLOSED",
        allow_interaction=True,
        next_step_id="ws_module_card_explain",
    ),
    InfoStep(
        id="ws_module_card_explain",
        text=(
            "A Flow Cytometry module card now appears in your workspace. Each card shows the module's name, icon, and trust level. Click a card to launch that analysis environment."
        ),
        cyto_emotion="talking",
        target_widget_names=["moduleCard"],
        next_step_id="ws_open_module_action",
    ),
    WaitForEventStep(
        id="ws_open_module_action",
        text=("Click the Flow Cytometry card to open the analysis environment."),
        cyto_emotion="pointing",
        target_widget_names=["moduleCard"],
        event_name="MODULE_OPENED",
        allow_interaction=True,
        next_step_id="analysis_landed",
    ),
    # ── PHASE 3: Analysis Panel ───────────────────────────────────────────────
    InfoStep(
        id="analysis_landed",
        text=(
            "You're in the Flow Cytometry analysis environment! 🧬 Each module gets its own dedicated workspace like this."
        ),
        cyto_emotion="cheering",
        next_step_id="analysis_toolbar",
    ),
    InfoStep(
        id="analysis_toolbar",
        text=(
            "The toolbar at the top lets you go ← Home to return to the dashboard, close the project, or open the AI Chat from anywhere inside a module."
        ),
        cyto_emotion="talking",
        target_widget_names=["top_toolbar"],
        next_step_id="analysis_data_integrity",
    ),
    InfoStep(
        id="analysis_data_integrity",
        text=(
            "Before we import any data — a key promise: BioPro will never modify your raw files. When you import a file, it's hashed (SHA-256), copied into your project's `assets/` folder, and the original is left untouched."
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
        next_step_id="analysis_import_action",
    ),
    WaitForEventStep(
        id="analysis_import_action",
        text=(
            "Time to import data! I've automatically placed a demo file (`demo_tutorial.fcs`) in your Downloads folder.\n\n"
            "Click Import in the toolbar to load it."
        ),
        cyto_emotion="pointing",
        target_widget_names=["ImportDataButton"],
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
        text=(
            "Save your work now: click Save Workflow in the toolbar, or press Ctrl+S (Cmd+S on Mac)."
        ),
        cyto_emotion="happy",
        target_widget_names=["SaveNewWorkflowButton"],
        event_name="WORKFLOW_SAVED",
        allow_interaction=True,
        next_step_id="analysis_saved_confirm",
    ),
    InfoStep(
        id="analysis_saved_confirm",
        text=(
            "Your workflow is saved! If you go back to the Dashboard, you'll see it appear in Recent Sessions."
        ),
        cyto_emotion="happy",
        next_step_id="ai_chat_intro",
    ),
    InfoStep(
        id="ai_chat_intro",
        text=(
            "One last thing: BioPro features a built-in AI assistant. It runs a local model (Gemma) directly on your machine, so your data never leaves your computer! (It's currently a work in progress 🛠️)"
        ),
        cyto_emotion="talking",
        next_step_id="cleanup_explain",
    ),
    # ── PHASE 4: Graduation ───────────────────────────────────────────────────
    InfoStep(
        id="cleanup_explain",
        text=(
            "To manage a past session — rename or delete it — click the ⚙️ gear icon on its Dashboard card. To delete an entire project, right-click it in the Hub's Recent Projects list."
        ),
        cyto_emotion="talking",
        next_step_id="graduation",
    ),
    InfoStep(
        id="graduation",
        text=(
            "🏆 That's the full tour! You now know how to create projects, install modules from the Store, import data safely, and save your work."
        ),
        cyto_emotion="cheering",
        cyto_animation="cheering",
        next_step_id="finish",
    ),
    BranchingStep(
        id="finish",
        text=(
            "You've earned the 🔬 BioPro Explorer badge! Click below to start exploring for real."
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
    badge_reward="🔬 BioPro Explorer",
    badge_icon="🔬",
    prerequisite_course_ids=[],
    steps=_steps,
)
