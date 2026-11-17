# mondo-insta-auto

主水有楽町店（@mondo.yurakucho）の Instagram / Facebook ページへの自動投稿。

## しくみ

- GitHub Actions が **15分ごと** に `schedule.csv` を確認する
- 投稿時刻を過ぎていて、まだ出していない予定があれば投稿する
- 投稿したものは `posted.json` に記録される（二重投稿しない）
- PC を閉じていても動く

## 予定の追加のしかた

1. 画像・動画を `media/` に入れる
   - フィード写真：1080×1350（縦4:5）の JPEG、8MB まで
   - ストーリーズ：1080×1920（縦9:16）の JPEG
   - 動画：MP4（フィードではリールとして出る）
2. キャプションを `captions/` にテキストファイルで入れる（ストーリーズは不要）
3. `schedule.csv` に1行追加する

```csv
datetime,type,media,caption,targets
2026-12-01 11:30,feed,20261201_feed.jpg,20261201_feed.txt,"ig,fb"
2026-12-01 17:00,story,20261201_story.jpg,,"ig,fb"
```

| 列 | 内容 |
|---|---|
| datetime | 投稿日時（日本時間、`YYYY-MM-DD HH:MM`） |
| type | `feed`（フィード／リール）か `story`（ストーリーズ） |
| media | `media/` の中のファイル名 |
| caption | `captions/` の中のファイル名（ストーリーズは空でOK） |
| targets | `ig`、`fb`、または `ig,fb` |

## 注意

- 投稿時刻から **6時間以上** 過ぎた予定は、古い投稿が急に出ないようにスキップする
- 投稿は GitHub の混み具合で **最大15〜30分ほど遅れる** ことがある
- 失敗すると GitHub から登録メールに通知が届く
- 投稿用の鍵（アクセストークン）は Settings → Secrets → `META_TOKEN` に入っている。ここ以外には絶対に書かない

## 接続確認

Actions → auto-post → Run workflow → mode を `check` にして実行すると、投稿せずに
「Facebookページ／Instagramにつながるか」と「次の予定」だけ確認できる。
