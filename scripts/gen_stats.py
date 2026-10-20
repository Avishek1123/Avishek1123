import os, json, datetime as dt, urllib.request

USER = os.environ.get("GH_USER", "Avishek1123")
TOKEN = os.environ["GH_TOKEN"]

def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}"},
    )
    return json.load(urllib.request.urlopen(req))["data"]

created = gql("query($u:String!){user(login:$u){createdAt}}", {"u": USER})["user"]["createdAt"]
start = dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
now = dt.datetime.now(dt.timezone.utc)

days = {}
while start < now:
    end = min(start + dt.timedelta(days=365), now)
    data = gql(
        """query($u:String!,$f:DateTime!,$t:DateTime!){
          user(login:$u){contributionsCollection(from:$f,to:$t){
            contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}""",
        {"u": USER, "f": start.isoformat(), "t": end.isoformat()},
    )
    for w in data["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[d["date"]] = d["contributionCount"]
    start = end

total = sum(days.values())
today = dt.date.today()
def count(d): return days.get(d.isoformat(), 0)

d = today if count(today) > 0 else today - dt.timedelta(days=1)
current = 0
while count(d) > 0:
    current += 1
    d -= dt.timedelta(days=1)

longest = run = 0
prev = None
for key in sorted(days):
    day = dt.date.fromisoformat(key)
    if days[key] > 0:
        run = run + 1 if prev and (day - prev).days == 1 else 1
        longest = max(longest, run)
        prev = day
    else:
        run = 0
        prev = None

repos = gql(
    """query($u:String!){user(login:$u){repositories(first:100,ownerAffiliations:OWNER,isFork:false){
      nodes{languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}""",
    {"u": USER},
)["user"]["repositories"]["nodes"]
langs = {}
for r in repos:
    for e in r["languages"]["edges"]:
        langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
top = sorted(langs.items(), key=lambda x: -x[1])[:6]
tsum = sum(langs.values()) or 1

STYLE = """<style>
.card{fill:#080808;stroke:#2a2a2a;stroke-width:1}
.num{font:800 46px 'Segoe UI',Arial,sans-serif;fill:#FF1F1A}
.lbl{font:13px Consolas,Menlo,monospace;fill:#bdbdbd;letter-spacing:2px}
.sub{font:12px Consolas,Menlo,monospace;fill:#6b6b6b}
.name{font:600 15px Consolas,Menlo,monospace;fill:#F5F5F5}
.pct{font:13px Consolas,Menlo,monospace;fill:#bdbdbd}
g.a{opacity:0;animation:in .8s ease forwards}
@keyframes in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
</style>"""

cards = [
    (f"{total:,}", "TOTAL CONTRIBUTIONS", "since joining GitHub"),
    (f"{current}", "CURRENT STREAK", "days in a row"),
    (f"{longest}", "LONGEST STREAK", "days in a row"),
]
out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 160" width="1000" height="160">', STYLE]
for i, (n, label, sub) in enumerate(cards):
    x = i * 340
    out.append(
        f'<g class="a" style="animation-delay:{i*0.2}s">'
        f'<rect class="card" x="{x}" y="10" width="320" height="130" rx="10"/>'
        f'<text class="num" x="{x+26}" y="68">{n}</text>'
        f'<text class="lbl" x="{x+26}" y="98">{label}</text>'
        f'<text class="sub" x="{x+26}" y="120">{sub}</text></g>'
    )
out.append("</svg>")
os.makedirs("assets", exist_ok=True)
open("assets/streak.svg", "w").write("\n".join(out))

h = 70 + len(top) * 38
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {h}" width="1000" height="{h}">', STYLE,
       f'<rect class="card" x="0" y="0" width="1000" height="{h}" rx="10"/>',
       '<text class="lbl" x="26" y="38">MOST USED LANGUAGES</text>']
for i, (name, size) in enumerate(top):
    pct = size / tsum * 100
    y = 70 + i * 38
    w = max(4, pct / 100 * 640)
    out.append(
        f'<text class="name" x="26" y="{y+14}">{name}</text>'
        f'<rect x="200" y="{y}" width="640" height="14" rx="7" fill="#161616"/>'
        f'<rect x="200" y="{y}" height="14" rx="7" fill="#E10600">'
        f'<animate attributeName="width" from="0" to="{w:.0f}" dur="1.2s" begin="{i*0.15}s" fill="freeze"/></rect>'
        f'<text class="pct" x="860" y="{y+13}">{pct:.1f}%</text>'
    )
out.append("</svg>")
open("assets/languages.svg", "w").write("\n".join(out))
