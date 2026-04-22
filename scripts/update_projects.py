import requests
import re
import os

def get_top_repos(username):
    url = f"https://api.github.com/users/{username}/repos?sort=stars&direction=desc"
    response = requests.get(url)
    if response.status_code == 200:
        repos = response.json()
        # 排除同名主页仓库，展示另外两个最火的项目
        filtered_repos = [repo for repo in repos if repo['name'].lower() != username.lower()]
        return filtered_repos[:2]
    return []

def update_readme(username, top_repos):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    new_content = ""
    for repo in top_repos:
        name = repo['name']
        new_content += f'  <a href="https://github.com/{username}/{name}">\n'
        new_content += f'    <img src="https://github-readme-stats.vercel.app/api/pin/?username={username}&repo={name}&theme=tokyonight" />\n'
        new_content += f'  </a>\n'

    # 使用正则替换锚点之间的内容
    pattern = r"<!-- PROJECTS_START -->.*?<!-- PROJECTS_END -->"
    replacement = f"<!-- PROJECTS_START -->\n{new_content}  <!-- PROJECTS_END -->"
    updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(updated_content)

if __name__ == "__main__":
    USER = "xmbhjQAQ"
    top = get_top_repos(USER)
    if top:
        update_readme(USER, top)
        print("README updated with top repos.")
    else:
        print("No repos found.")
