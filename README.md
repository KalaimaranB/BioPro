# 🧬 BioPro — Bio-Image Analysis Made Simple

> An open-source, intuitive alternative to ImageJ for lab students and professionals.

BioPro automates tedious bio-image analysis workflows — starting with **western blot densitometry** — through a modern desktop interface with sensible defaults and full parameter control.

## ✨ Why BioPro?

| Feature | ImageJ | BioPro |
|---------|--------|--------|
| Western blot analysis | 20+ manual steps | **4-step guided wizard** |
| Lane detection | Manual rectangle placement | **Automatic** (with manual override) |
| Band quantification | Manual peak selection | **Auto-detect with adjustable sensitivity** |
| Interface | Java-era UI | **Modern dark theme** |
| Extensibility | Java plugins | **Python modules** — easy for scientists |
| Learning curve | Steep | **Gentle** — smart defaults, clear guidance |

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or later
- pip (Python package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/BioPro/biopro.git
cd biopro

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install BioPro and its dependencies
pip install -e ".[dev]"
```

### Run BioPro

```bash
# Launch the GUI
biopro

# Or run as a Python module
python -m biopro
```

## 📖 Usage

### Auto Western Blot Analysis (GUI)

1. **Load Image** — Open your western blot image (TIFF, PNG, JPG)
2. **Lane Setup** — Click "Auto-Detect" or set lane count manually
3. **Band Detection** — Adjust sensitivity slider to fine-tune peak detection
4. **Results** — View density bar chart, export to CSV/Excel

### Programmatic Analysis (Headless)

Use the analysis engine directly in Python scripts:

```python
from biopro.analysis import WesternBlotAnalyzer

analyzer = WesternBlotAnalyzer()
analyzer.load_image("my_blot.tif")
analyzer.preprocess(invert_lut="auto")
analyzer.detect_lanes(num_lanes=6)
analyzer.detect_bands(min_peak_height=0.1)
analyzer.compute_densitometry()

# Get results as a pandas DataFrame
results = analyzer.get_results()
print(results)

# Export
results.to_csv("densitometry_results.csv")
```

## 🏗️ Architecture

```
biopro/
├── analysis/          # Headless image processing engine
│   ├── western_blot.py    # Main WesternBlotAnalyzer pipeline
│   ├── image_utils.py     # Image loading, conversion, preprocessing
│   ├── lane_detection.py  # Lane boundary detection algorithms
│   └── peak_analysis.py   # Peak detection and densitometry
├── ui/                # PyQt6 desktop interface
│   ├── main_window.py     # Application main window
│   ├── image_canvas.py    # Zoomable/pannable image viewer
│   ├── western_blot_panel.py  # Analysis wizard panel
│   ├── results_widget.py  # Results display and export
│   └── theme.py           # Dark theme and styling
├── __init__.py
└── __main__.py        # Application entry point
```

**Key design principle:** The `analysis/` engine is fully independent of the `ui/` layer. You can use `analysis/` in scripts, notebooks, or build alternative frontends — the GUI is just one consumer of the analysis API.

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=biopro --cov-report=html
```

Sample test images are generated programmatically in `tests/` — no real lab data required.

## 🔌 Extending BioPro

BioPro is designed for extensibility. Each analysis type is a self-contained module:

1. Create a new module in `biopro/analysis/` (e.g., `cell_counter.py`)
2. Implement an analyzer class following the pattern in `WesternBlotAnalyzer`
3. Add a corresponding UI panel in `biopro/ui/`
4. Register the module in the main window

See the [Contributing Guide](#contributing) for detailed instructions.

## 🤝 Contributing

Contributions are welcome! BioPro follows standard Python best practices:

- **Code style**: [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- **Docstrings**: Google-style docstrings on all public functions and classes
- **Type hints**: Full type annotations throughout
- **Tests**: pytest with synthetic test data

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check biopro/

# Format
ruff format biopro/
```

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🗺️ Roadmap

- [x] Auto Western Blot Densitometry
- [ ] SDS-PAGE Gel Quantification
- [ ] Fluorescence Image Analysis
- [ ] Cell Counting & Morphometry
- [ ] Batch Processing Mode
- [ ] Plugin System for Community Extensions
