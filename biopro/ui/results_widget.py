"""Results display widget with embedded plots and data table.

Displays analysis results in two views:
    1. An embedded Matplotlib bar chart showing relative band densities.
    2. A QTableWidget with the full numerical data.

Includes export buttons for CSV, Excel, and chart image (PNG).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")  # noqa: E402 — must be set before importing pyplot

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGroupBox,
    QLabel,
)

from biopro.ui.theme import Colors


class DensityChart(FigureCanvasQTAgg):
    """Embedded Matplotlib chart for displaying band densities.

    Shows a grouped bar chart with lanes on the x-axis and
    normalized intensity on the y-axis. Styled to match the
    BioPro dark theme.
    """

    def __init__(self, parent=None, width: float = 6, height: float = 3.5) -> None:
        """Initialize the chart canvas.

        Args:
            parent: Parent widget.
            width: Figure width in inches.
            height: Figure height in inches.
        """
        self.fig = Figure(figsize=(width, height), dpi=100)
        self.fig.patch.set_facecolor(Colors.BG_DARK)
        self.axes = self.fig.add_subplot(111)

        super().__init__(self.fig)
        self.setStyleSheet(f"background-color: {Colors.BG_DARK};")

    def plot_densities(self, df: pd.DataFrame) -> None:
        """Plot band densities as a bar chart.

        Args:
            df: DataFrame with columns 'lane', 'band', and 'normalized'.
        """
        self.axes.clear()

        if df.empty:
            self.axes.text(
                0.5, 0.5, "No data to display",
                ha="center", va="center",
                color=Colors.FG_SECONDARY,
                fontsize=14,
                transform=self.axes.transAxes,
            )
            self.draw()
            return

        # Style the axes for dark theme
        self.axes.set_facecolor(Colors.BG_DARK)
        self.axes.tick_params(colors=Colors.FG_SECONDARY)
        self.axes.spines["bottom"].set_color(Colors.BORDER)
        self.axes.spines["left"].set_color(Colors.BORDER)
        self.axes.spines["top"].set_visible(False)
        self.axes.spines["right"].set_visible(False)

        # Group by lane — prefer matched bands when available so comparisons stay consistent
        if "matched_band" in df.columns and df["matched_band"].notna().any():
            primary_bands = df[df["matched_band"] == 0]
            if primary_bands.empty:
                # Fallback: choose the lowest matched_band per lane
                primary_bands = (
                    df.dropna(subset=["matched_band"])
                    .sort_values(["lane", "matched_band"])
                    .groupby("lane", as_index=False)
                    .first()
                )
        else:
            primary_bands = df[df["band"] == 0] if "band" in df.columns else df

        if primary_bands.empty:
            primary_bands = df.groupby("lane").first().reset_index()

        lanes = primary_bands["lane"].values
        intensities = primary_bands["normalized"].values
        labels = [f"Lane {l + 1}" for l in lanes]

        chart_colors = Colors.CHART_COLORS
        bar_colors = [chart_colors[i % len(chart_colors)] for i in range(len(lanes))]

        bars = self.axes.bar(
            range(len(lanes)),
            intensities,
            color=bar_colors,
            edgecolor="none",
            width=0.6,
            alpha=0.9,
        )

        self.axes.set_xticks(range(len(lanes)))
        self.axes.set_xticklabels(labels, fontsize=10, color=Colors.FG_SECONDARY)
        self.axes.set_ylabel(
            "Relative Density",
            fontsize=12,
            color=Colors.FG_PRIMARY,
        )
        self.axes.set_title(
            "Band Density Comparison",
            fontsize=14,
            fontweight="bold",
            color=Colors.FG_PRIMARY,
            pad=12,
        )

        # Add value labels on top of bars
        for bar, val in zip(bars, intensities):
            self.axes.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(intensities) * 0.02,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=Colors.FG_SECONDARY,
            )

        self.fig.tight_layout()
        self.draw()

    def save_chart(self, path: str | Path) -> None:
        """Save the chart as a PNG image.

        Args:
            path: Output file path.
        """
        self.fig.savefig(
            str(path),
            dpi=300,
            bbox_inches="tight",
            facecolor=self.fig.get_facecolor(),
        )


class ResultsWidget(QWidget):
    """Combined results display with chart and data table.

    Layout:
        Top: DensityChart (Matplotlib bar chart).
        Middle: QTableWidget with full data.
        Bottom: Export buttons (CSV, Excel, PNG).
    """

    def __init__(self, parent=None) -> None:
        """Initialize the results widget."""
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Chart
        self.chart = DensityChart(self)
        layout.addWidget(self.chart, stretch=2)

        # Data table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

        # Export buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.btn_csv = QPushButton("📄 Export CSV")
        self.btn_excel = QPushButton("📊 Export Excel")
        self.btn_png = QPushButton("🖼️ Export Chart PNG")
        self.btn_copy = QPushButton("📋 Copy to Clipboard")

        for btn in [self.btn_csv, self.btn_excel, self.btn_png, self.btn_copy]:
            button_layout.addWidget(btn)

        self.btn_csv.clicked.connect(self._export_csv)
        self.btn_excel.clicked.connect(self._export_excel)
        self.btn_png.clicked.connect(self._export_png)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        layout.addLayout(button_layout)
        
        # Pairwise Comparison
        self.comparison_group = QGroupBox("Pairwise Comparison")
        comp_layout = QVBoxLayout(self.comparison_group)
        self.lbl_comparison = QLabel("Select exactly two bands on the image canvas to compare their densities.")
        self.lbl_comparison.setWordWrap(True)
        comp_layout.addWidget(self.lbl_comparison)
        layout.addWidget(self.comparison_group)

    def set_results(self, df: pd.DataFrame) -> None:
        """Display results from a DataFrame.

        Updates both the chart and the data table.

        Args:
            df: DataFrame with analysis results.
        """
        self._df = df.copy()

        # Update chart
        self.chart.plot_densities(df)

        # Update table
        self.table.clear()
        if df.empty:
            return

        # Display columns (user-friendly subset)
        display_cols = [
            c
            for c in [
                "lane",
                "band",
                "matched_band",
                "position",
                "aligned_position",
                "raw_intensity",
                "percent_of_total",
                "normalized",
            ]
            if c in df.columns
        ]
        display_df = df[display_cols].copy()

        # Rename for readability
        col_names = {
            "lane": "Lane",
            "band": "Band",
            "matched_band": "Matched Band",
            "position": "Position",
            "aligned_position": "Aligned Pos",
            "raw_intensity": "Raw Intensity",
            "percent_of_total": "% of Total",
            "normalized": "Normalized",
        }

        self.table.setColumnCount(len(display_cols))
        self.table.setRowCount(len(display_df))
        self.table.setHorizontalHeaderLabels(
            [col_names.get(c, c) for c in display_cols]
        )

        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            for col_idx, col in enumerate(display_cols):
                value = row[col]
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    text = ""
                elif isinstance(value, float):
                    text = f"{value:.4f}"
                else:
                    text = str(int(value) + 1 if col == "lane" else value)

                item = QTableWidgetItem(text)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row_idx, col_idx, item)

    def _export_csv(self) -> None:
        """Export results to CSV via file dialog."""
        if self._df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "densitometry_results.csv", "CSV Files (*.csv)"
        )
        if path:
            self._df.to_csv(path, index=False)

    def _export_excel(self) -> None:
        """Export results to Excel via file dialog."""
        if self._df is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "densitometry_results.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            self._df.to_excel(path, index=False, sheet_name="Results")

    def _export_png(self) -> None:
        """Export chart as PNG via file dialog."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chart", "density_chart.png", "PNG Files (*.png)"
        )
        if path:
            self.chart.save_chart(path)

    def _copy_to_clipboard(self) -> None:
        """Copy results table to clipboard as tab-separated text."""
        if self._df is None:
            return
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self._df.to_csv(sep="\t", index=False))

    def update_pairwise_comparison(self, selected_bands: list) -> None:
        """Update the pairwise comparison UI based on selected bands.
        
        Args:
            selected_bands: List of explicitly toggled/selected DetectedBand objects.
        """
        if len(selected_bands) != 2:
            self.lbl_comparison.setText("Select exactly two bands on the image canvas to compare their densities.")
            self.lbl_comparison.setStyleSheet(f"color: {Colors.FG_SECONDARY};")
            return
            
        b1, b2 = selected_bands
        
        # Calculate raw ratio
        r1, r2 = b1.integrated_intensity, b2.integrated_intensity
        if r2 == 0:
            ratio_text = "N/A (Div by zero)"
        else:
            ratio = r1 / r2
            ratio_text = f"Band A / Band B = <b>{ratio:.2f}x</b>"
            
        info = (
            f"<b>Band A</b> (Lane {b1.lane_index + 1}, Pos {b1.position:.0f}): Raw Int = {r1:.2f}<br>"
            f"<b>Band B</b> (Lane {b2.lane_index + 1}, Pos {b2.position:.0f}): Raw Int = {r2:.2f}<br><br>"
            f"{ratio_text}"
        )
        self.lbl_comparison.setText(info)
        self.lbl_comparison.setStyleSheet(f"color: {Colors.FG_PRIMARY};")
