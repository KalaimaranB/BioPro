"""Menu Manager for WorkspaceWindow."""

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMenu

from biopro.core.config import AppConfig
from biopro.shared.ui.alerts import show_about
from biopro.ui.theme import theme_manager


class MenuManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def setup_menu_bar(self) -> None:
        """
        Builds and attaches the application's File, Edit, Theme, and Help menus to the main window.
        """
        mw = self.main_window
        menubar = mw.menuBar()
        assert menubar is not None

        file_menu = QMenu("&File", mw)
        menubar.addMenu(file_menu)

        # --- Edit Menu for History ---
        edit_menu = QMenu("&Edit", mw)
        menubar.addMenu(edit_menu)

        undo_action = QAction("&Undo", mw)
        # Magic cross-platform native Undo shortcut
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        if hasattr(mw, "trigger_undo"):
            undo_action.triggered.connect(mw.trigger_undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", mw)
        # Magic cross-platform native Redo shortcut
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        if hasattr(mw, "trigger_redo"):
            redo_action.triggered.connect(mw.trigger_redo)
        edit_menu.addAction(redo_action)
        # -----------------------------

        open_action = QAction("&Open File...", mw)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(
            mw._on_open_file if hasattr(mw, "_on_open_file") else lambda: None
        )
        file_menu.addAction(open_action)
        file_menu.addSeparator()

        home_action = QAction("&Home Screen", mw)
        home_action.setShortcut("Ctrl+H")
        home_action.triggered.connect(
            mw.hub_manager.show_home if hasattr(mw, "hub_manager") else mw._show_home
        )
        file_menu.addAction(home_action)
        file_menu.addSeparator()

        close_project_action = QAction("Close Project && Return to Hub", mw)
        close_project_action.triggered.connect(mw.return_to_hub)
        file_menu.addAction(close_project_action)

        exit_action = QAction("E&xit", mw)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(mw.close)
        file_menu.addAction(exit_action)

        theme_menu = QMenu("&Theme", mw)
        menubar.addMenu(theme_menu)

        # DYNAMIC THEME DISCOVERY
        available_themes = theme_manager.discover_themes()
        for name, path in available_themes:
            action = QAction(name, mw)
            if hasattr(mw, "theme_manager"):
                action.triggered.connect(lambda checked, p=path: mw.theme_manager.switch_theme(p))  # noqa: ARG005
            else:
                action.triggered.connect(lambda checked, p=path: mw._switch_theme(p))  # noqa: ARG005
            theme_menu.addAction(action)

        # Help Menu
        help_menu = QMenu("&Help", mw)
        menubar.addMenu(help_menu)

        docs_action = QAction("📖 BioPro &Help Center", mw)
        docs_action.setShortcut(QKeySequence("F1"))
        docs_action.triggered.connect(self.open_help_center)
        help_menu.addAction(docs_action)

        help_menu.addSeparator()

        wiki_action = QAction("🌐 View GitHub Wiki Online", mw)
        wiki_action.triggered.connect(self.open_wiki_online)
        help_menu.addAction(wiki_action)

        about_action = QAction("🧬 &About BioPro", mw)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        help_menu.addSeparator()

        restart_tour_action = QAction("♻️ Restart Onboarding Tour", mw)
        restart_tour_action.triggered.connect(
            mw.hub_manager.restart_core_intro
            if hasattr(mw, "hub_manager")
            else mw._restart_core_intro
        )
        help_menu.addAction(restart_tour_action)

        view_logs_action = QAction("📜 View Logs", mw)
        view_logs_action.triggered.connect(self.view_logs)
        help_menu.addAction(view_logs_action)

    def setup_shortcuts(self):
        """Register global app shortcuts."""
        help_shortcut = QAction(self.main_window)
        help_shortcut.setShortcut(QKeySequence("F1"))
        help_shortcut.triggered.connect(self.open_help_center)
        self.main_window.addAction(help_shortcut)

    def open_help_center(self):
        """Launch the localized help center."""
        from biopro.ui.dialogs.help_dialog import HelpCenterDialog

        dialog = HelpCenterDialog(
            module_manager=self.main_window.module_manager, parent=self.main_window
        )
        dialog.exec()

    def open_wiki_online(self):
        """Open the public wiki in the browser."""
        import webbrowser

        webbrowser.open("https://github.com/KalaimaranB/BioPro/wiki")

    def view_logs(self):
        """View application logs."""
        from biopro.ui.dialogs.log_viewer import LogViewerDialog

        dialog = LogViewerDialog(self.main_window)
        dialog.exec()

    def show_about(self) -> None:
        # Dynamic Version from Config!
        show_about(
            self.main_window,
            "About BioPro",
            f"<h2>🧬 BioPro v{AppConfig.CORE_VERSION}</h2>"
            "<p>Bio Analysis Made Simple</p>"
            "<p>An open-source, intuitive platform for lab students "
            "and professionals.</p>"
            "<p>© 2026 BioPro Contributors<br>"
            "Licensed under the MIT License</p>",
        )

    def open_ai_chat(self):
        """Opens the AI floating panel for contextual help."""
        from biopro.ui.components.ai_panel import AIChatWindow

        # Make the AI window a child of main window but as a tool (floating, on top)
        if not hasattr(self.main_window, "ai_window") or self.main_window.ai_window is None:
            self.main_window.ai_window = AIChatWindow(self.main_window)

        if self.main_window.ai_window.isHidden():
            self.main_window.ai_window.show()
            self.main_window.ai_window.raise_()
            self.main_window.ai_window.activateWindow()
        else:
            self.main_window.ai_window.hide()
