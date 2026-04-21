"""Tests for the ProgrammaticLoader (DNA Helix) widget."""

import math
import pytest
from PyQt6.QtCore import Qt
from biopro.ui.widgets.dna_loader import ProgrammaticLoader
from biopro.ui.theme import Colors

@pytest.fixture
def loader(qtbot):
    """Fixture for ProgrammaticLoader widget."""
    widget = ProgrammaticLoader()
    qtbot.addWidget(widget)
    return widget

class TestDNALoader:
    """Test suite for the DNA helix animation widget."""

    def test_initial_state(self, loader):
        """Verifies initial configuration of the loader."""
        assert loader.angle == 0.0
        assert len(loader.binary_bits) == 12
        assert len(loader.dust) == 25
        assert loader.minimumWidth() >= 250

    def test_glyph_pool_selection(self, loader, monkeypatch):
        """Verifies that the glyph pool changes based on the theme color."""
        # 1. Test Default Theme (cyan)
        monkeypatch.setattr(Colors, "DNA_PRIMARY", "#00f2ff")
        assert loader._glyph_pool == ["0", "1"]
        
        # 2. Test 'Dark Side' Theme (imperial red #E60000)
        # Note: We use .upper() in the code logic
        monkeypatch.setattr(Colors, "DNA_PRIMARY", "#E60000")
        pool = loader._glyph_pool
        assert "ᚙ" in pool
        assert "0" not in pool

    def test_make_bit_structure(self, loader):
        """Verifies the internal data structure of a binary bit stream."""
        bit = loader._make_bit()
        assert "x" in bit
        assert "y" in bit
        assert "chars" in bit
        assert len(bit["chars"]) >= 2
        assert 0.0 <= bit["x"] <= 1.5 # Path can be slightly offscreen

    def test_update_animation_cycle(self, loader):
        """Verifies that calling update_animation advances the state."""
        initial_angle = loader.angle
        loader._update_animation()
        assert loader.angle > initial_angle
        # Pulse is sin(angle * 0.8) * 0.1, so it should change from 0.0
        assert loader.pulse != 0.0

    def test_theme_swap_refresh(self, loader, monkeypatch):
        """Tests the logic that automatically refreshes bit glyphs on theme change."""
        # Force a known state
        monkeypatch.setattr(Colors, "DNA_PRIMARY", "#00f2ff")
        loader.binary_bits[0]['chars'] = ["0"]
        
        # Swap to Sith theme
        monkeypatch.setattr(Colors, "DNA_PRIMARY", "#E60000")
        
        # The animation loop should detect that "0" is not in the new pool and swap it
        loader._update_animation()
        
        new_char = loader.binary_bits[0]['chars'][0]
        assert new_char in loader._glyph_pool
        assert new_char != "0"

    def test_dust_particle_logic(self, loader):
        """Verifies dust particles have variations."""
        assert len(loader.dust) == 25
        d = loader.dust[0]
        assert 0 <= d['x'] <= 1
        assert 0 <= d['y'] <= 1
        assert 'size_mult' in d
        assert 'flicker' in d

    def test_resize_event_smoke(self, loader):
        """Ensures resizing the widget doesn't cause math errors in paint metrics."""
        loader.resize(500, 500)
        # Force a paint to trigger coordinate math
        loader.repaint()
        assert loader.width() == 500
