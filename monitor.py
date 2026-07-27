import feedparser, json, os, sys, requests
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IS_CI = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
PROXIES = None if IS_CI else {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

print(f"START: IS_CI={IS_CI}, WEBHOOK={'SET' if os.environ.get('DISCORD_WEBHOOK') else 'EMPTY'}, KEYS={sum(1 for k in [os.environ.get(f'GEMINI_KEY_{i}','') for i in range(1,5)] if k)}")

CHANNELS = {
    "Fabrizio Romano": "UCX1em-uaFMS02Rrk_Bowyng",
    "mercato": "UCrzDtXyuSBch2u_31JJj-Dw",
    "footmercatofc": "UC6hiQYvXvMJ3mJXa-NBaq_A",
    "FFF": "UCeJlXGyEl7kBgQJKADAHM3A",
    "beIN SPORTS France": "UCfj4kQ6_mYO5r4hzX5KloVw",
    "PSG": "UCt9a_qP9CqHCNwilf-iULag",
}

SEEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen.json")
WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")
API_KEYS = [k for k in [
    os.environ.get("GEMINI_KEY_1", ""),
    os.environ.get("GEMINI_KEY_2", ""),
    os.environ.get("GEMINI_KEY_3", ""),
    os.environ.get("GEMINI_KEY_4", ""),
] if k]
ki = 0

def translate(t):
    global ki
    if not API_KEYS:
        return t
    for _ in range(4):
        try:
            k = API_KEYS[ki % len(API_KEYS)]; ki += 1
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={k}",
                json={"contents": [{"parts": [{"text": f"Translate to Chinese, output only translation:\n{t}"}]}]},
                proxies=PROXIES, timeout=30
            )
            if r.status_code == 200:
                return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        except Exception as e:
            print(f"  translate error: {e}")
    return t

def load():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f: return json.load(f)
    return {}

def save(s):
    with open(SEEN_FILE, "w") as f: json.dump(s, f, ensure_ascii=False)

def discord(msg):
    if not WEBHOOK:
        print(f"  discord: NO WEBHOOK")
        return
    try:
        r = requests.post(WEBHOOK, json={"content": msg}, proxies=PROXIES, timeout=15)
        print(f"  discord: {r.status_code}")
    except Exception as e:
        print(f"  discord error: {e}")

seen = load()
print(f"SEEN: loaded {len(seen)} channels")
new = []

for name, cid in CHANNELS.items():
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
        resp = requests.get(url, proxies=PROXIES, timeout=30)
        feed = feedparser.parse(resp.text)
        print(f"  {name}: {len(feed.entries)} entries, RSS={resp.status_code}")
    except Exception as e:
        print(f"  {name}: FAILED - {e}")
        continue
    if not feed.entries:
        print(f"  {name}: RSS empty!")
    old = seen.get(cid, [])
    for e in feed.entries[:15]:
        vid = e.get("yt_videoid", "")
        if vid and vid not in old:
            title = e.get("title", "")
            link = e.get("link", "")
            pub_raw = e.get("published", "")
            try:
                dt = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
                pub = (dt + timedelta(hours=8)).strftime("%m-%d %H:%M")
            except: pub = pub_raw[:16]
            new.append((name, title, link, pub))
            print(f"    NEW: {vid} - {title[:50]}")
            old.append(vid)
    seen[cid] = old[-200:]

save(seen)

print(f"RESULT: {len(new)} new videos")

if not new:
    print("No new videos")
else:
    for ch, title, link, pub in new:
        cn = translate(title)
        msg = f"**{ch}** {pub}\n{cn}\n{link}"
        discord(msg)
        print(f"Sent: {ch} - {cn}")
