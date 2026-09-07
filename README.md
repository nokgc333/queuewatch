# QueueWatch

Celery + Redisで動く分散レンダーファーム風のジョブキュー監視ダッシュボード。優先度別キューイング・自動リトライ（指数バックオフ）・デッドレターキューを、実際に動くコードで証明するプロジェクトです。

**重要な注意**: QueueWatchは**疑似レンダーファーム**です。実際のHoudini/Nukeレンダリングは一切行いません（[ADR-0002](docs/adr/0002-simulated-render-farm.md)）。`backend/app/tasks.py`の`process_render_job`は`time.sleep()`でジョブの複雑度に応じた処理時間をシミュレートし、一定確率（既定10%）で意図的に失敗させることで、分散タスクキューの核心である「キューイング → ワーカー処理 → リトライ → デッドレターキュー」という設計を再現性高く実演します。

## 目的・背景

CGパイプライン開発では、レンダーファームのジョブキュー管理・失敗時の自動リトライ・ワーカー稼働状況の可視化が実務上の重要課題です。QueueWatchはこれをCelery + Redisという業界標準の分散タスクキュー基盤で実装し、優先度キューイング・指数バックオフ・冪等性設計・アプリケーションレベルDLQといった分散システムの基礎設計を、正直に「疑似」であることを明記した上で実装として示します。

詳細な要件定義・設計判断は [docs/要件定義書.md](docs/要件定義書.md) / [docs/仕様書.md](docs/仕様書.md) / [docs/adr/](docs/adr/) を参照してください。

## アーキテクチャ

```
Web Browser / Houdini Python Shell
        │ HTTP (REST/JSON, ポーリング)
        ▼
FastAPI Backend (:8000) ──publish──▶ Redis (:6379, Broker + Result Backend)
        │ CRUD/集計                          │ deliver
        ▼                                    ▼
   SQLite (queuewatch.db)  ◀──状態更新── Celery Worker (process_render_job)
```

- **同期**: ジョブ登録（`POST /jobs`）と一覧・詳細・統計の取得はすべて同期API（DB読み書きのみ、即座に応答）
- **非同期**: ジョブの実処理（疑似レンダリング）はCeleryワーカー上で非同期実行。フロントエンドは3秒間隔のポーリングで結果を確認（WebSocketは不採用、[ADR-0005](docs/adr/0005-polling-over-websocket.md)）

この「登録は同期・高速」「実処理は非同期・低速」という分離が設計の核です。

## 構成

```
queuewatch/
├── frontend/   React 19 + Vite + TypeScript + Tailwind CSS v4（ジョブボード・統計ダッシュボード）
├── backend/    FastAPI + Celery + SQLAlchemy + SQLite（REST API + 分散タスクキュー）
├── scripts/    houdini_submit_job.py（HoudiniからのFR-007連携）
└── docs/       要件定義書・仕様書・ADR
```

## 技術スタック

- **backend**: FastAPI / Celery / Redis / SQLAlchemy 2.0 / Pydantic v2 / pytest / mypy(strict)
- **frontend**: React 19 / Vite / TypeScript(strict) / Tailwind CSS v4 / Chart.js(react-chartjs-2) / Vitest + Testing Library
- **scripts**: requests のみ（hou非依存、どのPython環境からでも実行可能）
- **infra**: Docker Compose（Redis / backend / worker / frontend）

## インストール・起動（ローカル）

```bash
# Redis
redis-server --port 6379

# バックエンド
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed           # デモデータ投入
uvicorn app.main:app --reload --port 8000

# Celeryワーカー（別ターミナル）
cd backend && source .venv/bin/activate
celery -A app.worker worker -Q queue_high,queue_normal,queue_low --concurrency=4 --loglevel=info

# フロントエンド（別ターミナル）
cd frontend
npm install
npm run dev
```

`http://localhost:5173` でダッシュボードが表示されます。APIドキュメントは `http://localhost:8000/docs`。

### Docker Composeで起動する場合

```bash
docker compose up --build
```

### Houdiniからジョブを投入する

Houdiniの Python Shell で:

```python
import sys
sys.path.append("/path/to/queuewatch/scripts")
from houdini_submit_job import submit_job
submit_job("http://localhost:8000", "SHOT010_render", "high")
```

## テスト

```bash
# バックエンド（57テスト、カバレッジ98%）
cd backend && CELERY_TASK_ALWAYS_EAGER=true pytest --cov=app --cov-report=term-missing

# フロントエンド（77テスト、カバレッジ99%）
cd frontend && npx vitest run --coverage
npx tsc --noEmit

# Houdini連携スクリプト（7テスト、hou非依存）
cd scripts && pytest tests/ -v
```

### Lint

```bash
# バックエンド
cd backend && black --check . && isort --check . && flake8 app/ tests/ && mypy app/

# フロントエンド
cd frontend && npx eslint . && npx tsc --noEmit
```

Celery統合テストは`CELERY_TASK_ALWAYS_EAGER=true`環境変数によりワーカーを別プロセス起動せず同期実行する（Celery公式のテスト推奨パターン）。ただし、eagerモードの`apply()`は実際のワーカー再配信を自動シミュレートしないため（1回の呼び出し = 1回の試行）、複数回のリトライを経てdead状態に至る挙動は`apply()`を手動で複数回呼び出して検証している（`backend/tests/test_tasks.py`参照）。実際の指数バックオフ間隔（1秒→2秒→4秒）は実ワーカープロセスのログのタイムスタンプで目視確認する運用とした。

## Design Decisions

- **Celery + Redisを分散タスクキュー基盤として採用**（[ADR-0001](docs/adr/0001-celery-and-redis.md)）: 自前実装は「車輪の再発明」であり、業界標準ツールの設計思想を理解していることを示す目的に反するため、Pythonの事実上の標準であるCeleryを採用。ブローカー抽象化により将来RabbitMQ/SQSへの移行余地も残す
- **疑似レンダーファームの採用**（[ADR-0002](docs/adr/0002-simulated-render-farm.md)）: 実レンダリングエンジン統合は環境構築コスト・実行時間の制約に見合わないと判断。処理時間を正規分布(2〜15秒)でシミュレートし、意図的な疑似失敗率(既定10%)でリトライ・DLQのデモを再現性高く実演する設計とした
- **指数バックオフはCelery標準機能をそのまま使用**（仕様書§8.1）: `retry_backoff=True`の内部計算式(`delay = min(backoff_max, 2**retries * backoff_base)`)をアプリ層で再実装せず、テスト・検証済みのCelery実装に委ねることで保守性・信頼性を優先
- **優先度キューを3段階固定に**（[ADR-0004](docs/adr/0004-fixed-priority-queues.md)）: Redisブローカーでのメッセージ単位優先度サポートが限定的なため、`queue_high`/`queue_normal`/`queue_low`の3つの物理キューに分離し、ワーカー起動時のキュー列挙順で疑似的な優先度制御を実現。グローバルな優先順序の厳密な保証はない
- **WebSocketではなくポーリングを採用**（[ADR-0005](docs/adr/0005-polling-over-websocket.md)）: 3秒間隔ポーリングで実装をシンプルに保ち、接続再接続管理の複雑さを回避
- **SQLiteをv1の正本DBに、WALモードを有効化**（[ADR-0003](docs/adr/0003-sqlite-as-primary-db.md)）: 複数Celeryワーカーからの並行書き込みを考慮し`PRAGMA journal_mode=WAL`を有効化して読み取り-書き込み競合を緩和
- **フロントエンドはNext.jsではなくVite**（[ADR-0006](docs/adr/0006-vite-over-nextjs.md)）: SSR不要な内部ダッシュボード用途のため、姉妹プロジェクトPipeBoardと差別化しシンプルな構成を選択
- **アプリケーションレベルDLQ**（仕様書§10.4）: RedisブローカーがブローカーレベルのDLQ機構を十分サポートしないため、`jobs.status="dead"`というDBフィールドを正としたシンプルな実装にした
- **冪等性ガード**（仕様書§10.5）: `task_acks_late=True`によるat-least-once配信でワーカークラッシュ時にタスクが再配信されても、`status="success"`チェックで二重処理を防止

## 既知の制限事項（Not in scope, v1）

- **実レンダリングとの統合なし**: 前述の通り疑似シミュレーションのみ。ファイル入出力・GPU/CPUリソース管理・ライセンスサーバー連携の実装経験は示せない
- **真の優先度スケジューリングの非保証**: 複数ワーカープロセスが並行して異なるキューを消費する場合、グローバルな優先順序は保証されない（[ADR-0004](docs/adr/0004-fixed-priority-queues.md)）
- **手動再投入UIなし**: SCR-004（デッドレターキュービュー）はdeadジョブの一覧表示のみで、再投入は「同名で再度POSTしてください」という運用ガイド表示に留まる（Could優先度FR-010はv1スコープ外）
- **ページネーション未実装**: `GET /jobs`は現状全件返却。`JobListParams`にlimit/offsetの型のみ先行して用意している
- **認証なし**: 全APIエンドポイントが認証不要（要件定義書§5.2の判断）
- **Redis接続不可時の孤立レコード**: `POST /jobs`のDB INSERTには成功しCeleryへのpublishに失敗した場合、DB上に`status="pending"`のまま進行しないレコードが残りうる。ワーカー再起動でも自動的には再配信されない（v1の許容リスク）
- **Celery eagerモードでのテストの限界**: `apply()`は実ワーカーの複数回再配信を自動シミュレートしないため、`backend/tests/test_tasks.py`ではdead到達までの複数回試行を手動ループで模擬している。実際の指数バックオフ間隔の実測は手動確認（実ワーカーログのタイムスタンプ）に依存し、CI化していない
- **実機検証・負荷テストは未実施**: Houdini実機での`houdini_submit_job.py`動作確認、ジョブ数増加時のSQLite書き込み遅延の実測は本README執筆時点で行っていない（捏造しない方針）

## ライセンス

MIT License（[LICENSE](LICENSE)参照）
