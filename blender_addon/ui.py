"""Blender operator and File > Import menu entry for mcapclip files."""

import bpy
from bpy_extras.io_utils import ImportHelper

from . import importer, mcapclip


class MCAPCLIP_OT_import(bpy.types.Operator, ImportHelper):
    """Import a .mcapclip.json animation onto the active armature."""

    bl_idname = "import_scene.mcapclip"
    bl_label = "Import AI Mocap Clip"
    bl_options = {"REGISTER", "UNDO"}  # noqa: RUF012 - Blender operator API idiom

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: "bpy.types.Context") -> set[str]:
        armature = context.active_object

        if armature is None or armature.type != "ARMATURE":
            self.report({"ERROR"}, "Select an armature first")
            return {"CANCELLED"}

        try:
            clip = mcapclip.load_clip(self.filepath)
        except mcapclip.McapClipError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        touched = importer.apply_clip_to_armature(
            armature, clip, bone_map=clip.bone_map
        )
        self.report(
            {"INFO"},
            f"Imported {len(clip.frames)} frames onto {touched} bone(s)",
        )
        return {"FINISHED"}


def _file_import_entry(self: "bpy.types.Menu", context: "bpy.types.Context") -> None:
    self.layout.operator(
        MCAPCLIP_OT_import.bl_idname, text="AI Mocap Clip (.mcapclip.json)"
    )


def register() -> None:
    bpy.utils.register_class(MCAPCLIP_OT_import)
    bpy.types.TOPBAR_MT_file_import.append(_file_import_entry)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(_file_import_entry)
    bpy.utils.unregister_class(MCAPCLIP_OT_import)
