"""Results display widget — chart, slot-based band comparison, popout table."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")  # noqa: E402

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from biopro.ui.theme import Colors


# ── Data table popout ─────────────────────────────────────────────────────────

class DataTableDialog(QDialog):
    """Full results table in a scrollable, resizable popout window."""

    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Full Results Table")
        self.resize(920, 520)
        self.setStyleSheet(f"background: {Colors.BG_DARK};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setStretchLastSection(True)

        col_labels = {
            "lane": "Lane", "band": "Band", "matched_band": "Matched",
            "position": "Position (px)", "raw_intensity": "Raw Intensity",
            "percent_of_total": "% of Total", "normalized": "Normalised",
            "ponceau_factor": "Ponceau Factor",
            "ponceau_normalized": "Ponceau Norm.",
            "snr": "SNR", "width": "Width (px)",
            # Add labels for your custom professor schema
            "wb_band_position": "Position (px)",
            "wb_raw": "WB Raw Intensity",
            "ponceau_raw": "Ponceau Raw",
            "ratio": "WB/Pon Ratio",
            "normalised_ratio": "Normalised",
        }
        
        core = ["lane", "band", "position", "raw_intensity",
                "percent_of_total", "normalized"]
        # Define the custom columns
        prof_cols = ["wb_band_position", "wb_raw", "ponceau_raw", "ratio", "normalised_ratio"]
        pon_cols = ["ponceau_factor", "ponceau_normalized"]
        extra = ["snr", "width"]
        
        # Add prof_cols to the final list generation
        cols = [c for c in core + prof_cols + pon_cols + extra if c in df.columns]

        table.setColumnCount(len(cols))
        table.setRowCount(len(df))
        table.setHorizontalHeaderLabels([col_labels.get(c, c) for c in cols])

        from PyQt6.QtGui import QColor as _QColor
        for ri, (_, row) in enumerate(df.iterrows()):
            for ci, col in enumerate(cols):
                val = row[col]
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    text = ""
                elif col == "lane":
                    text = str(int(val) + 1)
                elif isinstance(val, float):
                    text = f"{val:.4f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                if col in pon_cols:
                    item.setForeground(_QColor(Colors.ACCENT_PRIMARY))
                table.setItem(ri, ci, item)

        layout.addWidget(table)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)


# ── Chart ─────────────────────────────────────────────────────────────────────

class DensityChart(FigureCanvasQTAgg):
    """Matplotlib bar chart — WB or Ponceau-corrected values."""

    def __init__(self, parent=None) -> None:
        self.fig = Figure(figsize=(6, 3.2), dpi=100)
        self.fig.patch.set_facecolor(Colors.BG_DARK)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")

    def plot_densities(
        self,
        df: pd.DataFrame,
        mode: str = "wb",
        highlighted_lanes: Optional[list[int]] = None,
    ) -> None:
        self.axes.clear()
        self.axes.set_facecolor(Colors.BG_DARK)
        self.axes.tick_params(colors=Colors.FG_SECONDARY)
        for sp in ("top", "right"):
            self.axes.spines[sp].set_visible(False)
        for sp in ("bottom", "left"):
            self.axes.spines[sp].set_color(Colors.BORDER)

        if df.empty:
            self.axes.text(
                0.5, 0.5, "No data to display",
                ha="center", va="center",
                color=Colors.FG_SECONDARY, fontsize=13,
                transform=self.axes.transAxes,
            )
            self.draw()
            return

        use_pon = mode == "ponceau" and "ponceau_normalized" in df.columns
        vcol = "ponceau_normalized" if use_pon else "normalized"

        sample_df = df[~df["is_ladder"]] if "is_ladder" in df.columns else df
        primary = (
            sample_df
            .sort_values("raw_intensity", ascending=False)
            .groupby("lane", as_index=False).first()
            .sort_values("lane")
        )

        hl = set(highlighted_lanes or [])
        lanes = primary["lane"].values
        vals  = primary[vcol].values
        labels = [f"Lane {int(l)+1}" for l in lanes]
        colors = [
            Colors.ACCENT_WARNING
            if int(l) in hl
            else Colors.CHART_COLORS[int(l) % len(Colors.CHART_COLORS)]
            for l in lanes
        ]

        bars = self.axes.bar(
            range(len(lanes)), vals,
            color=colors, edgecolor="none", width=0.6, alpha=0.9,
        )
        self.axes.set_xticks(range(len(lanes)))
        self.axes.set_xticklabels(labels, fontsize=9, color=Colors.FG_SECONDARY)

        max_val = float(max(vals)) if len(vals) else 1.0
        for bar, val in zip(bars, vals):
            if val > 0:
                self.axes.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max_val * 0.01,
                    f"{val:.3f}", ha="center", va="bottom",
                    fontsize=8, color=Colors.FG_SECONDARY,
                )

        ylabel = ("Ponceau-normalised Density"
                  if use_pon else "Relative Density")
        self.axes.set_ylabel(ylabel, fontsize=10, color=Colors.FG_PRIMARY)
        title = ("Band Density — Ponceau Loading Correction Applied"
                 if use_pon else "Band Density Comparison")
        self.axes.set_title(
            title, fontsize=12, fontweight="bold",
            color=Colors.FG_PRIMARY, pad=8,
        )
        self.fig.tight_layout()
        self.draw()

    def plot_professor(
        self,
        df: pd.DataFrame,
        has_ponceau: bool = False,
        highlighted_lanes: Optional[list[int]] = None,
        slot_colors: Optional[dict[int, str]] = None,
    ) -> None:
        """Plot normalised ratios using per-slot colors for selected lanes."""
        self.axes.clear()
        self.axes.set_facecolor(Colors.BG_DARK)
        self.axes.tick_params(colors=Colors.FG_SECONDARY)
        for sp in ("top", "right"):
            self.axes.spines[sp].set_visible(False)
        for sp in ("bottom", "left"):
            self.axes.spines[sp].set_color(Colors.BORDER)

        if df.empty or "normalised_ratio" not in df.columns:
            self.axes.text(0.5, 0.5, "No data yet",
                           ha="center", va="center",
                           color=Colors.FG_SECONDARY, fontsize=12,
                           transform=self.axes.transAxes)
            self.draw()
            return

        sample = df[~df["is_ladder"]] if "is_ladder" in df.columns else df
        sc = slot_colors or {}

        lanes = sample["lane"].values
        ratios = sample["normalised_ratio"].values
        labels = [f"Lane {int(l)+1}" for l in lanes]
        colors = [
            sc[int(l)] if int(l) in sc
            else Colors.BG_LIGHT
            for l in lanes
        ]

        bars = self.axes.bar(
            range(len(lanes)), ratios,
            color=colors, edgecolor="none", width=0.6, alpha=0.92,
        )
        self.axes.set_xticks(range(len(lanes)))
        self.axes.set_xticklabels(labels, fontsize=9, color=Colors.FG_SECONDARY)

        max_v = float(max(ratios)) if len(ratios) else 1.0
        for bar, val, lane in zip(bars, ratios, lanes):
            color = sc.get(int(lane), Colors.FG_SECONDARY)
            self.axes.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_v * 0.01,
                f"{val:.3f}", ha="center", va="bottom",
                fontsize=9, color=color,
            )

        title = (
            "WB / Ponceau Ratio per Lane (normalised)"
            if has_ponceau
            else "WB Band Density per Lane (normalised)"
        )
        self.axes.set_title(title, fontsize=12, fontweight="bold",
                            color=Colors.FG_PRIMARY, pad=8)
        ylabel = "WB / Ponceau ratio" if has_ponceau else "Normalised density"
        self.axes.set_ylabel(ylabel, fontsize=10, color=Colors.FG_PRIMARY)

        self.fig.tight_layout()
        self.draw()

    def save_chart(self, path: Path) -> None:
        self.fig.savefig(
            str(path), dpi=300, bbox_inches="tight",
            facecolor=self.fig.get_facecolor(),
        )


# ── Results widget ────────────────────────────────────────────────────────────

class ResultsWidget(QWidget):
    """Chart + slot-based band comparison + popout full data table."""

    _SLOT_COLORS = [
        "#f85149",  # red
        "#58a6ff",  # blue
        "#3fb950",  # green
        "#d29922",  # amber
        "#a371f7",  # purple
        "#f778ba",  # pink
        "#2dccb8",  # teal
        "#79c0ff",  # light blue
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._chart_mode = "wb"
        self._canvas_ref = None
        self._slots: list = []
        self._active_slot: int | None = None
        self._num_slots = 2
        self._slot_btns: list[QPushButton] = []
        self._setup_ui()

    def set_canvas(self, canvas) -> None:
        self._canvas_ref = canvas

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Chart
        self.chart = DensityChart(self)
        layout.addWidget(self.chart, stretch=3)

        # WB / Ponceau toggle
        self._toggle_row = QWidget()
        tr = QHBoxLayout(self._toggle_row)
        tr.setContentsMargins(4, 0, 4, 0)
        tr.setSpacing(8)
        tr.addWidget(QLabel("Show:"))
        self._btn_wb  = QRadioButton("WB Normalised")
        self._btn_pon = QRadioButton("Ponceau Corrected")
        self._btn_wb.setChecked(True)
        self._mode_grp = QButtonGroup(self)
        self._mode_grp.addButton(self._btn_wb,  0)
        self._mode_grp.addButton(self._btn_pon, 1)
        self._mode_grp.idClicked.connect(self._on_mode_changed)
        tr.addWidget(self._btn_wb)
        tr.addWidget(self._btn_pon)
        tr.addStretch()
        self._toggle_row.setVisible(False)
        layout.addWidget(self._toggle_row)

        # Export row
        exp = QHBoxLayout()
        exp.setSpacing(4)
        self.btn_table = QPushButton("📋 Full Table")
        self.btn_csv   = QPushButton("📄 CSV")
        self.btn_excel = QPushButton("📊 Excel")
        self.btn_png   = QPushButton("🖼️ Chart")
        for b in (self.btn_table, self.btn_csv, self.btn_excel, self.btn_png):
            b.setMinimumHeight(28)
            exp.addWidget(b)
        self.btn_table.clicked.connect(self._show_table)
        self.btn_csv.clicked.connect(self._export_csv)
        self.btn_excel.clicked.connect(self._export_excel)
        self.btn_png.clicked.connect(self._export_png)
        layout.addLayout(exp)

        # Band comparison group
        cg = QGroupBox("Band Comparison — Fold Change")
        cg_l = QVBoxLayout(cg)
        cg_l.setSpacing(5)

        # Slot count
        cr = QHBoxLayout()
        cr.addWidget(QLabel("Bands to compare:"))
        self._spin_slots = QSpinBox()
        self._spin_slots.setRange(2, 12)
        self._spin_slots.setValue(2)
        self._spin_slots.setToolTip(
            "Number of bands to compare.\n"
            "Click a Band button to enter selection mode,\n"
            "then click a band on the image."
        )
        self._spin_slots.valueChanged.connect(self._on_slots_changed)
        # valueChanged is wired externally by WesternBlotPanel.set_results_widget
        # so that changing the count also triggers a results recompute.
        cr.addWidget(self._spin_slots)
        cr.addStretch()
        cg_l.addLayout(cr)

        # Instructions
        hint = QLabel(
            "1. Click a Band button to enter selection mode.\n"
            "2. Click any band on the image to assign it.\n"
            "3. Click the button again to exit, repeat for other slots."
        )
        hint.setStyleSheet(f"color: {Colors.FG_SECONDARY}; font-size: 10px;")
        cg_l.addWidget(hint)

        # Slot buttons container
        self._slots_container = QWidget()
        self._slots_layout = QVBoxLayout(self._slots_container)
        self._slots_layout.setSpacing(3)
        self._slots_layout.setContentsMargins(0, 0, 0, 0)
        cg_l.addWidget(self._slots_container)

        # Clear button
        btn_clr = QPushButton("✖  Clear All")
        btn_clr.setStyleSheet(
            f"QPushButton {{ background: {Colors.BG_MEDIUM};"
            f" color: {Colors.FG_SECONDARY}; border: 1px solid {Colors.BORDER};"
            f" border-radius: 5px; padding: 3px 10px; }}"
            f"QPushButton:hover {{ background: {Colors.BG_LIGHT}; }}"
        )
        btn_clr.clicked.connect(self._clear_all)
        cg_l.addWidget(btn_clr)

        # Result text
        self.lbl_result = QLabel("")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_result.setStyleSheet(f"color: {Colors.FG_PRIMARY}; font-size: 11px;")
        cg_l.addWidget(self.lbl_result)

        layout.addWidget(cg)
        self.comparison_group = cg

        # Build default slots
        self._rebuild_slots(2)

    def _col(self, idx: int) -> str:
        return self._SLOT_COLORS[idx % len(self._SLOT_COLORS)]

    def _rebuild_slots(self, n: int) -> None:
        """Recreate n slot buttons, preserving existing assignments where possible."""
        # Save current assignments before destroying buttons
        old_slots = list(self._slots)
        old_n = self._num_slots

        self._active_slot = None
        self._slots = [None] * n
        self._num_slots = n

        while self._slots_layout.count():
            item = self._slots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._slot_btns = []
        for i in range(n):
            c = self._col(i)
            btn = QPushButton(f"Band {i+1} — click here to start selecting")
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setStyleSheet(
                f"QPushButton {{ border: 2px solid {c}; border-radius: 5px;"
                f" background: {Colors.BG_DARK}; color: {Colors.FG_SECONDARY};"
                f" padding: 4px 8px; text-align: left; font-size: 11px; }}"
                f"QPushButton:checked {{ background: {c}22; color: {c};"
                f" font-weight: 600; }}"
                f"QPushButton:hover:!checked {{ background: {c}11; }}"
            )
            btn.clicked.connect(lambda checked, idx=i: self._on_slot_clicked(idx, checked))
            self._slot_btns.append(btn)
            self._slots_layout.addWidget(btn)

        # Restore previous assignments for slots that still exist
        for i in range(min(n, old_n)):
            if i < len(old_slots) and old_slots[i] is not None:
                self._slots[i] = old_slots[i]
                self._update_slot_label(i)

        self.lbl_result.setText("")
        self._update_canvas_markers()

    def _on_slot_clicked(self, idx: int, checked: bool) -> None:
        if checked:
            self._active_slot = idx
            for i, b in enumerate(self._slot_btns):
                if i != idx:
                    b.blockSignals(True)
                    b.setChecked(False)
                    b.blockSignals(False)
            self._slot_btns[idx].setText(
                f"Band {idx+1} — 🎯 selecting… click a band on the image"
            )
        else:
            self._active_slot = None
            self._update_slot_label(idx)

    # ── Public API ────────────────────────────────────────────────────

    def set_results(self, df: pd.DataFrame) -> None:
        """Update results data.

        On the **first** call, initialises the slot count from the number
        of lanes.  On subsequent calls, preserves the user's slot count
        and band assignments — only the labels and chart are refreshed.
        """
        is_first = self._df is None
        self._df = df.copy()

        if is_first:
            # First result: set slot count from lane count
            n = max(2, int(df["lane"].nunique())) if not df.empty else 2
            self._spin_slots.blockSignals(True)
            self._spin_slots.setValue(n)
            self._spin_slots.blockSignals(False)
            self._rebuild_slots(n)
        else:
            # Subsequent updates: preserve slot count and assignments.
            # Just refresh labels so ratio values shown in buttons stay current.
            for i in range(self._num_slots):
                self._update_slot_label(i)

        # Detect Ponceau
        has_pon = False
        if "ponceau_raw" in df.columns:
            pon_vals = pd.to_numeric(df["ponceau_raw"], errors="coerce").fillna(0)
            has_pon = bool((pon_vals > 0).any())

        self._toggle_row.setVisible(False)
        self._chart_mode = "ratio"
        self._refresh_chart()
        self._update_canvas_markers()
        self._render_result()

    def assign_band_to_active_slot(self, band) -> None:
        """Called when user clicks a band on the canvas while in slot-select mode."""
        idx = self._active_slot
        if idx is None:
            return
        self._slots[idx] = band
        self._slot_btns[idx].blockSignals(True)
        self._slot_btns[idx].setChecked(False)
        self._slot_btns[idx].blockSignals(False)
        self._active_slot = None
        self._update_slot_label(idx)
        self._update_canvas_markers()
        self._render_result()
        self._refresh_chart()

    # Back-compat shim
    def highlight_band_for_comparison(self, band) -> None:
        self.assign_band_to_active_slot(band)

    def update_pairwise_comparison(self, _bands: list) -> None:
        pass

    # ── Internal ──────────────────────────────────────────────────────

    def _update_slot_label(self, idx: int) -> None:
        band = self._slots[idx]
        if band is None:
            self._slot_btns[idx].setText(
                f"Band {idx+1} — click here to start selecting"
            )
            return

        intensity = float(band.integrated_intensity)
        if intensity < 1e-6:
            intensity = float(band.peak_height)
            intensity_src = "peak"
        else:
            intensity_src = "raw"
        norm_txt = f"  ·  {intensity_src} {intensity:.1f}"

        if self._df is not None and not self._df.empty and "normalised_ratio" in self._df.columns:
            mask = self._df["lane"].astype(int) == int(band.lane_index)
            rows = self._df[mask]
            if not rows.empty:
                ratio = float(rows.iloc[0]["normalised_ratio"])
                norm_txt += f"  ·  norm {ratio:.4f}"

        self._slot_btns[idx].setText(
            f"Band {idx+1}  ·  Lane {band.lane_index+1}"
            f"  pos {band.position}px  SNR {band.snr:.1f}"
            f"  raw {band.integrated_intensity:.1f}{norm_txt}"
        )

    def _clear_all(self) -> None:
        self._active_slot = None
        for i in range(self._num_slots):
            self._slots[i] = None
            self._slot_btns[i].blockSignals(True)
            self._slot_btns[i].setChecked(False)
            self._slot_btns[i].blockSignals(False)
            self._update_slot_label(i)
        self.lbl_result.setText("")
        self._update_canvas_markers()
        self._refresh_chart()

    def _update_canvas_markers(self) -> None:
        if self._canvas_ref is None:
            return
        if hasattr(self._canvas_ref, "set_all_comparison_slots"):
            slot_map = {}
            for i, band in enumerate(self._slots):
                if band is not None:
                    slot_map[(band.lane_index, band.band_index)] = self._col(i)
            self._canvas_ref.set_all_comparison_slots(slot_map)
        elif hasattr(self._canvas_ref, "set_band_comparison_slots"):
            a = self._slots[0] if len(self._slots) > 0 else None
            b = self._slots[1] if len(self._slots) > 1 else None
            self._canvas_ref.set_band_comparison_slots(a, b)

    def _refresh_chart(self) -> None:
        if self._df is None:
            return
        slot_colors = {}
        for i, band in enumerate(self._slots):
            if band is not None:
                slot_colors[band.lane_index] = self._col(i)
        has_pon = False
        if "ponceau_raw" in self._df.columns:
            pon_vals = pd.to_numeric(self._df["ponceau_raw"], errors="coerce").fillna(0)
            has_pon = bool((pon_vals > 0).any())
        self.chart.plot_professor(
            self._df, has_ponceau=has_pon, slot_colors=slot_colors
        )

    def _get_vals(self, band):
        """Get (normalised_ratio, ponceau_raw) for a band from the results df."""
        if self._df is None or self._df.empty:
            return None, None
        if "normalised_ratio" in self._df.columns:
            mask = self._df["lane"].astype(int) == int(band.lane_index)
            rows = self._df[mask]
            if rows.empty:
                return None, None
            row = rows.iloc[0]
            ratio = float(row.get("normalised_ratio", row.get("ratio", 0.0)))
            pon_raw = float(row.get("ponceau_raw", 0.0) or 0.0)
            return ratio, pon_raw
        # Legacy schema
        mask = (
            (self._df["lane"].astype(int) == int(band.lane_index)) &
            (self._df["band"].astype(int) == int(band.band_index))
        )
        rows = self._df[mask]
        if rows.empty:
            return None, None
        row = rows.iloc[0]
        norm = float(row.get("normalized", 0.0))
        pon  = float(row.get("ponceau_normalized", norm))
        return norm, pon

    def _render_result(self) -> None:
        filled = [(i, b) for i, b in enumerate(self._slots) if b is not None]
        if len(filled) < 2:
            self.lbl_result.setText(
                f"<span style='color:{Colors.FG_SECONDARY}; font-size:10px;'>"
                f"Fill at least 2 slots to see fold changes.</span>"
            )
            return

        has_pon = (
            self._df is not None
            and "ponceau_normalized" in self._df.columns
            and bool((self._df.get("ponceau_factor", pd.Series([1.0])) != 1.0).any())
        )

        lines = []
        for i, band in filled:
            c = self._col(i)
            norm, pon = self._get_vals(band)
            ns = f"{norm:.4f}" if norm is not None else "N/A"
            ps = f"{pon:.4f}"  if pon  is not None else "N/A"
            extra = (f"  · Ponceau <b>{ps}</b>" if has_pon and pon != norm else "")
            lines.append(
                f"<span style='color:{c}; font-weight:600;'>Band {i+1}</span>"
                f" — Lane {band.lane_index+1} · pos {band.position}px"
                f" · raw {band.integrated_intensity:.1f} · norm {ns}{extra}"
            )

        lines.append("")

        ac = Colors.ACCENT_PRIMARY
        pairs = [(filled[k], filled[k+1]) for k in range(len(filled)-1)]
        for (i, b1), (j, b2) in pairs:
            n1, p1 = self._get_vals(b1)
            n2, p2 = self._get_vals(b2)
            c1, c2 = self._col(i), self._col(j)
            lbl = (
                f"<span style='color:{c1};'>Band {i+1}</span>"
                f" \u2192 <span style='color:{c2};'>Band {j+1}</span>"
            )
            if n1 is not None and n2 is not None:
                if n1 > 1e-6:
                    fc = f"<b>{n2/n1:.3f}\u00d7</b>"
                elif n2 > 1e-6:
                    fc = "<b>\u221e</b> (Band A norm is zero)"
                else:
                    fc = "N/A (both near zero — check band detection)"
                lines.append(f"{lbl} &nbsp; fold (normalised): {fc}")
            if has_pon and p1 is not None and p2 is not None:
                if p1 > 1e-6:
                    fc_p = f"<b>{p2/p1:.3f}\u00d7</b>"
                elif p2 > 1e-6:
                    fc_p = "<b>\u221e</b> (Band A Ponceau is zero)"
                else:
                    fc_p = "N/A (both near zero)"
                lines.append(
                    f"{lbl} &nbsp; fold (Ponceau-normalised): "
                    f"<span style='color:{ac};'>{fc_p}</span>"
                )

        self.lbl_result.setText("<br>".join(lines))

    def _on_mode_changed(self, btn_id: int) -> None:
        self._chart_mode = "ponceau" if btn_id == 1 else "wb"
        self._refresh_chart()

    def _show_table(self) -> None:
        if self._df is None:
            return
        DataTableDialog(self._df, parent=self).exec()

    def _export_csv(self) -> None:
        if self._df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "densitometry_results.csv", "CSV Files (*.csv)"
        )
        if path:
            self._df.to_csv(path, index=False)

    def _export_excel(self) -> None:
        if self._df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "densitometry_results.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            self._df.to_excel(path, index=False, sheet_name="Results")

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chart", "density_chart.png", "PNG Files (*.png)"
        )
        if path:
            self.chart.save_chart(path)

    def _on_slots_changed(self, val: int) -> None:
        """Handle changes to the number of comparison slots."""
        self._rebuild_slots(val)
        self._refresh_chart()
        self._render_result()