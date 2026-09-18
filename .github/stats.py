import json
import os
import urllib.request
from xml.sax.saxutils import escape

USER = "S4vi0r17"
TOP = 4
EXCLUDE = {"Jupyter Notebook"}

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions }
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { languages(first: 20) { edges { size node { name } } } }
    }
  }
}
"""


def graphql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]["user"]


def fetch():
    sizes, cursor = {}, None
    while True:
        user = graphql({"login": USER, "cursor": cursor})
        repos = user["repositories"]
        for repo in repos["nodes"]:
            for edge in repo["languages"]["edges"]:
                name = edge["node"]["name"]
                if name not in EXCLUDE:
                    sizes[name] = sizes.get(name, 0) + edge["size"]
        if not repos["pageInfo"]["hasNextPage"]:
            counts = {
                "commits": user["contributionsCollection"]["totalCommitContributions"],
                "pulls": user["pullRequests"]["totalCount"],
                "issues": user["issues"]["totalCount"],
            }
            return sizes, counts
        cursor = repos["pageInfo"]["endCursor"]


def render(sizes, counts):
    total = sum(sizes.values())
    langs = sorted(sizes.items(), key=lambda kv: kv[1], reverse=True)[:TOP]
    width, bar_x, bar_w, row = 320, 96, 168, 22
    rows = []
    for i, (name, size) in enumerate(langs):
        y = 44 + i * row
        pct = size / total * 100
        rows.append(
            f'<text x="0" y="{y}">{escape(name)}</text>'
            f'<rect class="track" x="{bar_x}" y="{y - 5}" width="{bar_w}" height="3" rx="1.5"/>'
            f'<rect class="bar" x="{bar_x}" y="{y - 5}" width="{max(bar_w * pct / 100, 3):.1f}" height="3" rx="1.5"/>'
            f'<text class="dim" x="{width}" y="{y}" text-anchor="end">{pct:.1f}%</text>'
        )
    footer_y = 44 + len(langs) * row + 18
    char_w = 7.2
    widths = [len(f"{n} {label}") * char_w for label, n in counts.items()]
    gap = (width - sum(widths)) / (len(widths) + 1)
    x, footer = gap, ""
    for (label, n), w in zip(counts.items(), widths):
        footer += (
            f'<text xml:space="preserve" x="{x + w / 2:.1f}" y="{footer_y}" text-anchor="middle">'
            f'{n}<tspan class="dim"> {label}</tspan></text>'
        )
        x += w + gap
    height = footer_y + 8
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
  text {{ font: 12px Iosevka, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #57606a; }}
  .dim {{ fill: #8c959f; }}
  .bar {{ fill: #c77dd1; }}
  .track {{ fill: #eaeef2; }}
  @media (prefers-color-scheme: dark) {{
    text {{ fill: #c9d1d9; }}
    .dim {{ fill: #6e7681; }}
    .bar {{ fill: #fbd6ff; }}
    .track {{ fill: #21262d; }}
  }}
</style>
<text class="dim" x="0" y="16">languages</text>
{"".join(rows)}
{footer}
</svg>
"""


if __name__ == "__main__":
    with open("stats.svg", "w") as f:
        f.write(render(*fetch()))
