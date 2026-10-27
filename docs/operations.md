# 運用手順書

## 起動

```bash
cp .env.example .env      # 必要なら編集する(全設定の見本)
docker compose up --build
```

- 順序: Redis → バックエンド(マイグレーションを適用してから起動)→ ワーカー・フロントエンド(バックエンドが正常になってから)
- ダッシュボードは `http://localhost:8080`、API は `http://localhost:8000`(どちらも `127.0.0.1` にだけ公開)
- Redis はホストに公開しない(パスワードつき)。ホストから触る必要があるときだけ、開発用の上書きを使う: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`
- 観測性(Prometheus・Grafana)を足す: `docker compose -f docker-compose.yml -f docker-compose.observability.yml up`

実レンダー(Blender)にする場合は、ワーカーから見える場所に、シーンのルート・出力のルート・Blender の実行ファイルが要る。`RENDERER=blender`、`BLENDER_PATH`、`RENDER_SCENE_ROOT`、`RENDER_OUTPUT_ROOT` を設定する([ADR-0007](adr/0007-renderer-port-and-blender.md))。

## 状態の確認

| 確認 | 方法 | 正常 |
| --- | --- | --- |
| API とブローカー | `curl localhost:8000/healthz` | `{"status":"ok","redis":"ok"}`(`redis` が `unreachable` なら、Redis に繋がらない) |
| ワーカー | `docker compose ps`(ヘルスチェックは `celery inspect ping`)/ ダッシュボードのワーカーパネル | `healthy` |
| 件数 | `GET /metrics` の `queuewatch_jobs{status=...}` | 待機・リトライが増え続けない |
| ログ | `docker compose logs backend`(JSON の 1 行 1 件、`request_id` つき) | `level: ERROR` が出ていない |

## 障害対応

| 症状 | 原因と対処 |
| --- | --- |
| `POST /jobs` が 503 `Queue service unavailable` | Redis に繋がらない。`docker compose ps redis`、パスワード(`REDIS_PASSWORD`)がバックエンドとワーカーで同じか確認する。この間、DB には `pending` のまま孤立したジョブが残りうる(ワーカー再開後、`requeue` はできないため、`cancel` して投入し直す) |
| 401 / 403 | `token` モード。`Authorization: Bearer <token>` が要る。書き込みは editor 以上、削除は admin |
| 429 | レート制限。`Retry-After` の秒数だけ待つか、`QUEUEWATCH_RATE_LIMIT_*` を上げる |
| 413 / 411 | 本文が 16 KB を超える、または `Content-Length` が無い |
| ダッシュボードに「取得に失敗」 | API に繋がらない、または CORS。`QUEUEWATCH_CORS_ORIGINS` に画面のオリジン(`http://localhost:8080`)があるか確認する |
| ジョブが `dead` になった | 原因を調べて(ジョブ詳細のエラーとリトライ履歴)、デッドレターの画面から「再投入」(リトライ回数は 0 に戻る) |
| `running` のまま動かない | ワーカーが落ちた。`acks_late` のため、ワーカーの再起動で、メッセージが再配信される(冪等性のガードで二重処理はしない) |
| 実レンダーが `Blender could not be started` | `BLENDER_PATH` が、ワーカーのコンテナから見える場所にない |
| 実レンダーが `scene resolves to a path outside` | シーンは `RENDER_SCENE_ROOT` の内側の `.blend` に限る |

## キューが滞留したとき

1. `GET /metrics` で、`queuewatch_jobs{status="pending"}` と `queuewatch_jobs{status="retrying"}` の増え方を見る
2. **ワーカーが足りない**: `docker compose up -d --scale worker=3`。優先度の高いキューは、ワーカーが `queue_high` を先に見る(厳密な優先順位ではない、[ADR-0004](adr/0004-fixed-priority-queues.md))
3. **失敗が多い**: エラー種別(統計の画面、`/stats/errors`)を見て、原因を直す。失敗のジョブは、バックオフ(1 秒 → 2 秒 → 4 秒、最大 60 秒)で再試行し、3 回で `dead` になる
4. **不要なジョブを止める**: 待機・リトライ中のジョブは、「一時停止」「キャンセル」できる(実行中は、止められない)
5. 直ったら、一時停止のジョブは「再開」、`dead` と `cancelled` は「再投入」

## シャットダウンと更新

- ワーカーは、`SIGTERM` で、実行中のタスクを終えてから止まる(猶予 120 秒、`stop_grace_period`)。終わらなかったタスクは、`acks_late` のため、再配信される
- API は、20 秒の猶予で、受け付け済みの要求を終えてから止まる
- 更新: 新しい版のイメージで `docker compose up -d`。マイグレーションは、API の起動時に自動で適用される

## データ

| 内容 | 場所 |
| --- | --- |
| データベース(SQLite、WAL) | ボリューム `backend-data`(`/app/data/queuewatch.db`) |
| 実レンダーの出力 | `RENDER_OUTPUT_ROOT`(`job-<id>/frame_####.png`) |

バックアップは、SQLite の `backup` API で、整合した複製を作る(`cp` でコピーしない。WAL の途中の内容が混ざる)。

```bash
docker compose exec backend python -c "import sqlite3; s=sqlite3.connect('/app/data/queuewatch.db'); d=sqlite3.connect('/app/data/backup.db'); s.backup(d)"
docker compose cp backend:/app/data/backup.db ./backup-$(date +%F).db
```

復旧: `docker compose down` → ボリュームの `queuewatch.db` を置き換える → `docker compose up`(起動時にマイグレーションが走り、古いバックアップでも最新の形になる)。

マイグレーション導入前(0.1.0 以前)のデータベースは、`docker compose run --rm backend python -m app.migrate stamp 0001` で「適用済み」にしてから使う。

## 設定

すべての環境変数は [`.env.example`](../.env.example) にある。不正な設定は、起動時に例外で止まる。
