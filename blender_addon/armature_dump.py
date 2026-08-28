"""Build the armature-dump document the desktop app imports.

Standard library only -- no ``bpy``, so it can be unit-tested outside
Blender. The ``bpy`` side lives in :mod:`blender_addon.armature_export`.

The document lists a target armature's bone names so the app can guess a
canonical-to-rig bone mapping. It carries no animation.
"""

import json

ARMATURE_DUMP_FORMAT = "mcap_armature"
ARMATURE_DUMP_VERSION = 1


def build_dump_document(armature_name, bones, up_axis="Z", unit_scale=1.0):
    """Return the armature-dump document for ``bones``.

    Args:
        armature_name: The armature object's name.
        bones: An iterable of ``(bone_name, parent_name_or_None)`` pairs.
        up_axis: The rig's up axis ("Z" for Blender).
        unit_scale: Metres per rig unit.

    Returns:
        A JSON-serialisable dict.
    """

    return {
        "format": ARMATURE_DUMP_FORMAT,
        "version": ARMATURE_DUMP_VERSION,
        "armature_name": str(armature_name),
        "up_axis": str(up_axis),
        "unit_scale": float(unit_scale),
        "bones": [
            {"name": str(name), "parent": (str(parent) if parent else None)}
            for name, parent in bones
        ],
    }


def write_dump(path, document):
    """Write ``document`` to ``path`` as UTF-8 JSON."""

    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2)
