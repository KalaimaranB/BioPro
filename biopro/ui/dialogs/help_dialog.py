import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QSplitter, QFrame, QPushButton
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import Qt, QUrl, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QObject
from biopro.ui.theme import Colors, Fonts
import re
import markdown
from pygments.formatters import HtmlFormatter

logger = logging.getLogger(__name__)

class RenderSignals(QObject):
    """Bridge for background rendering thread to send HTML back to UI."""
    finished = pyqtSignal(str, str) # file_path_str, html_body

class RenderWorker(QRunnable):
    """Offloads Markdown/Math processing to a background thread."""
    def __init__(self, file_path_str: str):
        super().__init__()
        self.file_path_str = file_path_str
        self.signals = RenderSignals()

    @pyqtSlot()
    def run(self):
        try:
            file_path = Path(self.file_path_str)
            with open(file_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            # Pre-processing (Alerts, Mermaid)
            alert_map = {"TIP": "tip", "NOTE": "note", "IMPORTANT": "important", "WARNING": "warning", "CAUTION": "caution"}
            for github_tag, extension_tag in alert_map.items():
                pattern = rf'^>\s*\[!{github_tag}\]\s*'
                md_content = re.sub(pattern, f'!!! {extension_tag}\n    ', md_content, flags=re.MULTILINE)
            
            mermaid_pattern = re.compile(r'```mermaid\s+(.*?)```', re.DOTALL)
            md_content = mermaid_pattern.sub(r'<div class="mermaid">\1</div>', md_content)
            
            # Rendering
            html_body = markdown.markdown(md_content, extensions=['fenced_code', 'tables', 'codehilite', 'admonition'])
            self.signals.finished.emit(self.file_path_str, html_body)
        except Exception as e:
            logger.error(f"Async Render Error: {e}")
            self.signals.finished.emit(self.file_path_str, f"<h3>Error</h3><p>{e}</p>")

class HelpPage(QWebEnginePage):
    """Custom page to intercept links and prevent navigation crashes."""
    def __init__(self, dialog, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dialog = dialog
        
    def acceptNavigationRequest(self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool) -> bool:
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            url_str = url.toString()
            if url_str.endswith(".md"):
                self.dialog.navigate_to_md(url.fileName())
                return False
        return True

class HelpCenterDialog(QDialog):
    """Categorized documentation viewer with async rendering and caching."""
    
    def __init__(self, module_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BioPro Help Center")
        self.setMinimumSize(1100, 800)
        self.setStyleSheet(f"background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY};")
        
        self.module_manager = module_manager
        self.docs_dir = Path(__file__).parents[3] / "docs"
        self.lookup_table = {} 
        self.render_cache = {}    # file_path_str -> html_body
        self.thread_pool = QThreadPool.globalInstance()
        
        self._setup_ui()
        self._load_topics()
        self._select_initial_topic()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top Bar
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet(f"background: {Colors.BG_DARK}; border-bottom: 1px solid {Colors.BORDER};")
        top_layout = QHBoxLayout(top_bar)
        
        title = QLabel("📖 BioPro Documentation")
        title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {Colors.ACCENT_PRIMARY};")
        top_layout.addWidget(title)
        top_layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { border: none; font-size: 18px; } QPushButton:hover { color: white; }")
        close_btn.clicked.connect(self.close)
        top_layout.addWidget(close_btn)
        
        layout.addWidget(top_bar)
        
        # Main Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {Colors.BORDER}; }}")
        
        # Sidebar
        self.tree = QTreeWidget()
        self.tree.setFixedWidth(280)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{ background: {Colors.BG_DARK}; border: none; padding: 10px; font-size: 13px; }}
            QTreeWidget::item {{ padding: 8px 5px; color: {Colors.FG_SECONDARY}; border-radius: 4px; }}
            QTreeWidget::item:selected {{ background: {Colors.BG_MEDIUM}; color: {Colors.ACCENT_PRIMARY}; font-weight: bold; }}
            QTreeWidget::item:hover {{ background: {Colors.BG_LIGHT}; }}
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)
        splitter.addWidget(self.tree)
        
        # Content Area
        self.viewer = QWebEngineView()
        self.viewer.setPage(HelpPage(self, self.viewer)) 
        self.viewer.setStyleSheet(f"background: {Colors.BG_DARKEST};")
        
        # Optmization: Speed up WebEngine
        settings = self.viewer.settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.ScrollAnimatorEnabled, True)
        settings.setAttribute(settings.WebAttribute.ErrorPageEnabled, False)
        
        self.viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        splitter.addWidget(self.viewer)
        layout.addWidget(splitter)

    def _load_topics(self):
        """Build hierarchical categories."""
        categories = {
            "Getting Started": ["01", "02", "12", "13", "14"],
            "How It Works": ["07", "08", "09", "10", "11"],
            "For Developers": ["03", "04", "05", "06"]
        }
        
        font = self.tree.font()
        font.setBold(True)
        font.setPointSize(11)

        self.groups = {}
        for cat in categories.keys():
            group = QTreeWidgetItem(self.tree, [cat])
            group.setFlags(group.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            group.setForeground(0, Qt.GlobalColor.gray)
            group.setFont(0, font)
            self.groups[cat] = group
            group.setExpanded(True)

        self.plugin_group = QTreeWidgetItem(self.tree, ["Plugin Manuals"])
        self.plugin_group.setFlags(self.plugin_group.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.plugin_group.setForeground(0, Qt.GlobalColor.gray)
        self.plugin_group.setFont(0, font)

        if self.docs_dir.exists():
            for f in sorted(list(self.docs_dir.glob("*.md"))):
                name = f.stem
                prefix = name[:2]
                target_group = self.groups["Getting Started"]
                for cat, prefixes in categories.items():
                    if prefix in prefixes:
                        target_group = self.groups[cat]
                        break
                
                display_name = name.split("_", 1)[1].replace("_", " ") if "_" in name else name
                item = QTreeWidgetItem(target_group, [f"• {display_name}"])
                item.setData(0, Qt.ItemDataRole.UserRole, str(f))
                self.lookup_table[f.name] = item

        if self.module_manager:
            found_plugins = False
            for mod_id, mod_info in self.module_manager.modules.items():
                plugin_docs = mod_info["path"] / "docs"
                if plugin_docs.exists():
                    found_plugins = True
                    manifest = mod_info["manifest"]
                    plugin_root = QTreeWidgetItem(self.plugin_group, [f"📦 {manifest.get('name', mod_id)}"])
                    plugin_root.setFlags(plugin_root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                    for doc_f in sorted(list(plugin_docs.glob("*.md"))):
                        doc_item = QTreeWidgetItem(plugin_root, [doc_f.stem.replace("_", " ")])
                        doc_item.setData(0, Qt.ItemDataRole.UserRole, str(doc_f))
                        self.lookup_table[doc_f.name] = doc_item
            
            if not found_plugins: self.plugin_group.setHidden(True)
            else: self.plugin_group.setExpanded(True)
        else:
            self.plugin_group.setHidden(True)

    def _select_initial_topic(self):
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            if group.childCount() > 0:
                first_doc = group.child(0)
                if first_doc.childCount() > 0: first_doc = first_doc.child(0)
                self.tree.setCurrentItem(first_doc)
                self._on_item_clicked(first_doc)
                break

    def navigate_to_md(self, filename: str):
        if filename in self.lookup_table:
            item = self.lookup_table[filename]
            self.tree.setCurrentItem(item)
            self._on_item_clicked(item)

    def _on_item_clicked(self, item: QTreeWidgetItem):
        """Triggers the async rendering flow."""
        file_path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path_str: return
        
        # 1. Check Cache
        if file_path_str in self.render_cache:
            self._finalize_render(file_path_str, self.render_cache[file_path_str])
            return

        # 2. Show Loading State
        loading_html = f"<html><body style='background:{Colors.BG_DARKEST};color:{Colors.FG_SECONDARY};display:flex;justify-content:center;align-items:center;height:90vh;font-family:sans-serif;'><div><h2>⏳ Preparing Scientific Manual...</h2></div></body></html>"
        self.viewer.setHtml(loading_html)

        # 3. Offload to Thread Pool
        worker = RenderWorker(file_path_str)
        worker.signals.finished.connect(self._on_render_finished)
        self.thread_pool.start(worker)

    def _on_render_finished(self, file_path_str: str, html_body: str):
        """Callback from background thread."""
        self.render_cache[file_path_str] = html_body
        # Only update if the user hasn't switched to another file already
        current_item = self.tree.currentItem()
        if current_item and current_item.data(0, Qt.ItemDataRole.UserRole) == file_path_str:
            self._finalize_render(file_path_str, html_body)

    def _finalize_render(self, file_path_str: str, html_body: str):
        """Final UI assembly on the main thread."""
        file_path = Path(file_path_str)
        pygments_css = HtmlFormatter(style='monokai').get_style_defs('.codehilite')
        assets_path = Path(__file__).parents[1] / "assets"
        mermaid_lib = QUrl.fromLocalFile(str(assets_path / "mermaid.min.js")).toString()
        base_url = QUrl.fromLocalFile(str(file_path.parent) + "/")

        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
            <script src="{mermaid_lib}"></script>
            <style>
                {pygments_css}
                body {{ background: {Colors.BG_DARKEST}; color: {Colors.FG_PRIMARY}; font-family: sans-serif; line-height: 1.7; padding: 40px; max-width: 900px; margin: 0 auto; }}
                h1 {{ color: {Colors.ACCENT_PRIMARY}; border-bottom: 2px solid {Colors.BORDER}; padding-bottom: 0.3em; }}
                .codehilite {{ background: {Colors.BG_MEDIUM}; padding: 16px; border-radius: 8px; }}
                .mermaid {{ background: #ffffff0a; border-radius: 8px; padding: 20px; margin: 2em 0; display: flex; justify-content: center; }}
                .admonition {{ padding: 16px; border-left: 4px solid {Colors.ACCENT_PRIMARY}; background: {Colors.BG_MEDIUM}; margin: 1.5em 0; border-radius: 4px; }}
                img {{ max-width: 100%; height: auto; border-radius: 8px; border: 1px solid {Colors.BORDER}; }}
                a {{ color: {Colors.ACCENT_PRIMARY}; text-decoration: none; }}
                table {{ border-collapse: collapse; width: 100%; margin: 2em 0; }}
                th, td {{ border: 1px solid {Colors.BORDER}; padding: 12px; }}
            </style>
            <script>
                window.MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] }} }};
                document.addEventListener('DOMContentLoaded', () => {{
                    if (typeof mermaid !== 'undefined') {{
                        mermaid.initialize({{ startOnLoad: true, theme: 'dark', flowchart: {{ curve: 'basis' }} }});
                        setTimeout(() => {{ mermaid.init(); }}, 200);
                    }}
                }});
            </script>
        </head>
        <body><div class="content">{html_body}</div></body>
        </html>
        """
        self.viewer.setHtml(styled_html, base_url)
