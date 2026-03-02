[English](README.md) | [한국어](README.ko.md) | 日本語

# justsell

Claude Code 向けのローカルファーストなマーケティング自動化プラグインです。

Threads、Instagram カードニュース、Remotion 動画ワークフローをローカルコンソールで生成・レンダリング・確認し、明示的な確認後にのみ公開します。

[クイックスタート](#クイックスタート) | [コマンド](#コマンドリファレンス) | [設定ドキュメント](docs/CONFIG.md) | [ワークフロー](docs/WORKFLOW.md)

## クイックスタート

1) インストール
```bash
/plugin marketplace add https://github.com/ubermensch1218/justsell
/plugin install justsell
```

2) 初期設定
```bash
/justsell:js init
```

3) コンソール起動
```bash
/justsell:js console
```

任意: ガイド付きオンボーディング
```bash
/justsell:onboard
```

## 主要ワークフロー

| ワークフロー | エントリーポイント | 結果 |
|--------------|--------------------|------|
| セットアップ | `justsell-setup` / `/justsell:js init` | ローカル設定保存 + OAuth/Setup 開始 |
| コンソール | `console-start` / `/justsell:js console` | `http://127.0.0.1:5678/` ダッシュボード起動 |
| カードニュース | `instagram-cardnews` / `/justsell:js cardnews` | カードニュース仕様生成 + PNG レンダリング |
| Remotion | `/justsell:js remotion` | 動画仕様生成 + MP4 レンダリング |
| オンボーディング | `/justsell:onboard` | 1ステップずつ初期ガイド |

## コマンドリファレンス

| コマンド | 説明 |
|----------|------|
| `/justsell:js init` | ローカル設定初期化と Setup モード開始 |
| `/justsell:js console` | JustSellConsole 起動 |
| `/justsell:js cardnews` | Instagram カードニュース生成/レンダリング |
| `/justsell:js remotion` | Instagram Remotion 動画生成/レンダリング |
| `/justsell:onboard` | ガイド付きオンボーディング |

## デフォルト保存先

- 設定/トークン: `~/.claude/.js/config.json`
- コンソールログ/イベント: `~/.claude/.js/console/`
- プロジェクト: `~/.claude/.js/projects/`

## 主な環境変数

- `CLAUDE_CONFIG_DIR`
- `CLAUDE_PLUGIN_ROOT`
- `JUSTSELL_HOME`
- `JUSTSELL_CONFIG_PATH`
- `JUSTSELL_PROJECTS_DIR`
- `JUSTSELL_CONSOLE_HOST`
- `JUSTSELL_CONSOLE_PORT`
- `JUSTSELL_PUBLIC_BASE_URL`
- `JUSTSELL_FONT_PATH`
- `JUSTSELL_THREADS_APP_ID`, `JUSTSELL_THREADS_APP_SECRET`, `JUSTSELL_THREADS_REDIRECT_URI`
- `JUSTSELL_META_APP_ID`, `JUSTSELL_META_APP_SECRET`, `JUSTSELL_IG_REDIRECT_URI`, `JUSTSELL_GRAPH_API_VERSION`

詳細は [README.md](README.md) の Environment Variables セクションを参照してください。
