"""TutorialOverlay — full-screen coaching overlay for BioPro Academy.

Design principles (SOLID):
- Single responsibility: owns only rendering and masking of the overlay.
  All state machine logic lives in AcademyManager / workspace_window.
- Open/Closed: new step types are handled by extending render_step()
  branching logic without modifying mask or paint internals.
- Dependency Inversion: receives steps via event_bus; does not import
  AcademyManager directly.
"""

import math

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QRegion
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from biopro.core.event_bus import BioProEvent, event_bus
from biopro.core.models.tutorial_models import (
    BaseStep,
    BranchingStep,
    ForcedInteractionStep,
    InfoStep,
    InteractionStep,
    SubplotCheckStep,
    VerificationStep,
    WaitForEventStep,
)
from biopro.ui.components.cyto_character import CytoWidget
from biopro.ui.theme import Colors

# We will use Colors dynamically in the UI code rather than hardcoded hex codes.


class TutorialOverlay(QWidget):
    """Full-screen coaching overlay.

    Sits as a sibling of the plugin panel inside analysis_page.
    Cuts transparent "spotlight" holes over target widgets so the user
    can interact with them while the rest of the UI is dimmed.

    Public interface
    ----------------
    render_step(step)        Called by event_bus when the step changes.
    show_text(text)          Update the bubble text (called by timer loop).
    set_targets(rects)       Update spotlight rectangles + reposition Cyto.
    set_progress(cur, total) Update the progress bar.
    """

    def __init__(self, parent: QWidget | None = None, compact_mode: bool = False) -> None:
        super().__init__(parent)
        # Allow mouse events; masking handles the passthrough behaviour.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.target_rects: list[QRect] = []
        self.current_step: BaseStep | None = None
        self._compact_mode = compact_mode

        self._build_cyto()
        self._build_bubble()

        # Save bound methods as instance variables so they can be reliably removed later
        # (Accessing self.method creates a new bound method object each time, which fails list.remove)
        self._render_step_cb = self.render_step
        self._on_subtask_cb = self._on_subtask_completed
        self._on_course_cb = self.show_completion_screen

        event_bus.subscribe(BioProEvent.ACADEMY_STEP_CHANGED, self._render_step_cb)
        event_bus.subscribe(BioProEvent.ACADEMY_SUBTASK_COMPLETED, self._on_subtask_cb)
        event_bus.subscribe(BioProEvent.ACADEMY_COURSE_COMPLETED, self._on_course_cb)

        self.destroyed.connect(self._cleanup)

        self._populate_default_buttons()

        # Initialize with the current state of the tutorial manager
        from PyQt6.QtCore import QTimer

        from biopro.core.tutorial_manager import global_tutorial_manager

        if getattr(global_tutorial_manager, "current_step", None):
            # Defer rendering slightly to allow layout to settle
            QTimer.singleShot(0, lambda: self.render_step(global_tutorial_manager.current_step))
        else:
            self.hide()

    def _cleanup(self, *args) -> None:
        """Unsubscribe from event bus when the C++ object is deleted."""
        event_bus.unsubscribe(BioProEvent.ACADEMY_STEP_CHANGED, self._render_step_cb)
        event_bus.unsubscribe(BioProEvent.ACADEMY_SUBTASK_COMPLETED, self._on_subtask_cb)
        event_bus.unsubscribe(BioProEvent.ACADEMY_COURSE_COMPLETED, self._on_course_cb)

    def _is_alive(self) -> bool:
        """Safely check if the underlying C++ object has been deleted."""
        try:
            self.objectName()
            return True
        except RuntimeError:
            return False

    # ── Build helpers ─────────────────────────────────────────────────────────

    def _build_cyto(self) -> None:
        self.cyto = CytoWidget(self)

    def _build_bubble(self) -> None:
        self.bubble_container = QWidget(self)
        self.bubble_container.setObjectName("BubbleContainer")
        self.bubble_container.setStyleSheet(
            f"#BubbleContainer {{ background-color: {Colors.BG_DARKEST}; border: 2px solid {Colors.ACCENT_SUCCESS}; border-radius: 12px; }}"
        )
        self.bubble_container.setFixedWidth(420)
        self.bubble_layout = QVBoxLayout(self.bubble_container)
        self.bubble_layout.setContentsMargins(0, 0, 0, 0)
        self.bubble_layout.setSpacing(0)

        self.body_container = QWidget()
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(14, 14, 14, 14)
        self.body_layout.setSpacing(8)
        self.bubble_layout.addWidget(self.body_container)

        # Header row
        header = QHBoxLayout()
        self.lbl_progress = QLabel("BioPro Academy")
        self.lbl_progress.setStyleSheet(
            f"color: {Colors.FG_SECONDARY}; font-size: 13px; font-weight: bold; font-family: sans-serif;"
        )
        self.btn_close = QPushButton("×")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setStyleSheet(
            f"color: {Colors.FG_SECONDARY}; border: none; font-size: 16px; font-weight: bold;"
        )
        self.btn_close.enterEvent = lambda e: self.btn_close.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; border: none; font-size: 16px; font-weight: bold;"
        )
        self.btn_close.leaveEvent = lambda e: self.btn_close.setStyleSheet(
            f"color: {Colors.FG_SECONDARY}; border: none; font-size: 16px; font-weight: bold;"
        )
        header.addWidget(self.lbl_progress)
        header.addStretch()
        header.addWidget(self.btn_close)
        self.body_layout.addLayout(header)

        # Step text
        self.text_label = QLabel("Welcome to BioPro Academy!")
        self.text_label.setTextFormat(Qt.TextFormat.PlainText)
        font = self.text_label.font()
        font.setPixelSize(16)
        font.setBold(True)
        font.setFamily("sans-serif")
        self.text_label.setFont(font)
        self.text_label.setStyleSheet(f"color: {Colors.FG_PRIMARY}; padding: 8px 0px;")
        self.text_label.setWordWrap(True)
        self.text_label.setFixedWidth(392)  # 420 (container) - 28 (margins)
        self.body_layout.addWidget(self.text_label)

        # Dynamic content (checklists, etc.)
        self.dynamic_content = QVBoxLayout()
        self.body_layout.addLayout(self.dynamic_content)

        # Footer container
        self.footer_container = QWidget()
        self.footer_container.setObjectName("BubbleFooter")
        self.footer_container.setStyleSheet(
            f"#BubbleFooter {{"
            f"  background-color: {Colors.BG_MEDIUM};"
            f"  border-bottom-left-radius: 8px;"
            f"  border-bottom-right-radius: 8px;"
            f"  border-top: 1px solid {Colors.BORDER};"
            f"}}"
        )
        self.footer_layout = QHBoxLayout(self.footer_container)
        self.footer_layout.setContentsMargins(14, 12, 14, 12)
        self.bubble_layout.addWidget(self.footer_container)

        # Progress bar (moved to footer)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {Colors.BG_DARKER}; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {Colors.ACCENT_PRIMARY}; border-radius: 3px; }}"
        )
        self.footer_layout.addWidget(self.progress_bar, stretch=1)
        self.footer_layout.addSpacing(16)

        # Button row
        self.btn_container = QWidget()
        self.btn_container.setStyleSheet("background: transparent;")
        self.btn_layout = QHBoxLayout(self.btn_container)
        self.btn_layout.setContentsMargins(0, 0, 0, 0)
        self.footer_layout.addWidget(self.btn_container)

        self.btn_next = QPushButton("Next →")
        self.btn_next.setStyleSheet(
            f"background-color: {Colors.ACCENT_PRIMARY}; color: {Colors.BG_DARKEST};"
            f"border: 1px solid {Colors.ACCENT_PRIMARY}; border-radius: 4px;"
            "padding: 6px 14px; font-weight: bold;"
        )
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_completion_screen(self, course_id: str, badge_reward: str) -> None:
        """Renders the sleek, professional completion overlay."""
        if not self._is_alive():
            return

        self.show()

        if hasattr(self, "completion_container"):
            self.completion_container.deleteLater()

        from biopro.ui.wizards.course_complete_overlay import CourseCompleteOverlay

        self.completion_container = CourseCompleteOverlay(self)
        self.completion_container.dismissed.connect(self._close_completion_screen)

        self.bubble_container.hide()
        self.cyto.hide()
        self.target_rects = []
        self._update_mask()
        self.update()

        self.completion_container.setGeometry(self.rect())
        self.completion_container.show_completion(course_id, badge_reward)

    def _center_completion_container(self) -> None:
        if hasattr(self, "completion_container") and self.completion_container.isVisible():
            cx = (self.width() - self.completion_container.width()) // 2
            cy = (self.height() - self.completion_container.height()) // 2
            self.completion_container.move(cx, cy)

    def _close_completion_screen(self) -> None:
        if hasattr(self, "completion_container"):
            self.completion_container.hide()
        self.hide()

    def show_text(self, text: str) -> None:
        """Update only the bubble text label (called from timer loop)."""
        self.text_label.setText(text)
        self._force_resize()

    def set_progress(self, current: int, total: int, phase_name: str = "") -> None:
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(current)
        label = f"Step {current} of {total}"
        if phase_name:
            label += f"  —  {phase_name}"
        self.lbl_progress.setText(label)

    def render_step(self, step: BaseStep | None) -> None:
        """Full render of a step — called by event_bus on ACADEMY_STEP_CHANGED."""
        if not self._is_alive():
            return

        if not step:
            if hasattr(self, "completion_container") and self.completion_container.isVisible():
                return
            self.hide()
            return

        self.current_step = step
        self.show()
        self._clear_dynamic_content()
        self._populate_default_buttons()

        # Update progress bar
        from biopro.core.tutorial_manager import global_tutorial_manager

        course = global_tutorial_manager.active_course
        if course and course.steps:
            main_path = course.get_main_path()
            total = len(main_path)
            if step.id in main_path:
                current = main_path.index(step.id) + 1
                self._last_main_step_idx = current
            else:
                current = getattr(self, "_last_main_step_idx", 1)
            self.set_progress(current, max(total, 1))

        self.text_label.setText(step.text)

        emotion = getattr(step, "cyto_emotion", "idle")
        self.cyto.set_emotion(emotion)
        if getattr(step, "cyto_animation", None):
            self.cyto.play_animation(step.cyto_animation)

        # Step-type-specific button configuration
        if isinstance(step, InfoStep):
            self.btn_next.show()
            self.btn_next.setText("Next →")

        elif isinstance(step, InteractionStep):
            # Auto-advances when the target widget fires its signal.
            self.btn_next.hide()

        elif isinstance(step, VerificationStep):
            # When allow_interaction is True the user acts then clicks Next.
            if getattr(step, "allow_interaction", False) and not getattr(
                step, "hide_next_button", False
            ):
                self.btn_next.show()
                self.btn_next.setText("Check ✓")
            else:
                self.btn_next.hide()

        elif isinstance(step, BranchingStep):
            self.btn_next.hide()
            self._render_branching_options(step.options)

        elif isinstance(step, ForcedInteractionStep):
            self.btn_next.hide()
            self._render_checklist(step)

        elif isinstance(step, SubplotCheckStep):
            self.btn_next.show()
            self.btn_next.setText("Confirm Subplot")

        elif isinstance(step, WaitForEventStep):
            # Auto-advances; no Next button needed. Show a waiting indicator.
            self.btn_next.hide()
            self._render_waiting_indicator()

        self._force_resize()

    # ── Spotlight geometry ────────────────────────────────────────────────────

    def set_targets(self, rects: list[QRect]) -> None:
        """Sets spotlight rectangles (in overlay-local coordinates)."""
        self.target_rects = rects
        self._reposition_cyto_and_bubble(rects)
        self._update_mask()
        self.update()  # schedule repaint

    def _reposition_cyto_and_bubble(self, rects: list[QRect]) -> None:
        """Move Cyto and bubble so they don't overlap spotlight holes.

        In ``compact_mode`` (hub launcher) Cyto is hidden and the bubble is
        centred in the overlay — no complex geometry needed.
        """
        if self._compact_mode:
            # ── Compact layout: Cyto and bubble as a side-by-side pair ────────
            self.cyto.show()
            self._force_resize()
            bubble_w = self.bubble_container.sizeHint().width()
            bubble_h = self.bubble_container.sizeHint().height()

            # Cyto's visual right edge is roughly cx + 240.
            # We place the bubble at cx + 240 so they sit side-by-side.
            total_w = 240 + bubble_w

            # Centre the pair horizontally
            start_x = max(10, (self.width() - total_w) // 2)
            cx = start_x
            bx = start_x + 240

            cyto_h = 400
            pair_h = max(cyto_h, bubble_h)

            # Centre vertically
            start_y = max(10, (self.height() - pair_h) // 2)
            cy = start_y + (pair_h - cyto_h) // 2
            by = start_y + (pair_h - bubble_h) // 2 + 30  # shift bubble slightly down for balance

            self.cyto.move(cx, cy)
            self.cyto.point_at(10)  # Point towards bubble

            self.bubble_container.move(bx, by)

            self.cyto.raise_()
            self.bubble_container.raise_()
            return

        if rects:
            primary = rects[0]

            # Compute the union bounding box of ALL targets to ensure Cyto avoids all of them
            union_rect = rects[0]
            for r in rects[1:]:
                union_rect = union_rect.united(r)

            cyto_x = union_rect.x() + union_rect.width() + 40
            cyto_y = max(20, primary.y() - 120)

            # If not enough room on the right, try the left
            if cyto_x + 320 > self.width():
                cyto_x = union_rect.x() - 350
                # If not enough room on the left either, put Cyto above or below the entire block
                if cyto_x < 20:
                    cyto_x = max(20, union_rect.x() + (union_rect.width() // 2) - 150)
                    if union_rect.y() + union_rect.height() + 400 < self.height():
                        cyto_y = union_rect.y() + union_rect.height() + 40
                    else:
                        cyto_y = max(20, union_rect.y() - 400)

            # If the union target is massive (like the plot canvas), move Cyto to the left sidebar
            if union_rect.width() > self.width() * 0.5 and len(rects) == 1:
                cyto_x = 20
                cyto_y = max(20, self.height() - 400)

            # Point Cyto's arm at target centre
            target_cx = primary.center().x()
            target_cy = primary.center().y()
            arm_x = cyto_x + 150 + 25
            arm_y = cyto_y + 250 + 10
            dx = target_cx - arm_x
            dy = target_cy - arm_y
            dist = math.hypot(dx, dy)
            target_angle = math.degrees(math.atan2(dy, dx))
            if dist > 47:
                angle = target_angle + math.degrees(math.acos(min(1.0, 47 / dist)))
            else:
                angle = target_angle + 90
            self.cyto.point_at(angle)
        else:
            cyto_x = 60
            cyto_y = 60
            self.cyto.point_at(-35)

        self.cyto.move(int(cyto_x), int(cyto_y))

        # Bubble sits below Cyto by default
        bubble_x = cyto_x
        bubble_y = cyto_y + 370
        bubble_w = self.bubble_container.sizeHint().width()
        bubble_h = self.bubble_container.sizeHint().height()

        # Clamp to screen
        if bubble_x + bubble_w > self.width():
            bubble_x = self.width() - bubble_w - 20
        if bubble_y + bubble_h > self.height():
            # If placing below Cyto pushes it off-screen, place it above Cyto's visible face.
            # Cyto's face is around y=150. We want the bottom of the bubble (bubble_y + bubble_h)
            # to be above y=150, leaving a small gap.
            bubble_y = max(10, cyto_y + 130 - bubble_h)

        # Keep bubble out of spotlight holes (unless hole is huge)
        if rects:
            bubble_rect = QRect(int(bubble_x), int(bubble_y), bubble_w, bubble_h)
            for r in rects:
                if r.width() > self.width() * 0.6 or r.height() > self.height() * 0.6:
                    continue  # Ignore massive holes like FlowCanvas
                if bubble_rect.intersects(r):
                    if r.x() > self.width() / 2:
                        bubble_x = min(bubble_x, r.x() - bubble_w - 20)
                    else:
                        bubble_x = max(bubble_x, r.right() + 20)

            bubble_x = max(10, min(bubble_x, self.width() - bubble_w - 10))

        self.bubble_container.move(int(bubble_x), int(bubble_y))

    # ── Painting & masking ────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:  # noqa: N802
        """Draw the dim overlay and cyan spotlight borders."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        allow = getattr(self.current_step, "allow_interaction", False)
        dim = QColor(0, 0, 0, 160)

        if self.target_rects:
            # Paint dim as a set of rects that surrounds the holes — never paint OVER holes.
            # This avoids CompositionMode_Clear which produces a white fill on non-translucent widgets.
            full = self.rect()
            holes = QRegion()
            for r in self.target_rects:
                holes = holes.united(QRegion(r))

            # Clip the painter to everything EXCEPT the holes, then fill
            dim_region = QRegion(full).subtracted(holes)
            painter.setClipRegion(dim_region)
            painter.fillRect(full, dim)
            painter.setClipping(False)

            # Cyan glow border around each hole
            glow_pen = QPen(QColor(88, 166, 255, 90))
            glow_pen.setWidth(8)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            for r in self.target_rects:
                painter.drawRoundedRect(r.adjusted(-4, -4, 4, 4), 8, 8)

            solid_pen = QPen(QColor(Colors.ACCENT_PRIMARY))
            solid_pen.setWidth(2)
            painter.setPen(solid_pen)
            for r in self.target_rects:
                painter.drawRoundedRect(r.adjusted(-1, -1, 1, 1), 5, 5)

        elif not allow:
            # No targets and not interactive — full dim
            painter.fillRect(self.rect(), dim)

        # else: allow_interaction with no targets — no dimming (pass-through mode)

        painter.end()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_mask()
        self._center_completion_container()

    def _update_mask(self) -> None:
        """Build a widget mask so mouse events pass through to target areas."""
        from biopro.core.models.tutorial_models import ForcedInteractionStep, InteractionStep

        allow = getattr(self.current_step, "allow_interaction", False)
        if isinstance(self.current_step, (InteractionStep, ForcedInteractionStep)):
            allow = True

        if self.target_rects and allow:
            # Mask = whole overlay MINUS the spotlight holes (holes are click-through)
            full = QRegion(self.rect())
            holes = QRegion()
            for r in self.target_rects:
                holes = holes.united(QRegion(r))

            mask = full.subtracted(holes)

            # Re-add Cyto and Bubble so they aren't erased by the holes
            mask = mask.united(QRegion(self.cyto.geometry()))
            mask = mask.united(QRegion(self.bubble_container.geometry()))

            self.setMask(mask)

        elif allow:
            # No specific targets but interaction is allowed — only the bubble
            # and Cyto block clicks; everything else is pass-through.
            mask = QRegion(self.cyto.geometry())
            mask = mask.united(QRegion(self.bubble_container.geometry()))
            self.setMask(mask)

        else:
            # Full lock — no clicks through at all
            self.clearMask()

    # ── Checklist (ForcedInteractionStep) ────────────────────────────────────

    def _render_checklist(self, step: ForcedInteractionStep) -> None:
        for task in step.sub_tasks:
            lbl = QLabel(f"☐  {task.instruction}")
            lbl.setObjectName(f"subtask_{task.id}")
            lbl.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 13px; margin-left: 8px;")
            self.dynamic_content.addWidget(lbl)

    def _on_subtask_completed(self, subtask_id: str, remaining_count: int) -> None:
        if not self._is_alive():
            return
        if not isinstance(self.current_step, ForcedInteractionStep):
            return
        for i in range(self.dynamic_content.count()):
            widget = self.dynamic_content.itemAt(i).widget()
            if widget and widget.objectName() == f"subtask_{subtask_id}":
                widget.setText(widget.text().replace("☐", "✅"))
                widget.setStyleSheet(
                    f"color: {Colors.FG_PRIMARY}; font-size: 13px; margin-left: 8px; font-weight: bold;"
                )
        if remaining_count == 0:
            self.btn_next.show()

    def _render_branching_options(self, options: dict) -> None:
        """Render branch buttons and connect them to next_step."""
        self._clear_buttons()
        btn_style = (
            "background-color: #1f6feb; color: white; border: none;"
            "border-radius: 4px; padding: 8px 14px; font-weight: bold;"
        )
        from biopro.core.tutorial_manager import global_tutorial_manager

        for text, target_id in options.items():
            btn = QPushButton(text.replace("btn_", "").replace("_", " ").title())
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Use default argument capture for target_id inside the lambda
            btn.clicked.connect(
                lambda checked, tid=target_id: global_tutorial_manager.next_step(tid)
            )
            self.btn_layout.addWidget(btn)

    def _render_waiting_indicator(self) -> None:
        """Add a pulsing 'waiting' label for WaitForEventStep steps."""
        from PyQt6.QtCore import QTimer

        wait_lbl = QLabel("⏳  Waiting for your action…")
        wait_lbl.setObjectName("waitingIndicator")
        wait_lbl.setStyleSheet(
            f"color: {Colors.ACCENT_PRIMARY}; font-size: 12px; font-style: italic;"
        )
        self.dynamic_content.addWidget(wait_lbl)

        # Simple text-blink pulse: toggle opacity-like feel by toggling colour
        self._wait_pulse_state = False

        def _pulse():
            self._wait_pulse_state = not self._wait_pulse_state
            colour = Colors.ACCENT_PRIMARY if self._wait_pulse_state else Colors.FG_SECONDARY
            wait_lbl.setStyleSheet(f"color: {colour}; font-size: 12px; font-style: italic;")

        self._wait_pulse_timer = QTimer(self)
        self._wait_pulse_timer.setInterval(700)
        self._wait_pulse_timer.timeout.connect(_pulse)
        self._wait_pulse_timer.start()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _populate_default_buttons(self) -> None:
        self._clear_buttons()
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.btn_next)

    def _clear_buttons(self) -> None:
        while self.btn_layout.count():
            item = self.btn_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                if w == getattr(self, "btn_next", None):
                    w.hide()
                    w.setParent(None)
                else:
                    w.deleteLater()

    def _clear_dynamic_content(self) -> None:
        # Stop any running WaitForEventStep pulse timer
        if hasattr(self, "_wait_pulse_timer") and self._wait_pulse_timer.isActive():
            self._wait_pulse_timer.stop()
        while self.dynamic_content.count():
            item = self.dynamic_content.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _force_resize(self) -> None:
        # Explicitly calculate the required height for the fixed width (392px)
        # and enforce it as the minimum height so the container layout expands.
        # Reset minimum height first so we don't infinitely compound during typing effect
        self.text_label.setMinimumHeight(0)

        # Add 48px buffer to account for stylesheet padding and macOS line-height quirks
        required_height = self.text_label.heightForWidth(392) + 48
        self.text_label.setMinimumHeight(required_height)

        self.text_label.updateGeometry()
        self.body_layout.invalidate()
        self.body_container.updateGeometry()
        self.bubble_layout.invalidate()
        self.bubble_container.updateGeometry()
        self.bubble_container.resize(self.bubble_layout.sizeHint())
