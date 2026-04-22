"""Workspace Dashboard (Home Screen inside Workspace) for BioPro."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget, QPushButton, QMessageBox
)

from biopro.ui.theme import Colors, Fonts
from biopro.ui.components.cards import ModuleCard, DashboardWorkflowCard as WorkflowCard
from biopro.ui.widgets.dna_loader import ProgrammaticLoader

class WorkspaceDashboard(QWidget):
    """Welcome / dashboard screen."""

    module_selected = pyqtSignal(dict)  # Passes manifest
    workflow_selected = pyqtSignal(str, str) # Passes (module_id, filename)
    workflow_delete_requested = pyqtSignal(str, str) # Passes (module_id, filename)
    
    return_to_hub_requested = pyqtSignal()
    open_store_requested = pyqtSignal()
    open_ai_requested = pyqtSignal()
    trust_module_requested = pyqtSignal(str) # Passes module_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Hero banner ───────────────────────────────────────────────
        hero = QWidget()
        hero.setObjectName("heroWidget")
        hero.setStyleSheet(f"QWidget#heroWidget {{ background: {Colors.BG_DARK}; border-bottom: 1px solid {Colors.BORDER}; }}")
        
        # FIX: Changed from Fixed to Minimum to allow the container to grow with the new text elements
        hero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        hero_layout = QVBoxLayout(hero)
        # FIX: Generous margins and spacing to prevent vertical crowding
        hero_layout.setContentsMargins(56, 48, 56, 40) 
        hero_layout.setSpacing(12) 

        # 1. Title Row (Logo + Buttons)
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignVCenter) 
        
        # Replacing static logo with high-fidelity DNA animation
        self.logo_animation = ProgrammaticLoader()
        self.logo_animation.setFixedSize(100, 100) # Compact for the header
        title_row.addWidget(self.logo_animation)

        name = QLabel("BioPro")
        name.setStyleSheet(f"font-size: 34px; font-weight: 800; color: {Colors.FG_PRIMARY}; background: transparent; letter-spacing: -1px;")
        title_row.addWidget(name)
        title_row.addStretch()

        self.btn_store = QPushButton("☁️ Store")
        self.btn_store.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {Colors.BORDER}; border-radius: 5px; padding: 6px 14px; margin-left: 20px; color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_MEDIUM}; border-color: {Colors.ACCENT_PRIMARY}; }}"
        )
        self.btn_store.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_store.clicked.connect(self.open_store_requested.emit)
        title_row.addWidget(self.btn_store)

        self.btn_ai = QPushButton("🧠 AI Chat")
        self.btn_ai.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {Colors.BORDER}; border-radius: 5px; padding: 6px 14px; margin-left: 10px; color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_MEDIUM}; border-color: {Colors.ACCENT_PRIMARY}; }}"
        )
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(self.open_ai_requested.emit)
        title_row.addWidget(self.btn_ai)

        self.btn_return_hub = QPushButton("🏠 Return to Project Hub")
        self.btn_return_hub.setStyleSheet(
            f"QPushButton {{"
            f"  background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER};"
            f"  border-radius: 5px; padding: 6px 14px; margin-left: 20px;"
            f"  color: {Colors.FG_PRIMARY}; font-size: {Fonts.SIZE_SMALL}px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f"}}"
        )
        self.btn_return_hub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_return_hub.clicked.connect(self.return_to_hub_requested.emit)
        title_row.addWidget(self.btn_return_hub)

        hero_layout.addLayout(title_row)

        # 2. Greeting Row
        # Added intentional spacing between the title row and the greeting
        hero_layout.addSpacing(4) 

        self.lbl_greeting = QLabel("Good morning.")
        self.lbl_greeting.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 600; color: {Colors.FG_PRIMARY};")
        hero_layout.addWidget(self.lbl_greeting)

        # 3. Tagline Row
        self.lbl_tagline = QLabel("Bio-Image Analysis Made Simple — open-source alternative to ImageJ")
        self.lbl_tagline.setStyleSheet(f"font-size: {Fonts.SIZE_NORMAL}px; color: {Colors.FG_SECONDARY}; background: transparent;")
        hero_layout.addWidget(self.lbl_tagline)
        
        # 4. Stats Pill Row
        stats_layout = QHBoxLayout()
        self.stat_modules = QLabel("0 Modules Active")
        self.stat_modules.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; border: 1px solid {Colors.BORDER}; "
            f"padding: 4px 10px; border-radius: 12px; background: {Colors.BG_DARKEST}; font-size: 11px;"
        )
        stats_layout.addWidget(self.stat_modules)
        stats_layout.addStretch()
        hero_layout.addLayout(stats_layout)

        root.addWidget(hero)
        
        # Call the update text method to apply Star Wars overrides or time-based greeting
        self._update_dashboard_text()

        # ── Dashboard Content (Scrollable Area) ───────────────────────────────
        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(56, 36, 56, 36)
        content_layout.setSpacing(30)

        # Recent Workflows Section
        self.workflows_container = QWidget()
        wf_layout = QVBoxLayout(self.workflows_container)
        wf_layout.setContentsMargins(0, 0, 0, 0)
        wf_layout.setSpacing(14)
        
        wf_lbl = QLabel("Recent Sessions")
        wf_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 600; color: {Colors.FG_PRIMARY};")
        wf_layout.addWidget(wf_lbl)

        self.workflows_grid = QGridLayout()
        self.workflows_grid.setSpacing(14)
        self.workflows_grid.setColumnStretch(0, 1)
        self.workflows_grid.setColumnStretch(1, 1)
        self.workflows_grid.setColumnStretch(2, 1)
        wf_layout.addLayout(self.workflows_grid)
        content_layout.addWidget(self.workflows_container)

        # New Analysis Section
        new_lbl = QLabel("Start New Analysis")
        new_lbl.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 600; color: {Colors.FG_PRIMARY};")
        content_layout.addWidget(new_lbl)

        self.modules_grid = QGridLayout()
        self.modules_grid.setSpacing(14)
        self.modules_grid.setColumnStretch(0, 1)
        self.modules_grid.setColumnStretch(1, 1)
        self.modules_grid.setColumnStretch(2, 1)
        content_layout.addLayout(self.modules_grid)

        content_layout.addStretch()
        root.addWidget(content, stretch=1)

    # ── Population Methods ──

    def populate_modules(self, manifests: list[dict]) -> None:
        """Dynamically build the selection grid based on installed plugins."""
        for i in reversed(range(self.modules_grid.count())): 
            widget = self.modules_grid.itemAt(i).widget()
            if widget: widget.setParent(None)

        if not manifests:
            lbl = QLabel("No analysis modules installed. Use the Store to download plugins.")
            lbl.setStyleSheet(f"color: {Colors.FG_DISABLED}; font-style: italic;")
            self.modules_grid.addWidget(lbl, 0, 0)
            return
        
        self.stat_modules.setText(f"📡 {len(manifests)} Modules Active") # Update the stat

        for i, manifest in enumerate(manifests):
            card = ModuleCard(
                icon=manifest.get("icon", "📦"),
                title=manifest.get("name", "Unknown Module"),
                description=manifest.get("description", ""),
                badge="Installed",
                enabled=True,
                trust_level=manifest.get("trust_level", "verified"),
                trust_path=manifest.get("trust_path", []),
                developer_name=manifest.get("developer_name"),
                developer_key=manifest.get("developer_key")
            )
            card.clicked.connect(lambda *args, m=manifest: self.module_selected.emit(m))
            card.trust_requested.connect(lambda *args, mid=manifest.get("id"): self.trust_module_requested.emit(mid))
            self.modules_grid.addWidget(card, i // 3, i % 3)

    def populate_workflows(self, workflows: list[dict]) -> None:
        """Populate the recent sessions grid with WorkflowCards."""
        for i in reversed(range(self.workflows_grid.count())): 
            widget = self.workflows_grid.itemAt(i).widget()
            if widget: widget.setParent(None)

        if not workflows:
            self.workflows_container.setVisible(False)
            return
            
        self.workflows_container.setVisible(True)

        for i, wf in enumerate(workflows):
            filename = wf.get("filename", "")
            module_id = wf.get("module_id", "Unknown")
            
            # Make the module ID prettier (e.g., "western_blot" -> "Western Blot")
            pretty_mod = module_id.replace("_", " ").title()
            
            title = wf.get("name", filename.replace('.json', ''))
            date_str = wf.get("timestamp", "Unknown Date")

            card = WorkflowCard(title=title, date_str=date_str, module_name=pretty_mod)
            
            # THE LAMBDA FIX: We are now explicitly locking 't=title' into memory!
            card.clicked.connect(lambda *args, mid=module_id, fn=filename: self.workflow_selected.emit(mid, fn))
            card.delete_requested.connect(lambda *args, mid=module_id, fn=filename, t=title: self._confirm_delete(mid, fn, t))
            
            self.workflows_grid.addWidget(card, i // 3, i % 3)

    def _confirm_delete(self, module_id: str, filename: str, title: str) -> None:
        """Prompt the user before emitting the delete signal."""
        reply = QMessageBox.question(
            self,
            "Delete Workflow",
            f"Are you sure you want to permanently delete '{title}'?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.workflow_delete_requested.emit(module_id, filename)

    def _update_dashboard_text(self):
        import datetime
        hour = datetime.datetime.now().hour
        
        # The logic to detect Star Wars mode
        is_dark_side = getattr(Colors, "DNA_PRIMARY", "").lower() == "#e60000"
        
        if is_dark_side:
            greeting = "Awaiting commands, Commander"
            tagline = "Imperial Analysis Mainframe — Unlimited Power."
            self.lbl_greeting.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 900; color: {Colors.ACCENT_PRIMARY}; text-transform: uppercase;")
        else:
            greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
            tagline = "Bio-Image Analysis Made Simple — open-source alternative to ImageJ"
            self.lbl_greeting.setStyleSheet(f"font-size: {Fonts.SIZE_LARGE}px; font-weight: 600; color: {Colors.FG_PRIMARY};")

        self.lbl_greeting.setText(f"{greeting}.")
        self.lbl_tagline.setText(tagline)