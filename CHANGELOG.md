# Changelog

形式は [Keep a Changelog](https://keepachangelog.com/) に、版の付け方は [Semantic Versioning](https://semver.org/) に従う。

## [0.2.0] - 2026-10-28

### Added

- トークン認証(`local` / `token`)・ロール(viewer / editor / admin)・レート制限・本文の大きさの上限
- レンダラーのポート: 疑似(既定)と実 Blender(`RENDERER=blender`)。ジョブに `scene` とフレーム範囲、進捗と出力先
- JSON の構造化ログ(リクエスト ID つき)、Prometheus の `/metrics`、OpenTelemetry のトレース(任意)、Grafana のダッシュボード例
- Alembic のマイグレーション、`/healthz` のほかにワーカーのヘルスチェック、グレースフルシャットダウンの設定
- GHCR へのイメージ公開(タグから)、Dependabot、pre-commit、`.env.example`
- ダッシュボードの実行時設定(`/config.js`。同じイメージを環境ごとに作り直さない)

### Changed

- Redis は、既定でホストに公開せず、パスワードを設定。開発用の上書きファイルで公開する
- ダッシュボードは、非 root の nginx で配信(CSP つき)。バックエンドのイメージも非 root
- CORS の既定は、ローカルのダッシュボードだけ(`*` は明示したときだけ)

## [0.1.0]

- 最初の版: ジョブ盤・ワーカー・統計・デッドレター、疑似レンダー、再試行とバックオフ
