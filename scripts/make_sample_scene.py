"""検証用の小さな .blend を作る。`blender -b --python scripts/make_sample_scene.py -- <出力パス>`

立方体を 1 つ、Workbench(GPU 不要で速い)、64x64、frame 1〜4 の回転のアニメーション。
"""

from __future__ import annotations

import sys

import bpy

output = sys.argv[sys.argv.index("--") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 64
scene.render.resolution_y = 64
scene.render.resolution_percentage = 100
scene.frame_start = 1
scene.frame_end = 4

bpy.ops.mesh.primitive_cube_add()
cube = bpy.context.active_object
for frame in range(1, 5):
    cube.rotation_euler[2] = frame * 0.4
    cube.keyframe_insert(data_path="rotation_euler", frame=frame)

bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.8))
scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type="SUN", location=(2, 2, 5))

bpy.ops.wm.save_as_mainfile(filepath=output)
