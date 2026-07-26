import feedparser, json, os, urllib.request
from datetime import datetime

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
API_KEYS = [
    "AIzaSyCF0vHDUgJFiI9J2wOJWf71U2wEEBMe96I",
    "AIzaSyDc53yUZ3TJAFBcwlK1itQhfznVemmJZdI",
    "AIzaSyA_dgk-B4-_QL_-acNAWCFuv-fSlkQV1eE",
    "AIzaSyDhLtLmX9DJbUqR3zm0rSPls8DcrvzfKO4",
]
ki = 0

def translate(t):
    global ki
    for _ in range(4):
        try:
            p = json.dumps({"contents":[{"parts":[{"text":f"Translate to Chinese, output only translation:\n{t}"}]}]}).encode()
            k = API_KEYS[ki % 4]; ki += 1
            r = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={k}", data=p, headers={"Content-Type":"application/json"})
            with urllib.request.urlopen(r, 30) as resp:
                return json.loads(resp.read())["candidates"][0]["content"]["parts"][0]["text"].strip().strip('"')
        except: pass
    return t

def load():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f: return json.load(f)
    return {}

def save(s):
    with open(SEEN_FILE, "w") as f: json.dump(s, f)

def discord(msg):
    if not WEBHOOK: return
    try:
        r = urllib.request.Request(WEBHOOK, data=json.dumps({"content":msg}).encode(), headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
        urllib.request.urlopen(r, 15)
    except: pass

seen = load()
new = []
for name, cid in CHANNELS.items():
    try:
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
    except: continue
    old = seen.get(cid, [])
    for e in feed.entries[:10]:
        vid = e.get("yt_videoid","")
        if vid and vid not in old:
            title = e.get("title","")
            link = e.get("link","")
            pub = e.get("published","")[:16]
            new.append((name, title, link, pub))
            old.append(vid)
    seen[cid] = old[-200:]
save(seen)

if not new:
    print("No new videos")
else:
    for ch, title, link, pub in new:
        cn = translate(title)
        msg = f"**{ch}**\n{cn}\n{title}\n{link}"
        discord(msg)
        print(f"Sent: {ch} - {cn}")
