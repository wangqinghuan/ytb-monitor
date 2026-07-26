import feedparser
import json
import os
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

CHANNELS = {
    "Fabrizio Romano": "UCX1em-uaFMS02Rrk_Bowyng",
    "mercato": "UCrzDtXyuSBch2u_31JJj-Dw",
    "footmercatofc": "UC6hiQYvXvMJ3mJXa-NBaq_A",
    "FFF": "UCeJlXGyEl7kBgQJKADAHM3A",
    "beIN SPORTS France": "UCfj4kQ6_mYO5r4hzX5KloVw",
    "PSG": "UCt9a_qP9CqHCNwilf-iULag",
}
SEEN_FILE = os.path.join(os.path.dirname(__file__), "seen.json")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
API_KEYS = [
    "AIzaSyCF0vHDUgJFiI9J2wOJWf71U2wEEBMe96I",
    "AIzaSyDc53yUZ3TJAFBcwlK1itQhfznVemmJZdI",
    "AIzaSyA_dgk-B4-_QL_-acNAWCFuv-fSlkQV1eE",
    "AIzaSyDhLtLmX9DJbUqR3zm0rSPls8DcrvzfKO4",
]
key_index = 0

def translate_to_chinese(text):
    global key_index
    if not text:
        return text
    for _ in range(len(API_KEYS)):
        try:
            prompt = f"Translate this YouTube video title to Chinese. Output only the translation:\n\n{text}"
            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
            api_key = API_KEYS[key_index % len(API_KEYS)]
            key_index += 1
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"  Translate attempt {key_index} failed: {e}")
    return text

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def send_discord(msg):
    if not DISCORD_WEBHOOK:
        print("  No Discord webhook, skipping")
        return False
    try:
        payload = json.dumps({"content": msg}).encode("utf-8")
        req = urllib.request.Request(DISCORD_WEBHOOK, data=payload, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 204)
    except Exception as e:
        print(f"  Discord error: {e}")
        return False

def check_new():
    seen = load_seen()
    new_videos = []
    for channel_name, channel_id in CHANNELS.items():
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            feed = feedparser.parse(rss_url)
        except Exception as e:
            print(f"  RSS error for {channel_name}: {e}")
            continue
        channel_seen = seen.get(channel_id, [])
        for entry in feed.entries[:10]:
            vid_id = entry.get("yt_videoid", entry.get("id", ""))
            if vid_id and vid_id not in channel_seen:
                title = entry.get("title", "Unknown")
                link = entry.get("link", "")
                new_videos.append((channel_name, title, link))
                channel_seen.append(vid_id)
        seen[channel_id] = channel_seen[-200:]
    save_seen(seen)
    return new_videos

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now}] Checking {len(CHANNELS)} channels...")

    new_vids = check_new()

    if not new_vids:
        print("  No new videos")
        return

    print(f"  Found {len(new_vids)} new videos!")

    for channel_name, title, link in new_vids:
        print(f"  [{channel_name}] {title}")
        title_cn = translate_to_chinese(title)
        print(f"  -> {title_cn}")
        msg = f"**[{channel_name}]** {title_cn}\n{title}\n{link}"
        if send_discord(msg):
            print("  Discord sent!")
        else:
            print("  Discord failed")

if __name__ == "__main__":
    main()
