# ADR-0007: レンダラーをポートにして、疑似と実 Blender を切り替える(ADR-0002 を置き換える)

## Status
Accepted (2026-10-28). Supersedes [ADR-0002](0002-simulated-render-farm.md) の「実レンダリングは行わない」。疑似レンダーは、既定のまま残す。

## Context
疑似レンダー(`sleep` と確率的な失敗)は、キュー・再試行・デッドレターの検証には十分だが、「実際の仕事を動かせる」ことは示せない。
実レンダラーは、利用者が渡したパスから外部プロセスを起動するため、安全性を設計に含める必要がある。

## Decision
- `Renderer` ポート(`render(request, on_progress) -> RenderResult`)を定義し、`SimulatedRenderer`(既定)と `BlenderRenderer` を実装する。`RENDERER=simulated|blender` で切り替える。
- ジョブは、`scene`(許可ルートからの相対パス)・`frame_start`・`frame_end` を持つ。実レンダーでは `scene` が必須で、投入の時点で検証して 422 にする(キューに載せない)。
- `BlenderRenderer` は `blender -b <scene> -noaudio -o <out>/frame_#### -F PNG -s <start> -e <end> -a` を実行し、`Fra:<n>` の出力から進捗(0〜100)を取り込む。出力は `<出力ルート>/job-<id>/`。
- 安全性: シーンは許可ルート内の `.blend` に限る(`..`・絶対パス・外を指すシンボリックリンク・`-` で始まる名前・NUL を拒否)。コマンドはリストで渡しシェルを使わない。子プロセスの環境変数は、ワーカーの秘密(トークン・ブローカーの URL)を含まない許可リストだけ。制限時間(`RENDER_TIMEOUT_SECONDS`)で強制終了する。Celery の時間制限は、実レンダーではそれより長くする。
- 失敗(非ゼロ終了・出力フレームなし・時間切れ)は `RenderError`(`RuntimeError`)で、既存の再試行・バックオフ・デッドレターの経路にそのまま乗る。

## Alternatives
- **OpenCue / Deadline のアダプタ**: 同じ `Renderer` ポートの実装として足せる設計にした。ただし、どちらも別のサーバー(ファーム)が要り、このプロジェクトの規模では運用の負担が大きいため、今回は実装しない。足すときは、`render()` がファームへの投入と進捗の取得を担う。

## Consequences
良い: 同じ骨格(再試行・DLQ・冪等性)で、疑似と実の両方が動く。実機で Blender 3.6.0 / 4.0.0 / 4.5.3 / 5.0.0 の投入から出力までを確認した(`docs/verification/`)。CI は疑似のまま通る。
悪い: Blender のパス・シーンのルート・出力のルートは、ワーカーから見える場所に置く必要がある(コンテナでは、ボリュームの共有)。
      進捗は、フレーム単位の粗さ(1 フレームの途中は分からない)。
      frame-slicer が作るジョブは、`scene` を送るよう変える必要がある。
