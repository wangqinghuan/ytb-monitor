import feedparser, json, os, urllib.request
from datetime import datetime, timezone, timedelta

CHANNELS = {
    "Fabrizio Romano": "UCX1em-uaFMS02Rrk_Bowyng",
    "mercato": "UCrzDtXyuSBch2u_31JJj-Dw",
    "footmercatofc": "UC6hiQYvXvMJ3mJXa-NBaq_A",
    "FFF": "UCeJlXGyEl7kBgQJKADAHM3A",
    "beIN SPORTS France": "UCfj4kQ6_mYO5r4hzX5KloVw",
    "PSG": "UCt9a_qP9CqHCNwilf-iULag",
}

SEARCH_KEYWORDS = [
    "Olise transfert",
    "Mbappé",
    "Zidane",
    "équipe de France",
    "PSG Luis Enrique",
    "mercato PSG",
    "mercato Barcelona",
]

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
        body = json.dumps({"content": msg}).encode("utf-8")
        r = urllib.request.Request(WEBHOOK, data=body, headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "Mozilla/5.0"})
        urllib.request.urlopen(r, 15)
    except: pass

def search_youtube(keyword, after_time):
    global ki
    for _ in range(4):
        try:
            k = API_KEYS[ki % 4]; ki += 1
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.request.quote(keyword)}&type=video&order=date&publishedAfter={after_time}&maxResults=5&key={k}"
            r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(r, 30) as resp:
                data = json.loads(resp.read())
                return data.get("items", [])
        except Exception as e:
            print(f"Search error: {e}")
    return []

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
            pub_raw = e.get("published","")
            try:
                dt = datetime.fromisoformat(pub_raw.replace("Z","+00:00"))
                pub = (dt + timedelta(hours=8)).strftime("%m-%d %H:%M")
            except: pub = pub_raw[:16]
            new.append((name, title, link, pub))
            old.append(vid)
    seen[cid] = old[-200:]

last_search = seen.get("_last_search", "")
now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
if not last_search or (datetime.now(timezone.utc) - datetime.fromisoformat(last_search.replace("Z","+00:00"))).total_seconds() > 1800:
    for kw in SEARCH_KEYWORDS:
        items = search_youtube(kw, last_search or (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00","Z"))
        for item in items:
            vid = item["id"]["videoId"]
            if vid in seen.get("_search_seen", []):
                continue
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={vid}"
            pub_raw = item["snippet"]["publishedAt"]
            try:
                dt = datetime.fromisoformat(pub_raw.replace("Z","+00:00"))
                pub = (dt + timedelta(hours=8)).strftime("%m-%d %H:%M")
            except: pub = pub_raw[:16]
            new.append((f"[搜索] {channel}", title, link, pub))
            seen.setdefault("_search_seen", []).append(vid)
    seen["_search_seen"] = seen.get("_search_seen", [])[-500:]
    seen["_last_search"] = now_iso

save(seen)

if not new:
    print("No new videos")
else:
    for ch, title, link, pub in new:
        cn = translate(title)
        msg = f"**{ch}** {pub}\n{cn}\n{link}"
        discord(msg)
        print(f"Sent: {ch} - {cn}")
