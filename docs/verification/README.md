# 実機検証の記録

疑似ではなく、実際の DCC を動かしたときの記録。CI は疑似レンダーで通る(実機は CI に載せない)。

| 対象 | 実施日 | 結果 | 記録 |
| --- | --- | --- | --- |
| Blender 3.6.0 | 2026-10-28 | 6/6 PASS | [blender-render-3.6.0.md](blender-render-3.6.0.md) |
| Blender 4.0.0 | 2026-10-28 | 6/6 PASS | [blender-render-4.0.0.md](blender-render-4.0.0.md) |
| Blender 4.5.3 | 2026-10-28 | 6/6 PASS | [blender-render-4.5.3.md](blender-render-4.5.3.md) |
| Blender 5.0.0 | 2026-10-28 | 6/6 PASS | [blender-render-5.0.0.md](blender-render-5.0.0.md) |

## 手順

`BLENDER_APP=<Blender.app のパス> python scripts/verify_blender_render.py`(backend の venv)。結果は 1 行 1 項目の `CHECK <名前> <PASS|FAIL> <詳細>`。新しい版を足すときは、出力を `blender-render-<版>.md` に記録し、この表に 1 行足す。

## 分割ジョブ(frame-slicer)との関係

frame-slicer が作るジョブは、名前と優先度だけで、シーンとフレーム範囲を持たない。実レンダーでは `scene` が必須(422)のため、そのまま実レンダーにはならない。frame-slicer 側で `scene` / `frame_start` / `frame_end` を送る変更が要る(frame-slicer のタスクで対応する)。
