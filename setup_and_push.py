#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""setup_and_push.py — 双击即用：授权 → 建库 → 推送 → 校验，一次跑完。

流程：
  1) 找令牌：GH_TOKEN / gh auth token / ~/.workbuddy/gh_token
  2) 没有就拉起 gh 设备码授权（浏览器输入 XXXX-XXXX，点 Authorize）
  3) 拿到令牌后固化到 ~/.workbuddy/gh_token + 用户环境变量 GH_TOKEN（以后永不再问）
  4) API 创建公开仓库（已存在则跳过）
  5) SSH 推送（git@github.com，不走代理、不过期）
  6) 拉远程 tree 与本地 git ls-files 比对，差集必须为 0
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

OWNER = "douwenxian0-lang"
REPO = "topic-workbench"
DESC = "公众号选题雷达 + 日更流水线：每日自动收集对标号、写稿推草稿箱、生成小红书图卡、本地/云版看板。完整可复刻工作流文档与脚本。"
BRANCH = "main"
NOPROXY = {k: v for k, v in os.environ.items()
           if k.lower() not in ("http_proxy", "https_proxy", "all_proxy")}
NOPROXY["GIT_TERMINAL_PROMPT"] = "0"
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", "gh_token")


def sh(cmd, cwd=None, timeout=180, quiet=False):
    r = subprocess.run(cmd, cwd=cwd, env=NOPROXY, capture_output=True, text=True,
                       timeout=timeout, shell=isinstance(cmd, str))
    if not quiet and r.stdout.strip():
        print("   " + r.stdout.strip().replace("\n", "\n   "))
    return r


def find_token():
    t = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if t:
        return t, "env"
    r = sh(["gh", "auth", "token"], quiet=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip(), "gh"
    if os.path.exists(TOKEN_FILE):
        t = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if t:
            return t, "file"
    return "", ""


def api(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request("https://api.github.com" + path, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token,
                                          "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json",
                                          "User-Agent": "topic-workbench-setup"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"__status__": 404}
        raise SystemExit("API %s %s -> HTTP %d: %s" % (method, path, e.code, e.read().decode()[:300]))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    print("== 1/6 检查 GitHub 令牌")
    token, src = find_token()
    if token:
        print("   已有令牌（来源 %s）" % src)
    else:
        print("   没有令牌，拉起设备码授权。浏览器会打开 github.com/login/device，")
        print("   把下面窗口里的 XXXX-XXXX 填进去点 Authorize 即可。")
        r = subprocess.run(["gh", "auth", "login", "--hostname", "github.com",
                            "--git-protocol", "https", "--web", "--skip-ssh-key"],
                           env=NOPROXY)
        if r.returncode != 0:
            sys.exit("   授权未完成，脚本退出。可重跑本脚本。")
        token, src = find_token()
        if not token:
            sys.exit("   授权后仍取不到令牌，请检查 gh 安装。")

    print("== 2/6 验证令牌")
    me = api("GET", "/user", token=token)
    print("   登录账号: %s" % me.get("login"))
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(token + "\n")
    subprocess.run(["setx", "GH_TOKEN", token], capture_output=True)
    print("   已固化到 %s + 环境变量 GH_TOKEN（以后不再需要授权）" % TOKEN_FILE)

    print("== 3/6 检查/创建仓库")
    r = api("GET", "/repos/%s/%s" % (OWNER, REPO), token=token)
    if r.get("__status__") == 404:
        api("POST", "/user/repos", {"name": REPO, "private": False, "description": DESC}, token=token)
        print("   已创建公开仓库 %s/%s" % (OWNER, REPO))
    else:
        print("   仓库已存在")

    print("== 4/6 本地提交")
    if not os.path.isdir(os.path.join(here, ".git")):
        sh(["git", "init", "-q"], cwd=here)
    sh(["git", "add", "-A"], cwd=here)
    sh(["git", "-c", "user.name=" + OWNER, "-c", "user.email=douwenxian0@gmail.com",
        "commit", "-q", "-m", "初始提交：选题工作台完整工作流文档与核心脚本"], cwd=here, quiet=True)

    print("== 5/6 SSH 推送")
    url = "git@github.com:%s/%s.git" % (OWNER, REPO)
    r = sh(["git", "push", "-u", url, BRANCH], cwd=here, timeout=240)
    if r.returncode != 0:
        print("   push 失败：", r.stderr.strip()[:300])
        sys.exit(1)

    print("== 6/6 校验远程/本地文件集合")
    tree = api("GET", "/repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, REPO, BRANCH), token=token)
    remote = {i["path"] for i in tree.get("tree", []) if i["type"] == "blob"}
    local = set(x for x in sh(["git", "-c", "core.quotepath=false", "ls-files"],
                              cwd=here, quiet=True).stdout.split("\n") if x)
    diff = remote.symmetric_difference(local)
    print("   远程 %d 个 / 本地 %d 个 | 差集 %d" % (len(remote), len(local), len(diff)))
    if diff:
        print("   ⚠️ 差集:", sorted(diff)[:10])
        sys.exit(1)
    print("\n✅ 完成：https://github.com/%s/%s" % (OWNER, REPO))


if __name__ == "__main__":
    main()
