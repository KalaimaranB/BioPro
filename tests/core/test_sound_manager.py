from biopro.core.sound_manager import sound_manager


def test_sound_manager_playback(qtbot):
    """Verifies that sound manager methods execute without errors.
    Actual audio output is hard to verify in headless, but we ensure no crashes.
    """
    sound_manager.play_beep()
    sound_manager.play_hyperspace()
