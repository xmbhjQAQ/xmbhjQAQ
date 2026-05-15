import html
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


USER = "xmbhjQAQ"
GENERATED_DIR = Path("assets/generated")
GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL_API = "https://api.github.com/graphql"

LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "C++": "#f34b7d",
    "C": "#555555",
    "Java": "#b07219",
    "Shell": "#89e051",
    "PowerShell": "#012456",
}


def github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    return headers


def github_get(path_or_url):
    url = path_or_url if path_or_url.startswith("https://") else f"{GITHUB_API}{path_or_url}"
    response = requests.get(url, headers=github_headers(), timeout=30)
    response.raise_for_status()
    return response.json()


def github_graphql(query, variables):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        return None

    response = requests.post(
        GITHUB_GRAPHQL_API,
        headers=github_headers(),
        json={"query": query, "variables": variables},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        messages = "; ".join(error.get("message", "GraphQL error") for error in payload["errors"])
        raise RuntimeError(messages)
    return payload.get("data")


def escape(value):
    return html.escape(str(value or ""), quote=True)


def format_count(value):
    return "--" if value is None else f"{value:,}"


def github_datetime(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def truncate(value, limit):
    value = " ".join(str(value or "").split())
    return value if len(value) <= limit else value[: limit - 1] + "..."


def write_svg(path, body, width=495, height=195):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 700 22px Segoe UI, Arial, sans-serif; fill: #2563eb; }}
    .text {{ font: 500 14px Segoe UI, Arial, sans-serif; fill: #475569; }}
    .muted {{ font: 500 13px Segoe UI, Arial, sans-serif; fill: #64748b; }}
    .num {{ font: 700 24px Segoe UI, Arial, sans-serif; fill: #0f172a; }}
  </style>
  <rect width="{width}" height="{height}" rx="6" fill="#ffffff"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="5.5" stroke="#dbe3ef"/>
{body}
</svg>
""",
        encoding="utf-8",
    )


def write_badge(path, label, value):
    width = 255
    height = 28
    label_width = 155
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .label {{ font: 600 12px Segoe UI, Arial, sans-serif; fill: #ffffff; }}
    .value {{ font: 700 12px Segoe UI, Arial, sans-serif; fill: #ffffff; }}
  </style>
  <rect width="{width}" height="{height}" rx="4" fill="#334155"/>
  <rect x="{label_width}" width="{width - label_width}" height="{height}" rx="4" fill="#0f766e"/>
  <path d="M {label_width} 0 H {label_width + 4} V {height} H {label_width} Z" fill="#0f766e"/>
  <text x="{label_width / 2}" y="18" class="label" text-anchor="middle">{escape(label)}</text>
  <text x="{label_width + (width - label_width) / 2}" y="18" class="value" text-anchor="middle">{escape(value)}</text>
</svg>
""",
        encoding="utf-8",
    )


def get_repos(username):
    repos = github_get(f"/users/{username}/repos?per_page=100&sort=updated")
    filtered_repos = [
        repo
        for repo in repos
        if repo["name"].lower() != username.lower() and not repo["fork"]
    ]
    filtered_repos.sort(key=lambda repo: repo["stargazers_count"], reverse=True)
    return filtered_repos


def get_total_contributions(username, created_at):
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """
    start = github_datetime(created_at)
    now = datetime.now(timezone.utc)
    total = 0

    while start < now:
        year_end = datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
        end = min(year_end, now)
        data = github_graphql(
            query,
            {
                "login": username,
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": end.isoformat().replace("+00:00", "Z"),
            },
        )
        if not data or not data.get("user"):
            return None

        total += data["user"]["contributionsCollection"]["contributionCalendar"][
            "totalContributions"
        ]
        start = end

    return total


def safe_total_contributions(username, created_at):
    try:
        return get_total_contributions(username, created_at)
    except Exception as exc:
        print(f"Contribution total unavailable: {exc}")
        return None


def render_project_card(repo, path):
    name = escape(truncate(repo["name"], 34))
    description = escape(truncate(repo.get("description") or "No description provided.", 58))
    language = escape(repo.get("language") or "Code")
    color = LANGUAGE_COLORS.get(repo.get("language"), "#64748b")
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]

    body = f"""  <text x="24" y="48" class="title">{name}</text>
  <text x="24" y="82" class="text">{description}</text>
  <circle cx="31" cy="134" r="6" fill="{color}"/>
  <text x="45" y="139" class="muted">{language}</text>
  <text x="185" y="139" class="muted">Stars {stars}</text>
  <text x="285" y="139" class="muted">Forks {forks}</text>
  <text x="24" y="169" class="muted">Updated {escape(repo["updated_at"][:10])}</text>"""
    write_svg(path, body)


def render_stats_card(username, repos, path):
    profile = github_get(f"/users/{username}")
    total_stars = sum(repo["stargazers_count"] for repo in repos)
    total_contributions = safe_total_contributions(username, profile["created_at"])
    contribution_count = format_count(total_contributions)
    write_badge(
        GENERATED_DIR / "total-contributions.svg",
        "Total contributions",
        contribution_count,
    )

    body = f"""  <text x="24" y="45" class="title">GitHub Stats</text>
  <text x="24" y="88" class="num">{profile["public_repos"]}</text>
  <text x="24" y="112" class="muted">Public repos</text>
  <text x="145" y="88" class="num">{total_stars}</text>
  <text x="145" y="112" class="muted">Total stars</text>
  <text x="266" y="88" class="num">{escape(contribution_count)}</text>
  <text x="266" y="112" class="muted">Contributions</text>
  <text x="387" y="88" class="num">{profile["followers"]}</text>
  <text x="387" y="112" class="muted">Followers</text>
  <text x="24" y="160" class="text">Generated daily from GitHub API data.</text>"""
    write_svg(path, body)


def render_top_languages_card(repos, path):
    totals = {}
    for repo in repos[:25]:
        languages = github_get(repo["languages_url"])
        for language, size in languages.items():
            totals[language] = totals.get(language, 0) + size

    top_languages = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:5]
    total_size = sum(size for _, size in top_languages) or 1
    rows = ['  <text x="24" y="38" class="title">Top Languages</text>']

    for index, (language, size) in enumerate(top_languages):
        y = 68 + index * 24
        percent = size / total_size
        width = max(8, int(235 * percent))
        color = LANGUAGE_COLORS.get(language, "#64748b")
        rows.append(f'  <text x="24" y="{y}" class="muted">{escape(language)}</text>')
        rows.append(f'  <rect x="145" y="{y - 10}" width="235" height="10" rx="5" fill="#e2e8f0"/>')
        rows.append(f'  <rect x="145" y="{y - 10}" width="{width}" height="10" rx="5" fill="{color}"/>')
        rows.append(f'  <text x="395" y="{y}" class="muted">{percent:.1%}</text>')

    write_svg(path, "\n".join(rows))


def refresh_cards(username, repos):
    top_repos = repos[:2]
    render_stats_card(username, repos, GENERATED_DIR / "github-stats.svg")
    render_top_languages_card(repos, GENERATED_DIR / "top-langs.svg")
    for index, repo in enumerate(top_repos, start=1):
        render_project_card(repo, GENERATED_DIR / f"project-{index}.svg")
    return top_repos


def update_readme(username, top_repos):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    new_content = ""
    for index, repo in enumerate(top_repos, start=1):
        name = repo["name"]
        new_content += f'  <a href="https://github.com/{username}/{name}">\n'
        new_content += f'    <img src="./assets/generated/project-{index}.svg" alt="{escape(name)}" />\n'
        new_content += "  </a>\n"

    pattern = r"<!-- PROJECTS_START -->.*?<!-- PROJECTS_END -->"
    replacement = f"<!-- PROJECTS_START -->\n{new_content}  <!-- PROJECTS_END -->"
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_content)


if __name__ == "__main__":
    all_repos = get_repos(USER)
    if all_repos:
        featured_repos = refresh_cards(USER, all_repos)
        update_readme(USER, featured_repos)
        print("README and generated SVG cards updated.")
    else:
        print("No repos found.")
