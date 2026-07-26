import feedparser, json, os, sys, urllib.request
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IS_CI = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'

if not IS_CI:
    os.environ["http_proxy"] = "http://127.0.0.1:7897"
    os.environ["https_proxy"] = "http://127.0.0.1:7897"

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

if IS_CI:
    proxy_handler = urllib.request.ProxyHandler({})
else:
    proxy_handler = urllib.request.ProxyHandler({"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"})
opener = urllib.request.build_opener(proxy_handler)

def translate(t):
    global ki
    if not API_KEYS:
        return t
    for _ in range(4):
        try:
            p = json.dumps({"contents":[{"parts":[{"text":f"Translate to Chinese, output only translation:\n{t}"}]}]}).encode()
            k = API_KEYS[ki % len(API_KEYS)]; ki += 1
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={k}",
                data=p, headers={"Content-Type": "application/json"}
            )
            with opener.open(req, 30) as resp:
                return json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
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
        print(f"  discord: NO WEBHOOK CONFIGURED")
        return
    try:
        body = json.dumps({"content": msg}).encode("utf-8")
        req = urllib.request.Request(WEBHOOK, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
        with opener.open(req, 15) as resp:
            print(f"  discord: {resp.status}")
    except Exception as e:
        print(f"  discord error: {e}")

seen = load()
new = []

for name, cid in CHANNELS.items():
    try:
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
    except Exception as e:
        print(f"WARNING: {name} RSS failed: {e}")
        continue
    if not feed.entries:
        print(f"WARNING: {name} RSS empty")
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
            old.append(vid)
    seen[cid] = old[-200:]

save(seen)

if not new:
    print("No new videos")
else:
    for ch, title, link, pub in new:
        cn = translate(title)
        msg = f"**{ch}** {pub}\n{cn}\n{link}"
        discord(msg)
        print(f"Sent: {ch} - {cn}")
