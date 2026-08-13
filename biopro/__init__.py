"""Temporary compatibility shim for the ``biopro`` -> ``karcytics`` rename.

biopro_sdk (published separately, not yet renamed) has soft/optional imports
of a few ``biopro.*`` modules for deeper integration when running inside the
full desktop app (undo/redo history, resource inspection, shared theming,
image utilities). Those imports fail gracefully to degraded mocks when
``biopro`` isn't importable, which is now *always* true post-rename unless
this shim exists.

Delete this whole ``biopro/`` directory once ``Karcytics-SDK`` is renamed and
republished with its internal imports updated to ``karcytics.*`` -- at that
point nothing references these modules anymore.
"""
