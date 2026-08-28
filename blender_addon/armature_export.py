"""Blender operator exporting the active armature's bone names.

The resulting file feeds the desktop app's "Import rig..." action, which
turns it into a rig profile.
"""

import bpy
from bpy_extras.io_utils import ExportHelper

from . import armature_dump


class MCAP_OT_export_armature(bpy.types.Operator, ExportHelper):
    """Export the active armature's bones as a Motion Capture rig file."""

    bl_idname = "export_scene.mcap_armature"
    bl_label = "Export AI Mocap Rig"
    bl_options = {"REGISTER"}  # noqa: RUF012 - Blender operator API idiom

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: "bpy.types.Context") -> set[str]:
        armature = context.active_object

        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Select an armature first")
            return {"CANCELLED"}

        bones = [
            (bone.name, bone.parent.name if bone.parent else None)
            for bone in armature.data.bones
        ]

        if not bones:
            self.report({"ERROR"}, "That armature has no bones")
            return {"CANCELLED"}

        document = armature_dump.build_dump_document(
            armature.name,
            bones,
            up_axis="Z",
            unit_scale=float(context.scene.unit_settings.scale_length),
        )

        try:
            armature_dump.write_dump(self.filepath, document)
        except OSError as error:
            self.report({"ERROR"}, f"Could not write the file: {error}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported {len(bones)} bone(s)")
        return {"FINISHED"}


def _file_export_entry(self: "bpy.types.Menu", context: "bpy.types.Context") -> None:
    self.layout.operator(
        MCAP_OT_export_armature.bl_idname, text="AI Mocap Rig (.json)"
    )


def register() -> None:
    bpy.utils.register_class(MCAP_OT_export_armature)
    bpy.types.TOPBAR_MT_file_export.append(_file_export_entry)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_export.remove(_file_export_entry)
    bpy.utils.unregister_class(MCAP_OT_export_armature)
