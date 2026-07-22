"""Module Store and Update Dialog."""

from pathlib import Path

from biopro_sdk.plugin import DangerButton, ModuleCard, PrimaryButton, SecondaryButton
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.module_manager import ModuleManager
from biopro.core.network_updater import NetworkUpdater
from biopro.ui.theme import Colors


class TrustPathDialog(QDialog):
    """Visualizes the exact cryptographic chain of trust for a developer."""

    def __init__(self, dev_id: str, name: str, pub_key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Trust Path Verification: {name}")
        self.setMinimumSize(450, 420)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Info
        header_lbl = QLabel(f"Verification Path for {name}")
        header_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 800; color: {Colors.ACCENT_PRIMARY}; border: none;"
        )
        layout.addWidget(header_lbl)

        # Determine path type
        path_type = "Verified Root Trust Chain"
        path_desc = "This developer is part of the official co-signing chain distributed directly by BioPro Core."
        step_color = Colors.DNA_PRIMARY
        steps = []

        manual_path = Path.home() / ".biopro" / "trusted_roots" / f"manual_{dev_id}.pub"
        network_path = Path.home() / ".biopro" / "trusted_roots" / f"network_{dev_id}.pub"

        if manual_path.exists():
            path_type = "Manually Approved Root (Local Override)"
            path_desc = "You manually approved and pinned this developer's public key as a local trusted authority."
            step_color = Colors.ACCENT_SUCCESS
            steps = [
                ("👤 End User (You)", "Authorized local override exception for this machine."),
                (
                    "⚠️ Local Override Anchor",
                    "Key imported into local trusted_roots storage directory.",
                ),
                (
                    f"👤 {name} (Developer Key)",
                    "Cryptographically allowed to run custom and local plugins.",
                ),
            ]
        elif network_path.exists():
            steps = [
                (
                    "🏛️ BioPro Root CA Anchor",
                    "Hardcoded cryptographic root of trust inside the core host.",
                ),
                (
                    "🏫 Authorities Registry",
                    "Registry signed by the Root CA verifying legitimate developer mappings.",
                ),
                (
                    f"👤 {name} (Developer Key)",
                    "Valid Ed25519 signature co-signed by the root registry authority.",
                ),
            ]
        else:
            if pub_key:
                path_type = "Unverified Self-Signed Identity"
                path_desc = "This developer has self-signed credentials but no verified signature chain from a root authority is present."
                step_color = Colors.ACCENT_WARNING
                steps = [
                    (
                        "🏛️ BioPro Root CA Anchor",
                        "Hardcoded cryptographic root of trust inside the core host.",
                    ),
                    (
                        "❓ Unknown Authority",
                        "No matching authority path found in local or remote registries.",
                    ),
                    (
                        f"👤 {name} (Developer Key)",
                        "Identity is unverified. Running plugins from this key is blocked by default.",
                    ),
                ]
            else:
                path_type = "Legacy / Unsigned Identity"
                path_desc = "No cryptographic identity was declared for this entry."
                step_color = Colors.FG_DISABLED
                steps = [("❓ Unknown Identity", "No public key or signature chain available.")]

        # Path Type Banner
        banner = QWidget()
        banner.setStyleSheet(
            f"background: {step_color}22; border: 1px solid {step_color}44; border-radius: 6px;"
        )
        banner_layout = QVBoxLayout(banner)
        banner_layout.setContentsMargins(12, 12, 12, 12)
        banner_layout.setSpacing(4)

        banner_title = QLabel(path_type)
        banner_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {step_color}; border: none;"
        )
        banner_desc = QLabel(path_desc)
        banner_desc.setWordWrap(True)
        banner_desc.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;")

        banner_layout.addWidget(banner_title)
        banner_layout.addWidget(banner_desc)
        layout.addWidget(banner)

        # Draw visual trust path nodes
        path_box = QWidget()
        path_box.setStyleSheet(
            f"background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER}; border-radius: 6px;"
        )
        path_layout = QVBoxLayout(path_box)
        path_layout.setContentsMargins(15, 15, 15, 15)
        path_layout.setSpacing(10)

        for i, (node_name, node_desc) in enumerate(steps):
            if i > 0:
                arrow = QLabel("▼")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                arrow.setStyleSheet(f"font-size: 12px; color: {step_color}; border: none;")
                path_layout.addWidget(arrow)

            node_widget = QWidget()
            node_widget.setStyleSheet("border: none; background: transparent;")
            node_item = QHBoxLayout(node_widget)
            node_item.setContentsMargins(0, 0, 0, 0)
            node_item.setSpacing(10)

            dot = QLabel("●")
            dot.setStyleSheet(f"font-size: 16px; color: {step_color}; border: none;")
            node_item.addWidget(dot)

            text_layout = QVBoxLayout()
            lbl_title = QLabel(node_name)
            lbl_title.setStyleSheet(
                f"font-size: 12px; font-weight: bold; color: {Colors.FG_PRIMARY}; border: none;"
            )
            lbl_desc = QLabel(node_desc)
            lbl_desc.setStyleSheet(f"font-size: 10px; color: {Colors.FG_SECONDARY}; border: none;")
            text_layout.addWidget(lbl_title)
            text_layout.addWidget(lbl_desc)
            node_item.addLayout(text_layout)
            node_item.addStretch()

            path_layout.addWidget(node_widget)

        layout.addWidget(path_box)

        # Close button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = PrimaryButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)


class PluginDetailsDialog(QDialog):
    """Inspects detailed plugin credentials, co-signing ledger histories, and contributor teams."""

    def __init__(self, plugin_id: str, data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ModuleDetailsPanel")
        self.setWindowTitle(f"Plugin Details: {data['info'].get('name', plugin_id)}")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header: Icon & Title
        header = QHBoxLayout()
        icon_lbl = QLabel(data["info"].get("icon", "📦"))
        icon_lbl.setStyleSheet("font-size: 32px; border: none;")
        header.addWidget(icon_lbl)

        title_layout = QVBoxLayout()
        name_lbl = QLabel(data["info"].get("name", plugin_id))
        name_lbl.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {Colors.ACCENT_PRIMARY}; border: none;"
        )
        title_layout.addWidget(name_lbl)

        ver_lbl = QLabel(
            f"Version: {data['info'].get('version')}  |  Min Core Required: {data['info'].get('min_core_version', '1.0.0')}"
        )
        ver_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_DISABLED}; border: none;")
        title_layout.addWidget(ver_lbl)
        header.addLayout(title_layout)
        header.addStretch()

        # Verified Badge
        if data.get("is_verified", False):
            badge = QLabel("🛡️ VERIFIED ROOT")
            badge.setStyleSheet(
                f"background: {Colors.ACCENT_SUCCESS}22; color: {Colors.ACCENT_SUCCESS}; font-size: 9px; font-weight: 900; padding: 4px 10px; border-radius: 4px; border: 1px solid {Colors.ACCENT_SUCCESS}44;"
            )
            header.addWidget(badge)

        layout.addLayout(header)

        # Divider
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep)

        # Details Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(15)

        # Description
        desc_title = QLabel("Description")
        desc_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {Colors.FG_PRIMARY}; border: none;"
        )
        scroll_layout.addWidget(desc_title)

        desc_body = QLabel(data["info"].get("description", "No description available."))
        desc_body.setWordWrap(True)
        desc_body.setStyleSheet(
            f"font-size: 12px; color: {Colors.FG_SECONDARY}; border: none; line-height: 1.4;"
        )
        scroll_layout.addWidget(desc_body)

        # Authors
        authors_title = QLabel("Authors & Contributors")
        authors_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {Colors.FG_PRIMARY}; border: none; margin-top: 10px;"
        )
        scroll_layout.addWidget(authors_title)

        authors_data = data["info"].get("authors", [])
        if authors_data and isinstance(authors_data, list):
            for author in authors_data:
                author_card = QWidget()
                author_card.setStyleSheet(
                    f"background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER}; border-radius: 6px;"
                )
                ac_layout = QHBoxLayout(author_card)
                ac_layout.setContentsMargins(12, 12, 12, 12)
                ac_layout.setSpacing(12)

                # Visual avatar fallback circle
                avatar_lbl = QLabel()
                avatar_lbl.setFixedSize(36, 36)
                initials = get_initials(author.get("name", "Unknown"))
                gradient = get_developer_gradient_css(author.get("name", "Unknown"))
                avatar_lbl.setText(initials)
                avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                avatar_lbl.setStyleSheet(f"""
                    border-radius: 18px;
                    background: {gradient};
                    color: #ffffff;
                    font-size: 11px;
                    font-weight: 800;
                    border: 1px solid {Colors.BORDER};
                """)
                ac_layout.addWidget(avatar_lbl)

                text_layout = QVBoxLayout()
                name_role = QHBoxLayout()
                a_name = QLabel(author.get("name", "Unknown"))
                a_name.setStyleSheet(
                    f"font-size: 12px; font-weight: 800; color: {Colors.ACCENT_PRIMARY}; border: none;"
                )
                a_role = QLabel(f"({author.get('role', 'Developer')})")
                a_role.setStyleSheet(
                    f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;"
                )
                name_role.addWidget(a_name)
                name_role.addWidget(a_role)
                name_role.addStretch()
                text_layout.addLayout(name_role)

                if author.get("details"):
                    a_details = QLabel(author["details"])
                    a_details.setWordWrap(True)
                    a_details.setStyleSheet(
                        f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;"
                    )
                    text_layout.addWidget(a_details)

                if author.get("github"):
                    a_git = QLabel(f"GitHub: {author['github']}")
                    a_git.setStyleSheet(
                        f"font-size: 11px; color: {Colors.DNA_PRIMARY}; border: none;"
                    )
                    text_layout.addWidget(a_git)

                ac_layout.addLayout(text_layout)
                scroll_layout.addWidget(author_card)
        else:
            # Try to lookup author_id in the DeveloperProfileDatabase
            author_id = data["info"].get("author_id", data["info"].get("author"))
            dev_profile = None
            if author_id:
                try:
                    from biopro.core.developer_database import DeveloperProfileDatabase

                    db = DeveloperProfileDatabase()
                    dev_profile = db.get_profile(author_id)
                except Exception:
                    pass

            if dev_profile and dev_profile.get("name"):
                author_card = QWidget()
                author_card.setStyleSheet(
                    f"background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER}; border-radius: 6px;"
                )
                ac_layout = QHBoxLayout(author_card)
                ac_layout.setContentsMargins(12, 12, 12, 12)
                ac_layout.setSpacing(12)

                avatar_lbl = QLabel()
                avatar_lbl.setFixedSize(36, 36)

                cached_avatar = None
                avatar_dir = Path.home() / ".biopro" / "avatars"
                if avatar_dir.exists():
                    for ext in ["png", "jpg", "jpeg", "webp", "JPEG", "PNG", "JPG"]:
                        candidate = avatar_dir / f"{author_id}.{ext}"
                        if candidate.exists():
                            cached_avatar = candidate
                            break

                if cached_avatar:
                    pixmap = QPixmap(str(cached_avatar))
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(
                            36,
                            36,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        avatar_lbl.setPixmap(pixmap)
                        avatar_lbl.setStyleSheet(
                            f"border-radius: 18px; border: 1px solid {Colors.BORDER};"
                        )
                    else:
                        cached_avatar = None

                if not cached_avatar:
                    initials = get_initials(dev_profile.get("name", author_id))
                    gradient = get_developer_gradient_css(author_id)
                    avatar_lbl.setText(initials)
                    avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    avatar_lbl.setStyleSheet(f"""
                        border-radius: 18px;
                        background: {gradient};
                        color: #ffffff;
                        font-size: 11px;
                        font-weight: 800;
                        border: 1px solid {Colors.BORDER};
                    """)

                ac_layout.addWidget(avatar_lbl)

                text_layout = QVBoxLayout()
                name_role = QHBoxLayout()
                a_name = QLabel(dev_profile.get("name", author_id))
                a_name.setStyleSheet(
                    f"font-size: 12px; font-weight: 800; color: {Colors.ACCENT_PRIMARY}; border: none;"
                )
                a_role = QLabel(f"({dev_profile.get('role', 'Developer')})")
                a_role.setStyleSheet(
                    f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;"
                )
                name_role.addWidget(a_name)
                name_role.addWidget(a_role)
                name_role.addStretch()
                text_layout.addLayout(name_role)

                if dev_profile.get("description"):
                    a_desc = QLabel(dev_profile["description"])
                    a_desc.setWordWrap(True)
                    a_desc.setStyleSheet(
                        f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;"
                    )
                    text_layout.addWidget(a_desc)

                ac_layout.addLayout(text_layout)
                scroll_layout.addWidget(author_card)
            else:
                legacy_name = author_id if author_id else "Community Contributor"
                lbl = QLabel(f"👤 {legacy_name}")
                lbl.setStyleSheet(f"font-size: 12px; color: {Colors.FG_SECONDARY}; border: none;")
                scroll_layout.addWidget(lbl)

        # Security Status Panel
        sec_title = QLabel("Security & Gating Verification")
        sec_title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {Colors.FG_PRIMARY}; border: none; margin-top: 10px;"
        )
        scroll_layout.addWidget(sec_title)

        status_card = QWidget()
        status_card.setStyleSheet(
            f"background: {Colors.BG_MEDIUM}; border: 1px solid {Colors.BORDER}; border-radius: 6px;"
        )
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(12, 12, 12, 12)
        sc_layout.setSpacing(6)

        if data.get("is_verified", False):
            sc_layout.addWidget(QLabel("🛡️ Verification: Cryptographically Verified"))
            sc_layout.addWidget(QLabel(f"Publisher Identity ID: {data['info'].get('author_id')}"))
            sc_layout.addWidget(
                QLabel("Consensus Validation: Green (Fully trusted co-signing chain present)")
            )
        else:
            sc_layout.addWidget(QLabel("⚠️ Verification: Self-Signed / Local Registry Key Only"))
            sc_layout.addWidget(
                QLabel("Consensus Validation: Yellow (Developer key verified, not signed by root)")
            )

        for i in range(sc_layout.count()):
            item = sc_layout.itemAt(i)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;")

        scroll_layout.addWidget(status_card)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Bottom Actions Row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = SecondaryButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class StoreLoaderWorker(QThread):
    finished = pyqtSignal(dict, list, str)

    def __init__(self, updater, filter_type, parent=None):
        super().__init__(parent)
        self.updater = updater
        self.filter_type = filter_type

    def run(self):
        inventory = {}
        trusted_devs = []
        try:
            if self.filter_type == "developers":
                trusted_devs = self.updater.fetch_remote_developers()
                if not trusted_devs:
                    remote_data = self.updater.fetch_remote_registry(self.updater.registry_url)
                    if remote_data:
                        trusted_devs = remote_data.get("trusted_developers", [])
                if not trusted_devs:
                    try:
                        from biopro.core.developer_database import DeveloperProfileDatabase

                        db = DeveloperProfileDatabase()
                        trusted_devs = list(db.profiles.values())
                    except Exception:
                        pass

                # Scan local manual keys
                manual_keys_dir = Path.home() / ".biopro" / "trusted_roots"
                known_dev_ids = {d.get("developer_id") for d in trusted_devs if "developer_id" in d}
                if manual_keys_dir.exists():
                    for key_file in manual_keys_dir.glob("manual_*.pub"):
                        dev_id = key_file.stem.replace("manual_", "")
                        if dev_id not in known_dev_ids:
                            try:
                                with open(key_file) as f:
                                    pub_key_hex = f.read().strip()
                                trusted_devs.append(
                                    {
                                        "developer_id": dev_id,
                                        "public_key": pub_key_hex,
                                        "name": f"Developer '{dev_id}'",
                                        "role": "Manually Trusted Local Exception",
                                        "is_manual": True,
                                    }
                                )
                            except Exception:
                                pass
            else:
                inventory = self.updater.evaluate_store_state()
        except Exception:
            pass

        self.finished.emit(inventory, trusted_devs, self.filter_type)


class PluginStoreDialog(QDialog):
    def __init__(self, module_manager: ModuleManager, updater: NetworkUpdater, parent=None):
        super().__init__(parent)
        self.module_manager = module_manager
        self.updater = updater
        self.filter_list = None
        self.scroll_area = None

        self.setWindowTitle("Marketplace")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        self.setObjectName("PluginStoreDialog")

        self._setup_ui()
        self._load_store_data()

        # Tutorial overlay for when the store is open
        from biopro.ui.wizards.tutorial_overlay import TutorialOverlay

        self.tutorial_overlay = TutorialOverlay(self)
        self.tutorial_overlay.hide()
        self.tutorial_overlay.btn_next.clicked.connect(self._on_tutorial_next)
        self.tutorial_overlay.btn_close.clicked.connect(self._on_tutorial_skip)

        # If a tutorial is already active (e.g. STORE_OPENED just fired), render it now
        from biopro.core.tutorial_manager import global_tutorial_manager

        if global_tutorial_manager.current_step:
            self.tutorial_overlay.render_step(global_tutorial_manager.current_step)

        # Subscribe to the nervous system
        event_bus.subscribe(BioProEvent.PLUGIN_INSTALLED, self._on_plugin_event)
        event_bus.subscribe(BioProEvent.PLUGIN_REMOVED, self._on_plugin_event)

    def _on_tutorial_next(self) -> None:
        from biopro.core.models.tutorial_models import BranchingStep
        from biopro.core.tutorial_manager import global_tutorial_manager

        step = global_tutorial_manager.current_step
        if step and isinstance(step, BranchingStep):
            first_target = next(iter(step.options.values()), None)
            if first_target == "__complete__":
                global_tutorial_manager.complete_course()
                global_tutorial_manager.current_step = None
                global_tutorial_manager._emit_step_changed()
            elif first_target:
                global_tutorial_manager.next_step(first_target)
            return

        if step and getattr(step, "next_step_id", None):
            global_tutorial_manager.next_step(step.next_step_id)

    def _on_tutorial_skip(self) -> None:
        from biopro.core.tutorial_manager import global_tutorial_manager

        global_tutorial_manager.end_tutorial()

    def _on_plugin_event(self, _id: str):
        """React to external plugin changes."""
        self._load_store_data()

    def closeEvent(self, event):
        """Cleanup subscriptions on close."""
        event_bus.unsubscribe(BioProEvent.PLUGIN_INSTALLED, self._on_plugin_event)
        event_bus.unsubscribe(BioProEvent.PLUGIN_REMOVED, self._on_plugin_event)
        super().closeEvent(event)

    def _setup_ui(self):
        self.setMinimumSize(1000, 650)
        self.resize(1100, 750)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Top Search & Header Bar ---
        header_banner = QWidget()
        header_banner.setFixedHeight(50)  # SLIMMER HEADER
        header_banner.setStyleSheet(
            f"background-color: {Colors.BG_MEDIUM}; border-bottom: 1px solid {Colors.BORDER};"
        )
        header_layout = QHBoxLayout(header_banner)
        header_layout.setContentsMargins(20, 0, 20, 0)

        header_title = QLabel("☁️ Marketplace")
        header_title.setStyleSheet(
            f"font-size: 15px; font-weight: 800; color: {Colors.FG_PRIMARY};"
        )
        header_layout.addWidget(header_title)

        header_layout.addStretch()

        self.repair_all_btn = SecondaryButton("Repair All Plugins")
        self.repair_all_btn.clicked.connect(self._repair_all_plugins)
        header_layout.addWidget(self.repair_all_btn)

        header_layout.addSpacing(10)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search plugins by name, tag, or author...")
        self.search_input.setFixedWidth(300)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 5px 12px;
                color: {Colors.FG_PRIMARY};
                font-size: 12px;
            }}
            QLineEdit:focus {{ border: 1px solid {Colors.ACCENT_PRIMARY}; }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)

        layout.addWidget(header_banner)

        # --- Main Splitter (Sidebar | Content) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background: {Colors.BORDER}; }}")

        # 1. Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(210)
        self.sidebar.setStyleSheet(
            f"background: {Colors.BG_DARK}; border-right: 1px solid {Colors.BORDER};"
        )
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 15, 10, 15)
        sidebar_layout.setSpacing(2)

        def add_section_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-size: 10px; font-weight: 800; color: {Colors.FG_DISABLED}; margin-top: 10px; margin-bottom: 5px; margin-left: 5px;"
            )
            sidebar_layout.addWidget(lbl)

        add_section_label("COLLECTIONS")

        self.filter_list = QListWidget()
        self.filter_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filter_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.filter_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {Colors.FG_PRIMARY};
                font-size: 12px;
            }}
            QListWidget::item:selected {{
                background: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
                font-weight: bold;
            }}
            QListWidget::item:hover:!selected {{
                background: {Colors.BG_MEDIUM};
            }}
        """)

        collections = [
            ("All Modules", "all"),
            ("Available Updates", "updates"),
            ("Installed", "installed"),
            ("Trusted Developers", "developers"),
        ]

        for label, data in collections:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.filter_list.addItem(item)

        self.filter_list.setCurrentRow(0)
        self.filter_list.setFixedHeight(140)  # Adjusted height for 4 options
        self.filter_list.currentRowChanged.connect(self._on_filter_changed)
        sidebar_layout.addWidget(self.filter_list)

        sidebar_layout.addStretch()
        self.splitter.addWidget(self.sidebar)

        # 2. Content Area
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.store_grid_widget = QWidget()
        self.store_grid_widget.setStyleSheet("background: transparent;")
        self.store_grid = QGridLayout(self.store_grid_widget)
        self.store_grid.setSizeConstraint(QGridLayout.SizeConstraint.SetMinAndMaxSize)
        self.store_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.store_grid.setContentsMargins(20, 20, 20, 20)
        self.store_grid.setSpacing(20)

        self.scroll_area.setWidget(self.store_grid_widget)
        content_layout.addWidget(self.scroll_area)

        self.splitter.addWidget(self.content_container)
        layout.addWidget(self.splitter)

        # Status Label at Bottom
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; font-weight: bold; padding: 10px; background: {Colors.BG_MEDIUM}; border-top: 1px solid {Colors.BORDER};"
        )
        self.status_lbl.hide()
        layout.addWidget(self.status_lbl)

    def _on_search_changed(self, text: str):
        self._load_store_data()

    def _on_filter_changed(self, row: int):
        self._load_store_data()

    def _load_store_data(self):
        # 1. Clear grid
        for i in reversed(range(self.store_grid.count())):
            item = self.store_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # Get filter from list
        filter_type = "all"
        if self.filter_list is not None and self.filter_list.currentRow() >= 0:
            item = self.filter_list.currentItem()
            if item is not None:
                filter_type = item.data(Qt.ItemDataRole.UserRole)

        # Show Loading state
        loading_lbl = QLabel("⏳ Loading Marketplace...")
        loading_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; font-size: 16px; font-weight: bold;"
        )
        loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.store_grid.addWidget(loading_lbl, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        # Disable inputs
        if self.filter_list is not None:
            self.filter_list.setEnabled(False)
        self.search_input.setEnabled(False)

        # Start background worker
        self.worker = StoreLoaderWorker(self.updater, filter_type, self)
        self.worker.finished.connect(self._on_loader_finished)
        self.worker.start()

    def _on_loader_finished(self, inventory: dict, trusted_devs: list, filter_type: str):
        # Re-enable inputs
        if self.filter_list is not None:
            self.filter_list.setEnabled(True)
        self.search_input.setEnabled(True)

        # Clear loading label
        for i in reversed(range(self.store_grid.count())):
            item = self.store_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        # 2. If Developer Dashboard is selected
        if filter_type == "developers":
            for i, dev in enumerate(trusted_devs):
                row, col = i // 2, i % 2
                card = self._create_developer_card(dev)
                self.store_grid.addWidget(card, row, col)
            self.store_grid_widget.adjustSize()
            return

        # 3. Handle Normal Inventory
        if not inventory:
            self.store_grid.addWidget(QLabel("Could not connect to the cloud registry."), 0, 0)
            return

        # 4. Apply Filters
        search_text = self.search_input.text().lower()

        filtered_items = []
        for plugin_id, data in inventory.items():
            mod_data = data["info"]
            state = data["state"]
            # Search Filter
            match_search = (
                search_text in plugin_id.lower()
                or search_text in mod_data.get("name", "").lower()
                or search_text in mod_data.get("description", "").lower()
                or search_text in mod_data.get("author", "").lower()
            )
            if not match_search:
                continue

            # Sidebar Filter
            if filter_type == "updates" and state != "UPDATE":
                continue
            if filter_type == "installed" and not data.get("local_version"):
                continue

            filtered_items.append((plugin_id, data))

        # 4. Populate Grid (2 columns for better readability)
        for i, (plugin_id, data) in enumerate(filtered_items):
            row, col = i // 2, i % 2
            card = self._create_store_card(plugin_id, data)
            self.store_grid.addWidget(card, row, col)
        self.store_grid_widget.adjustSize()

    def _create_store_card(self, plugin_id: str, data: dict):
        mod_data = data["info"]
        state = data["state"]
        local_ver = data["local_version"]
        is_verified = data.get("is_verified", False)

        card = ModuleCard()  # Base styling
        card.setObjectName("StoreModuleCard")
        card.setProperty("tutorial_id", f"store_card_{plugin_id}")
        card.setMinimumWidth(350)

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Header: Icon and Name
        header = QHBoxLayout()
        icon_lbl = QLabel(mod_data.get("icon", "📦"))
        icon_lbl.setStyleSheet("font-size: 24px;")
        header.addWidget(icon_lbl)

        name_layout = QVBoxLayout()
        name_lbl = QLabel(mod_data.get("name", "Unknown"))
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; border: none;")
        name_layout.addWidget(name_lbl)

        authors_data = mod_data.get("authors", [])
        if authors_data and isinstance(authors_data, list):
            names = [a.get("name", "Unknown") for a in authors_data]
            author_text = f"by {', '.join(names)}"
        else:
            # Fallback to single author / author_id lookup in database
            author_text = None
            author_id = mod_data.get("author_id")
            if author_id:
                try:
                    from biopro.core.developer_database import DeveloperProfileDatabase

                    db = DeveloperProfileDatabase()
                    dev_profile = db.get_profile(author_id)
                    author_text = (
                        f"by {dev_profile.get('name', dev_profile.get('developer_id', author_id))}"
                    )
                except Exception:
                    author_text = f"by {author_id}"
            if not author_text:
                author_text = f"by {mod_data.get('author', 'Community')}"

        author_lbl = QLabel(author_text)
        author_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;")
        name_layout.addWidget(author_lbl)
        header.addLayout(name_layout)
        header.addStretch()

        # Badge for Verified
        if is_verified:
            badge = QLabel("🛡️ VERIFIED")
            badge.setStyleSheet(
                f"background: {Colors.ACCENT_SUCCESS}22; color: {Colors.ACCENT_SUCCESS}; font-size: 9px; font-weight: 900; padding: 4px 8px; border-radius: 4px; border: 1px solid {Colors.ACCENT_SUCCESS}44;"
            )
            header.addWidget(badge)

        main_layout.addLayout(header)

        # Description (Fixed height to prevent jumping)
        desc = QLabel(mod_data.get("description", ""))
        desc.setWordWrap(True)
        desc.setFixedHeight(40)  # 2 lines roughly
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; border: none; font-size: 12px;")
        main_layout.addWidget(desc)

        # Metadata / Actions Row
        bottom_row = QHBoxLayout()

        ver_info = f"v{mod_data.get('version')}"
        if local_ver and local_ver != mod_data.get("version"):
            ver_info = f"v{local_ver} ➔ v{mod_data.get('version')}"

        ver_lbl = QLabel(ver_info)
        ver_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_DISABLED}; border: none;")
        bottom_row.addWidget(ver_lbl)
        bottom_row.addStretch()

        # Add Details button before the dynamic actions
        details_btn = SecondaryButton("Details")
        details_btn.clicked.connect(lambda: self._view_plugin_details(plugin_id, data))
        bottom_row.addWidget(details_btn)

        # Dynamic Actions
        if state == "INCOMPATIBLE":
            btn = SecondaryButton("Incompatible")
            btn.setToolTip(f"Requires core v{mod_data.get('min_core_version')}")
            btn.setEnabled(False)
            bottom_row.addWidget(btn)
        elif state == "INSTALL":
            btn = PrimaryButton("Install")
            btn.clicked.connect(lambda: self._install_module(plugin_id, mod_data))
            bottom_row.addWidget(btn)
        elif state == "UPDATE":
            upd_btn = PrimaryButton("Update")
            upd_btn.clicked.connect(lambda: self._install_module(plugin_id, mod_data))

            rm_btn = DangerButton("×")
            rm_btn.setToolTip("Remove Plugin")
            rm_btn.setFixedSize(30, 30)
            rm_btn.clicked.connect(lambda: self._remove_module(plugin_id))

            repair_btn = SecondaryButton("Repair")
            repair_btn.setToolTip("Diagnose & Repair")
            repair_btn.clicked.connect(lambda: self._view_plugin_diagnostics(plugin_id, data))

            bottom_row.addWidget(repair_btn)
            bottom_row.addWidget(rm_btn)
            bottom_row.addWidget(upd_btn)
        elif state == "UP_TO_DATE":
            ok_lbl = QLabel("✓ Installed")
            ok_lbl.setStyleSheet(
                f"color: {Colors.ACCENT_SUCCESS}; font-size: 11px; font-weight: bold; margin-right: 5px;"
            )
            bottom_row.addWidget(ok_lbl)

            repair_btn = SecondaryButton("Repair")
            repair_btn.setToolTip("Diagnose & Repair")
            repair_btn.clicked.connect(lambda: self._view_plugin_diagnostics(plugin_id, data))
            bottom_row.addWidget(repair_btn)

            rm_btn = DangerButton("Remove")
            rm_btn.clicked.connect(lambda: self._remove_module(plugin_id))
            bottom_row.addWidget(rm_btn)

        main_layout.addLayout(bottom_row)

        # Add Context Menu for Diagnose & Repair if installed
        if state in ["UP_TO_DATE", "UPDATE", "INCOMPATIBLE"]:
            card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, pid=plugin_id, pd=data: self._show_card_context_menu(card, pos, pid, pd)
            )

        return card

    def _show_card_context_menu(self, card, pos, plugin_id: str, data: dict):
        menu = QMenu(self)
        menu.setStyleSheet(f"background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_PRIMARY};")

        repair_action = menu.addAction("🛠️ Diagnose & Repair")
        repair_action.triggered.connect(lambda: self._view_plugin_diagnostics(plugin_id, data))

        menu.exec(card.mapToGlobal(pos))

    def _view_plugin_diagnostics(self, plugin_id: str, data: dict):
        from biopro.ui.dialogs.plugin_doctor_dialog import PluginDoctorDialog

        plugin_dir = self.updater.plugin_dir / plugin_id
        dialog = PluginDoctorDialog(plugin_id, plugin_dir, self.updater, parent=self)
        dialog.exec()

        # Refresh the store UI to reflect any repairs made
        self._load_store_data()

    def _repair_all_plugins(self):
        from biopro.ui.dialogs.plugin_doctor_dialog import PluginDoctorDialog

        inventory = self.updater.evaluate_store_state()
        installed_plugins = {
            pid: data
            for pid, data in inventory.items()
            if data["state"] in ["UP_TO_DATE", "UPDATE", "INCOMPATIBLE"]
        }

        if not installed_plugins:
            QMessageBox.information(self, "Repair All", "No installed plugins found to repair.")
            return

        for pid, _data in installed_plugins.items():
            plugin_dir = self.updater.plugin_dir / pid
            dialog = PluginDoctorDialog(pid, plugin_dir, self.updater, parent=self)
            dialog.exec()

        # Refresh the store UI to reflect any repairs made
        self._load_store_data()

    def _install_module(self, plugin_id: str, mod_data: dict):
        """Uses the Logic Engine to install the plugin and update the tracker."""
        from PyQt6.QtWidgets import QApplication

        # Briefly show the user that something is happening
        self.status_lbl.setText(f"Installing {mod_data.get('name')}...")
        self.status_lbl.show()
        QApplication.processEvents()  # Forces the UI to visually update immediately

        # Let the NetworkUpdater handle the download AND the json tracking
        success, msg = self.updater.install_plugin(plugin_id, mod_data)

        self.status_lbl.hide()

        if success:
            from biopro.ui.dialogs.dependency_installer_dialog import DependencyInstallerDialog

            plugin_dir = self.updater.plugin_dir / plugin_id
            plugin_name = mod_data.get("name", plugin_id)

            installer = DependencyInstallerDialog(plugin_dir, plugin_name, parent=self)
            installer.exec()

            # We no longer need to call self._load_store_data() here!
            # The Event Bus will fire and we will catch it in _on_plugin_event.
            pass
        else:
            QMessageBox.critical(self, "Installation Failed", msg)

    def _remove_module(self, plugin_id: str):
        success, msg = self.updater.remove_plugin(plugin_id)
        if not success:
            QMessageBox.critical(self, "Error", msg)

    def _view_plugin_details(self, plugin_id: str, data: dict):
        """Displays detailed V2 meta inspection dialog."""
        event_bus.emit(BioProEvent.STORE_MODULE_DETAILS_OPENED)
        dialog = PluginDetailsDialog(plugin_id, data, self)
        dialog.exec()

    def _create_developer_card(self, dev: dict):
        """Renders a verified trusted developer card with dynamic JPG/PNG avatars."""
        dev_id = dev.get("developer_id", "Unknown")
        pub_key = dev.get("public_key", "")

        # Rich local default cache fallback profiles
        DEFAULT_DEV_INFO = {
            "Kalaimaran": {
                "name": "Kalaimaran Balasothy",
                "role": "Founder & Lead Architect",
                "description": "Creator of the BioPro platform. Leading secure high-performance data analytics and pipeline automation.",
                "avatar": "👨‍💻",
            }
        }

        dev_info = DEFAULT_DEV_INFO.get(
            dev_id,
            {
                "name": dev.get("name", f"Developer '{dev_id}'"),
                "role": dev.get("role", "Verified Contributor"),
                "description": dev.get(
                    "description",
                    "Verified independent developer contributing safe computational plugins to BioPro.",
                ),
                "avatar": dev.get("avatar", "👤"),
            },
        )

        card = ModuleCard()
        card.setMinimumWidth(350)

        main_layout = QVBoxLayout(card)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Header: Avatar/Icon and Name
        header = QHBoxLayout()

        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(32, 32)

        # 1. Search for cached JPG/PNG image binaries
        cached_avatar = None
        avatar_dir = Path.home() / ".biopro" / "avatars"
        if avatar_dir.exists():
            for ext in ["png", "jpg", "jpeg", "webp"]:
                candidate = avatar_dir / f"{dev_id}.{ext}"
                if candidate.exists():
                    cached_avatar = candidate
                    break

        # 2. Render cached image or fall back to analogous radial gradients
        if cached_avatar:
            pixmap = QPixmap(str(cached_avatar))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    32,
                    32,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                avatar_lbl.setPixmap(pixmap)
                avatar_lbl.setStyleSheet(f"border-radius: 16px; border: 1px solid {Colors.BORDER};")
            else:
                cached_avatar = None

        if not cached_avatar:
            initials = get_initials(dev_info.get("name", dev_id))
            gradient = get_developer_gradient_css(dev_id)
            avatar_lbl.setText(initials)
            avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_lbl.setStyleSheet(f"""
                border-radius: 16px;
                background: {gradient};
                color: #ffffff;
                font-size: 11px;
                font-weight: 800;
                border: 1px solid {Colors.BORDER};
            """)

        header.addWidget(avatar_lbl)

        name_layout = QVBoxLayout()
        name_lbl = QLabel(dev_info.get("name", dev_id))
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 800; border: none;")
        name_layout.addWidget(name_lbl)

        role_lbl = QLabel(dev_info.get("role", "Verified Developer"))
        role_lbl.setStyleSheet(f"font-size: 11px; color: {Colors.FG_SECONDARY}; border: none;")
        name_layout.addWidget(role_lbl)

        header.addLayout(name_layout)
        header.addStretch()

        # Badge for Verified Status
        is_manual = dev.get("is_manual", False)
        if is_manual:
            badge = QLabel("⚠️ MANUAL OVERRIDE")
            badge.setStyleSheet(
                f"background: {Colors.ACCENT_WARNING}22; color: {Colors.ACCENT_WARNING}; font-size: 9px; font-weight: 900; padding: 4px 8px; border-radius: 4px; border: 1px solid {Colors.ACCENT_WARNING}44;"
            )
        else:
            badge = QLabel("🛡️ TRUSTED")
            badge.setStyleSheet(
                f"background: {Colors.ACCENT_SUCCESS}22; color: {Colors.ACCENT_SUCCESS}; font-size: 9px; font-weight: 900; padding: 4px 8px; border-radius: 4px; border: 1px solid {Colors.ACCENT_SUCCESS}44;"
            )
        header.addWidget(badge)

        main_layout.addLayout(header)

        # Description
        desc = QLabel(dev_info.get("description", ""))
        desc.setWordWrap(True)
        desc.setFixedHeight(40)
        desc.setStyleSheet(f"color: {Colors.FG_SECONDARY}; border: none; font-size: 11px;")
        main_layout.addWidget(desc)

        # Footer: Public Key Fingerprint
        bottom_row = QHBoxLayout()
        fp = pub_key[:8] + "..." + pub_key[-8:] if len(pub_key) > 16 else pub_key
        key_lbl = QLabel(f"Fingerprint: {fp}")
        key_lbl.setStyleSheet(f"font-size: 10px; color: {Colors.FG_DISABLED}; border: none;")
        bottom_row.addWidget(key_lbl)
        bottom_row.addStretch()

        path_btn = SecondaryButton("Trust Path")
        path_btn.setStyleSheet("padding: 3px 8px; font-size: 10px; margin-right: 5px;")
        path_btn.clicked.connect(
            lambda: self._show_trust_path(dev_id, dev_info.get("name", dev_id), pub_key)
        )
        bottom_row.addWidget(path_btn)

        copy_btn = SecondaryButton("Copy Key")
        copy_btn.setStyleSheet("padding: 3px 8px; font-size: 10px;")
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(pub_key))
        bottom_row.addWidget(copy_btn)

        if is_manual:
            revoke_btn = DangerButton("Revoke")
            revoke_btn.setStyleSheet("padding: 3px 8px; font-size: 10px; margin-left: 5px;")
            revoke_btn.clicked.connect(lambda: self._revoke_manual_trust(dev_id))
            bottom_row.addWidget(revoke_btn)

        main_layout.addLayout(bottom_row)
        return card

    def _show_trust_path(self, dev_id: str, name: str, pub_key: str):
        """Displays the cryptographic TrustPath Dialog for this developer."""
        dialog = TrustPathDialog(dev_id, name, pub_key, self)
        dialog.exec()

    def _revoke_manual_trust(self, dev_id: str):
        reply = QMessageBox.question(
            self,
            "Revoke Trust",
            f"Are you sure you want to revoke manual trust for {dev_id}?\n\nPlugins signed by this developer will no longer load.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            key_file = Path.home() / ".biopro" / "trusted_roots" / f"manual_{dev_id}.pub"
            if key_file.exists():
                try:
                    key_file.unlink()
                    self.status_lbl.setText(f"Revoked trust for {dev_id}.")
                    self.status_lbl.show()
                    QTimer.singleShot(2000, self.status_lbl.hide)
                    self._load_store_data()  # Reload the view
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to remove key file: {e}")

    def _copy_to_clipboard(self, text: str):
        """Helper to copy authority keys to system clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        self.status_lbl.setText("Copied public key to clipboard! ✅")
        self.status_lbl.show()
        QTimer.singleShot(2000, self.status_lbl.hide)

    def _remove_module(self, plugin_id: str):
        success, msg = self.updater.remove_plugin(plugin_id)
        if not success:
            QMessageBox.critical(self, "Error", msg)


def get_initials(name: str | None) -> str:
    """Extracts initials from a developer's full name (e.g. John Doe -> JD)."""
    if not name:
        return "?"
    parts = [p.strip() for p in name.split() if p.strip()]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def get_developer_gradient_css(dev_id: str | None) -> str:
    """Deterministic, hand-curated premium radial color gradients for circular fallbacks."""
    if not dev_id:
        return "qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #424242, stop:1 #212121)"

    import hashlib

    h = int(hashlib.md5(dev_id.encode()).hexdigest(), 16)

    # Selection of curated analogous deep dark tech gradients
    gradients = [
        "stop:0 #00F0FF, stop:1 #00363A",  # Cyber Neon Cyan
        "stop:0 #D500F9, stop:1 #311B92",  # Purple Aurora
        "stop:0 #FF6D00, stop:1 #4E1500",  # Solar Ember
        "stop:0 #AEEA00, stop:1 #1B5E20",  # Acid Lime
        "stop:0 #2979FF, stop:1 #0D47A1",  # Electric Blue
        "stop:0 #FF1744, stop:1 #5C0010",  # Crimson Ember
        "stop:0 #00E676, stop:1 #002D15",  # Deep Emerald
        "stop:0 #FFD600, stop:1 #3E2723",  # Royal Gold
    ]

    selected = gradients[h % len(gradients)]
    return f"qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, {selected})"
