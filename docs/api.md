# API 一覧

`python -m app.export_api_doc ../docs/api.md` で、実際の API から生成する(手で編集しない。
テストが、実際の API と一致していることを確かめる)。完全な定義は、起動中の `/docs`(Swagger UI)と
`frontend/openapi.json` にある。

ロールは、必要な最小の権限。`token` モードで、未認証は 401、権限不足は 403。
`local` モードでは、すべて管理者として扱う。


## health

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/healthz` | なし | ヘルスチェック（Redis接続確認を含む、仕様書§5.2参照）。 |
| GET | `/metrics` | viewer | Prometheus のスクレイプ用(ジョブの件数は DB から、HTTP の件数はプロセス内から)。 |

## jobs

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/jobs` | viewer | ジョブ一覧(`q` は名前の部分一致、`status` / `priority` で絞り込み、`limit` / `offset` でページング)。 |
| POST | `/jobs` | editor | ジョブを登録し、優先度に応じたキューへpublishする（FR-001/006）。 |
| GET | `/jobs/{job_id}` | viewer | get job |
| DELETE | `/jobs/{job_id}` | admin | ジョブを削除する（retry_logsもカスケード削除、仕様書§4.4）。 |
| POST | `/jobs/{job_id}/{action}` | editor | ジョブを、キャンセル・一時停止・再開・再投入する(cancel / pause / resume / requeue)。 |

## stats

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/stats/duration` | viewer | 処理時間分布統計（FR-008）。jobs.started_at〜finished_atからヒストグラムを生成する。 |
| GET | `/stats/errors` | viewer | エラー種別集計（FR-005）。retry_logs.error_messageを分類集計する。 |
| GET | `/stats/utilization` | viewer | ワーカー稼働率統計（FR-008）。worker_name単位の最新ウィンドウを集計する。 |

## workers

| メソッド | パス | ロール | 概要 |
| --- | --- | --- | --- |
| GET | `/workers/status` | viewer | ワーカーごとの直近ウィンドウの稼働率・処理件数を返す（FR-003）。 |
