# ADR-0006: フロントエンドにNext.jsではなくViteを採用（SSR不要な管理画面用途）

## Status
Accepted (2026-09-07)

## Context
姉妹プロジェクトPipeBoard miniはNext.js(App Router)を採用しているが、
QueueWatchのフロントエンドは純粋な管理画面・統計ダッシュボード用途であり、
SEO・SSR(サーバーサイドレンダリング)を必要としない。

## Decision
Viteをビルドツールとして採用し、Next.jsは使用しない。React + TypeScriptの
コンポーネント設計自体はPipeBoardのパターンを踏襲しつつ、ルーティングは
react-router、ビルドはViteのシンプルな構成とする。

## Consequences
良い: ビルド・開発サーバーの起動が高速。SSR関連の設定(データフェッチ戦略、
     hydration等)を考慮する必要がなく、実装がシンプルになる。「用途に
     応じてSSRの要否を判断し技術選定を変える」という判断プロセスを
     ポートフォリオとして示せる
悪い: Next.jsのファイルベースルーティング・Image最適化等の機能は使えない。
     ただし本プロジェクトの用途(内部ダッシュボード)ではこれらの機能の
     必要性が薄いため、実質的な悪影響は小さいと判断

## Alternatives Considered
- Next.js(PipeBoardと統一): 技術スタックの一貫性は高まるが、SSR不要な
  用途にNext.jsのフル機能を使う理由が説明できず、「なんとなく前と同じ
  技術を選んだ」という印象を与えるリスクがあるため、あえて差別化した
