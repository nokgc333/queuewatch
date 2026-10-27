# Blender 4.5.3 での実レンダー検証

> 実施日: 2026-10-28
> 環境: macOS(Apple Silicon)/ `/Applications/Blender_v4.5.3.app`
> 対象: `RENDERER=blender`(`app/renderers.py`の `BlenderRenderer`)。Celery は eager(同期)、Redis は使わない

## 手順

```bash
BLENDER_APP=/Applications/Blender_v4.5.3.app python scripts/verify_blender_render.py
```

`scripts/make_sample_scene.py` が、立方体 1 つ・Workbench・64x64・4 フレームの `.blend` を作る。そのシーンを `POST /jobs` で投入し、ワーカーのタスクが `blender -b <scene> -s 1 -e 4 -a` を動かす。

## 結果(全 6 項目 PASS)

```text
a_path_outside_the_scene_root_is_rejected PASS 422
job_reaches_success PASS success
progress_is_100 PASS 100
four_frames_are_written PASS 4 files
frames_are_pngs PASS 
frames_are_not_empty PASS 
```

## 観察

- 許可ルートの外を指すシーン(`../../etc/passwd.blend`)は、投入の時点で 422 になり、キューにも載らない
- 進捗は、Blender の `Fra:<n>` の出力から取り込み、完了時に 100 になる
- 出力は、`<出力ルート>/job-<id>/frame_####.png`
