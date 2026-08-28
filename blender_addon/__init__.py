"""AI Mocap -- import a ``.mcapclip.json`` animation onto a Blender armature.

This add-on is a standalone package: it imports only ``bpy`` and the
standard library, and never anything from the desktop application (``app``).
Communication with the app is strictly file-based.

The pure logic (file parsing, coordinate conversion, armature-dump
building) lives in :mod:`blender_addon.mcapclip`,
:mod:`blender_addon.conversion` and :mod:`blender_addon.armature_dump` and
imports only the standard library, so it can be unit-tested without
Blender. The Blender-facing operators and menu entries live in
:mod:`blender_addon.ui` and :mod:`blender_addon.armature_export` and are
imported lazily by :func:`register`.
"""

bl_info = {
    "name": "AI Mocap Clip Importer",
    "author": "AI Motion Capture",
    "version": (1, 1, 0),
    "blender": (3, 6, 0),
    "location": "File > Import > AI Mocap Clip, File > Export > AI Mocap Rig",
    "description": (
        "Import a .mcapclip.json animation onto the active armature, and "
        "export an armature's bones as a rig profile source"
    ),
    "category": "Import-Export",
}


def register() -> None:
    """Register the add-on's Blender classes."""

    from . import armature_export, ui

    ui.register()
    armature_export.register()


def unregister() -> None:
    """Unregister the add-on's Blender classes."""

    from . import armature_export, ui

    armature_export.unregister()
    ui.unregister()
