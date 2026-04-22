import requests
import re
import os

def get_top_repos(username):
    url = f"https://api.github.com/users/{username}/repos?per_page=100"
    response = requests.get(url)
    if response.status_code == 200:
        repos = response.json()
        # 1. 排除同名仓库
        # 2. 排除 fork 的仓库
        filtered_repos = [
            repo for repo in repos 
            if repo['name'].lower() != username.lower() and not repo['fork']
        ]
        # 3. 按 Star 数从高到低排序
        filtered_repos.sort(key=lambda x: x['stargazers_count'], reverse=True)
        return filtered_repos[:2]
    return []

def update_readme(username, top_repos):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    new_content = ""
    for repo in top_repos:
        name = repo['name']
        new_content += f'  <a href="https://github.com/{username}/{name}">\n'
        new_content += f'    <img src="https://github-readme-stats.vercel.app/api/pin/?username={username}&repo={name}&theme=flat&hide_border=true&bg_color=00000000&title_color=3b82f6&text_color=4b5563&icon_color=3b82f6" />\n'
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
