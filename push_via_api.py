#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""push_via_api.py — 一键把本目录推到 GitHub（REST API 通道，不依赖 git 协议）。

用法（先完成 GitHub 重新授权拿到有效 token，三选一）：
  1) 命令行重新登录：gh auth login -h github.com  然后直接运行本脚本（自动用 gh auth token）
  2) 把 PAT 存入文件后运行：python push_via_api.py <token文件路径>
  3) 环境变量：GH_TOKEN=ghp_xxx python push_via_api.py

行为：
  - 仓库 douwenxian0-lang/topic-workbench 不存在则自动创建（public）
  - 已存在则把本地全部文件（排除 .git / 本脚本）推成一个新提交
  - 推完自动校验远程文件集合与本地一致，打印仓库地址
"""
import base64, json, os, subprocess, sys, urllib.request

OWNER, REPO, BRANCH = "douwenxian0-lang", "topic-workbench", "main"
SKIP = {".git", "push_via_api.py", ".workbuddy"}
API = "https://api.github.com"

def get_token():
    if len(sys.argv) > 1:
        return open(sys.argv[1], encoding="utf-8").read().strip()
    env = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env:
        return env.strip()
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    sys.exit("没有可用 token：gh auth login 后重跑，或传 token 文件 / 设 GH_TOKEN")

TOKEN = get_token()

def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "topic-workbench-push",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"__status__": 404}
        raise SystemExit("API %s %s -> HTTP %d: %s" % (method, path, e.code, e.read().decode()[:300]))

BASE = os.path.dirname(os.path.abspath(__file__))

# 1) 建仓库（不存在才建）
r = api("GET", "/repos/%s/%s" % (OWNER, REPO))
if r.get("__status__") == 404:
    api("POST", "/user/repos", {"name": REPO, "private": False,
        "description": "公众号选题雷达 + 日更流水线：每日自动收集对标号、写稿推草稿箱、生成小红书图卡、本地/云版看板。完整可复刻工作流文档与脚本。"})
    print("已创建仓库 %s/%s" % (OWNER, REPO))
else:
    print("仓库已存在 %s/%s" % (OWNER, REPO))

# 2) 收集本地文件
files = {}
for root, dirs, names in os.walk(BASE):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for n in names:
        p = os.path.join(root, n)
        rel = os.path.relpath(p, BASE).replace("\\", "/")
        if any(rel.startswith(s + "/") or rel == s for s in SKIP):
            continue
        files[rel] = open(p, "rb").read()
print("本地待推文件 %d 个：%s" % (len(files), ", ".join(sorted(files))))

# 3) 取远程 HEAD（空仓库则新建首个提交）
ref = api("GET", "/repos/%s/%s/git/ref/heads/%s" % (OWNER, REPO, BRANCH))
parents = []
if ref.get("__status__") == 404:
    print("远程为空仓库，将创建首个提交")
else:
    parents = [ref["object"]["sha"]]

# 4) blob → tree → commit → ref
entries = []
for rel in sorted(files):
    b = api("POST", "/repos/%s/%s/git/blobs" % (OWNER, REPO),
            {"content": base64.b64encode(files[rel]).decode(), "encoding": "base64"})
    entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": b["sha"]})
tree = api("POST", "/repos/%s/%s/git/trees" % (OWNER, REPO), {"tree": entries})
commit = api("POST", "/repos/%s/%s/git/commits" % (OWNER, REPO), {
    "message": "初始提交：选题工作台完整工作流文档与核心脚本（验收版 2026-11-22）",
    "tree": tree["sha"], "parents": parents,
    "author": {"name": "douwenxian0-lang", "email": "douwenxian0@gmail.com"},
    "committer": {"name": "douwenxian0-lang", "email": "douwenxian0@gmail.com"},
})
if parents:
    api("PATCH", "/repos/%s/%s/git/refs/heads/%s" % (OWNER, REPO, BRANCH),
        {"sha": commit["sha"], "force": True})
else:
    api("POST", "/repos/%s/%s/git/refs" % (OWNER, REPO),
        {"ref": "refs/heads/%s" % BRANCH, "sha": commit["sha"]})
print("提交完成: %s" % commit["sha"])

# 5) 校验远程集合 == 本地集合
t = api("GET", "/repos/%s/%s/git/trees/%s?recursive=1" % (OWNER, REPO, commit["sha"]))
remote = {i["path"] for i in t["tree"] if i["type"] == "blob"}
diff = remote.symmetric_difference(files)
if diff:
    raise SystemExit("⚠️ 集合不一致，差集: %s" % diff)
print("✅ 校验通过：远程与本地文件集合完全一致（%d 个文件）" % len(remote))
print("仓库地址: https://github.com/%s/%s" % (OWNER, REPO))
