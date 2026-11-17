#!/usr/bin/env python3
"""
主水有楽町店 Instagram / Facebook 自動投稿

schedule.csv に書かれた予定のうち、投稿時刻を過ぎていて、まだ投稿していないものを
Instagram（と Facebook ページ）に投稿する。投稿済みは posted.json に記録する。

環境変数
  META_TOKEN  : システムユーザーのアクセストークン（GitHub Secrets に保存）
  MODE        : "post"（既定）/ "check"（接続確認だけ・投稿しない）
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

GRAPH = "https://graph.facebook.com/v23.0"
JST = timezone(timedelta(hours=9))
ROOT = os.path.dirname(os.path.abspath(__file__))

CONFIG = json.load(open(os.path.join(ROOT, "config.json"), encoding="utf-8"))
PAGE_ID = CONFIG["page_id"]
RAW_BASE = CONFIG["raw_base"].rstrip("/")
# 予定時刻からこの時間以上たったものは「取りこぼし」として投稿しない（古い投稿が急に出るのを防ぐ）
GRACE_HOURS = CONFIG.get("grace_hours", 6)

SCHEDULE = os.path.join(ROOT, "schedule.csv")
POSTED = os.path.join(ROOT, "posted.json")


# ---------- Graph API ----------
def api(method, path, token, **params):
    params["access_token"] = token
    url = f"{GRAPH}/{path}"
    data = None
    if method == "GET":
        url += "?" + urllib.parse.urlencode(params)
    else:
        data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> {e.code}: {body}") from None


def get_accounts(user_token):
    page = api("GET", PAGE_ID, user_token, fields="name,access_token,instagram_business_account{id,username}")
    ig = page.get("instagram_business_account") or {}
    if not ig.get("id"):
        raise RuntimeError("Facebookページに紐づいたInstagramビジネスアカウントが見つかりません")
    return page["access_token"], ig["id"], ig.get("username", ""), page.get("name", "")


def wait_container(container_id, token, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        st = api("GET", container_id, token, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"メディア処理エラー: {st}")
        time.sleep(5)
    raise RuntimeError("メディア処理がタイムアウトしました")


def is_video(path):
    return path.lower().endswith((".mp4", ".mov"))


# ---------- Instagram ----------
def post_instagram(ig_id, token, kind, url, caption):
    params = {}
    if kind == "story":
        params["media_type"] = "STORIES"
        params["video_url" if is_video(url) else "image_url"] = url
    elif is_video(url):
        params["media_type"] = "REELS"
        params["video_url"] = url
        params["share_to_feed"] = "true"
        params["caption"] = caption
    else:
        params["image_url"] = url
        params["caption"] = caption
    c = api("POST", f"{ig_id}/media", token, **params)
    wait_container(c["id"], token)
    res = api("POST", f"{ig_id}/media_publish", token, creation_id=c["id"])
    return res["id"]


# ---------- Facebook ページ ----------
def post_facebook(page_token, kind, url, caption):
    if kind == "story":
        if is_video(url):
            return None  # 動画ストーリーは手順が別なので今回は対象外（Instagram側だけ出す）
        photo = api("POST", f"{PAGE_ID}/photos", page_token, url=url, published="false")
        res = api("POST", f"{PAGE_ID}/photo_stories", page_token, photo_id=photo["id"])
        return res.get("post_id") or res.get("id")
    if is_video(url):
        res = api("POST", f"{PAGE_ID}/videos", page_token, file_url=url, description=caption)
        return res.get("id")
    res = api("POST", f"{PAGE_ID}/photos", page_token, url=url, message=caption)
    return res.get("post_id") or res.get("id")


# ---------- 予定表 ----------
def load_schedule():
    rows = []
    with open(SCHEDULE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("datetime") or row["datetime"].startswith("#"):
                continue
            rows.append(row)
    return rows


def caption_of(row):
    name = (row.get("caption") or "").strip()
    if not name:
        return ""
    with open(os.path.join(ROOT, "captions", name), encoding="utf-8") as f:
        return f.read().strip()


def key_of(row):
    return f'{row["datetime"]}|{row["type"]}|{row["media"]}'


def main():
    mode = os.environ.get("MODE", "post")
    rows = load_schedule()
    posted = json.load(open(POSTED, encoding="utf-8")) if os.path.exists(POSTED) else {}

    now = datetime.now(JST)
    due = []
    for r in rows:
        when = datetime.strptime(r["datetime"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=JST)
        k = key_of(r)
        if k in posted:
            continue
        if when <= now:
            if now - when > timedelta(hours=GRACE_HOURS):
                print(f"スキップ（時間が過ぎすぎ）: {k}")
                continue
            due.append(r)

    upcoming = sorted(
        (r for r in rows if key_of(r) not in posted
         and datetime.strptime(r["datetime"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=JST) > now),
        key=lambda r: r["datetime"])
    print(f"今回投稿するもの: {len(due)}件 / これからの予定: {len(upcoming)}件")
    for r in upcoming[:3]:
        print(f'  次: {r["datetime"]} {r["type"]} {r["media"]}')

    if mode == "post" and not due:
        print("今は投稿するものがないので終了します")
        return

    token = os.environ.get("META_TOKEN", "").strip()
    if not token:
        sys.exit("META_TOKEN が設定されていません（GitHub の Settings → Secrets に保存してください）")
    page_token, ig_id, ig_name, page_name = get_accounts(token)
    print(f"接続OK: Facebookページ「{page_name}」 / Instagram @{ig_name}")

    if mode == "check":
        missing = [r["media"] for r in rows if not os.path.exists(os.path.join(ROOT, "media", r["media"]))]
        if missing:
            print("⚠ 画像が見つからない予定があります:", missing)
        print("接続確認モードなので投稿はしません")
        return

    errors = 0
    for r in due:
        k = key_of(r)
        kind = r["type"].strip()
        url = f'{RAW_BASE}/media/{urllib.parse.quote(r["media"].strip())}'
        cap = caption_of(r)
        targets = (r.get("targets") or "ig,fb").replace(" ", "").split(",")
        result = {"at": now.isoformat()}
        try:
            if "ig" in targets:
                result["ig"] = post_instagram(ig_id, token, kind, url, cap)
                print(f"Instagram 投稿OK: {k} -> {result['ig']}")
            if "fb" in targets:
                try:
                    result["fb"] = post_facebook(page_token, kind, url, cap)
                    print(f"Facebook 投稿OK: {k} -> {result['fb']}")
                except Exception as e:  # Facebook 側の失敗で Instagram の記録を失わないように
                    result["fb_error"] = str(e)[:300]
                    print(f"Facebook 投稿失敗: {k}: {e}")
                    errors += 1
            posted[k] = result
        except Exception as e:
            print(f"投稿失敗: {k}: {e}")
            errors += 1
        with open(POSTED, "w", encoding="utf-8") as f:
            json.dump(posted, f, ensure_ascii=False, indent=2)

    if errors:
        sys.exit(f"{errors}件の投稿でエラーがありました")


if __name__ == "__main__":
    main()
