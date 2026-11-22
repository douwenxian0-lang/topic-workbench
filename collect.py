# -*- coding: utf-8 -*-
"""
选题雷达 · 公众号文章收集器
用法：
  python collect.py                     # 搜狗微信抓取对标号最新文章（尽力而为）
  python collect.py --add-url <文章链接> [更多链接...]   # 手动/喂链接方式收录（最可靠）
  python collect.py --accounts 名1 名2   # 临时覆盖对标号列表
收录后自动调用 build.py 重建看板。
"""
import json, re, sys, os, hashlib, html as H, urllib.request, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "articles.json")
ACCOUNTS_F = os.path.join(BASE, "accounts.json")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}

# ---------- 内容类型自动打标签（入池时按标题+摘要判定）----------
# 五类：复盘（第一人称经历/踩坑）/ 横测（对比评测）/ 清单（盘点合集）/ 教程（方法论）/ 资讯（行业新闻）
# 日更取题只取「可迁移结构」类（复盘/横测/教程/清单），资讯类仅作行业情报。
def classify(title, digest=""):
    t = f"{title} {digest}"
    if re.search(r"翻车|踩坑|踩了|避坑|复盘|折腾|坑了|被坑|翻大车|教训|亲历|我把|我做了|公开我|开源我|分享我|分享这|这一年|这几年|卖了|卖爆|烧了|求职|辞职", t):
        return "复盘"
    if re.search(r"横测|同台|大乱斗|极限横|\d+款|\d+个.{0,6}(模型|工具|产品)|vs|VS|对打|哪款|哪家|谁更|对比|评测|实测", t):
        return "横测"
    if re.search(r"清单|盘点|合集|汇总|资源|神器|宝藏|工具箱|名单", t):
        return "清单"
    if re.search(r"教程|指南|一文|怎么|如何|步骤|手册|入门|玩法|方法|实操|提示词|技巧|干货|抄作业|搭建|讲透|大白话|避雷|攻略", t):
        return "教程"
    return "资讯"

def load_json(p, default):
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    return default

def save(d, p): json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def get(url, timeout=20):
    # 直连绕过系统代理（本机 xray 代理对部分域名 502）
    proxy = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers=UA)
    return opener.open(req, timeout=timeout).read()

# ---------- 手动/喂链接模式：直接抓 mp.weixin.qq.com 正文页 ----------
def fetch_mp(url):
    raw = get(url).decode("utf-8", "ignore")
    def rx(p):
        m = re.search(p, raw)
        return H.unescape(m.group(1)).strip() if m else ""
    title = rx(r'var msg_title = \'(.*?)\'') or rx(r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>') or rx(r'property="og:title" content="(.*?)"')
    title = re.sub(r'\s+', ' ', title).strip()
    if not title:
        # 无标题基本都是「安全验证」占位页：多数是链接缺 chksm 参数，补上再试一次
        if "chksm=" not in url and "?" in url:
            raise ValueError("抓到验证页，请补全 chksm 参数后重试")
        raise ValueError("抓到验证页/空页面，稍后重试")
    account = rx(r'var nickname = htmlDecode\("(.*?)"\)') or rx(r'id="js_name"[^>]*>(.*?)</span>') or rx(r'property="og:article:author" content="(.*?)"')
    ts = rx(r'var ct = "(\d+)"') or rx(r'create_time":\s*(\d{10})')
    date = datetime.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d") if ts else datetime.date.today().isoformat()
    cover = rx(r'var msg_cdn_url = "(.*?)"') or rx(r'property="og:image" content="(.*?)"')
    digest = re.sub(r'\s+', ' ', rx(r'var msg_desc = "(.*?)"') or rx(r'property="og:description" content="(.*?)"'))[:120]
    # 正文文本（供 AI 拆解用）：截取 js_content 并去标签
    cm = re.search(r'<div[^>]*id="js_content"[^>]*>(.*?)</div>\s*<script', raw, re.S) or re.search(r'<div[^>]*id="js_content"[^>]*>(.*)', raw, re.S)
    content = ""
    if cm:
        body = cm.group(1)
        body = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S)
        body = re.sub(r'<br[^>]*>|</(p|div|section|li|h\d)>', '\n', body)
        body = re.sub(r'<[^>]+>', '', body)
        content = re.sub(r'\n{3,}', '\n\n', H.unescape(body)).strip()[:8000]
    # id 必须全局唯一：用完整链接（去 fragment）的 md5，避免 mp 链接前缀相同导致的 id 冲突
    key = url.split("#")[0].strip().replace("http://", "https://")
    return {"id": "mp" + hashlib.md5(key.encode("utf-8")).hexdigest()[:16], "link": url, "title": H.unescape(title),
            "account": account, "date": date, "cover": cover, "digest": digest, "content": content, "tag": classify(title, digest), "status": "待看", "added": datetime.date.today().isoformat()}

# ---------- 搜狗模式：尽力而为，遇验证码自动跳过 ----------
def parse_sogou_time(t):
    t = t.strip()
    today = datetime.date.today()
    if "今天" in t: return today.isoformat()
    if "昨天" in t: return (today - datetime.timedelta(days=1)).isoformat()
    m = re.match(r"(\d+)天前", t)
    if m: return (today - datetime.timedelta(days=int(m.group(1)))).isoformat()
    m = re.match(r"(\d{1,2})-(\d{1,2})", t)
    if m: return f"{today.year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return today.isoformat()

def sogou_search(account, pages=1):
    out = []
    for pg in range(1, pages + 1):
        url = f"https://weixin.sogou.com/weixin?type=2&query={urllib.parse.quote(account)}&page={pg}"
        try:
            raw = get(url).decode("utf-8", "ignore")
        except Exception as e:
            print(f"  [搜狗] {account} 第{pg}页请求失败: {e}"); continue
        if "antispider" in raw.lower() or "验证码" in raw:
            print(f"  [搜狗] 触发验证码，跳过 {account}（可稍后重试或用 --add-url 喂链接）"); break
        # 按结果块解析：标题/链接/真实公众号名/时间，只保留公众号名匹配的
        for blk in re.findall(r'<div class="txt-box">(.*?)</div>\s*</li>|<div class="txt-box">(.*?)</div>', raw, re.S):
            b = blk[0] or blk[1]
            tm = re.search(r'<h3>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?</h3>', b, re.S)
            if not tm: continue
            link = tm.group(1)
            if link.startswith("/link"): link = "https://weixin.sogou.com" + link
            title = H.unescape(re.sub(r"<[^>]+>", "", tm.group(2))).strip()
            acc_m = re.search(r'<span class="all-time-y2"[^>]*>(.*?)</span>', b, re.S)
            real_acc = H.unescape(re.sub(r"<[^>]+>", "", acc_m.group(1))).strip() if acc_m else ""
            if not real_acc:
                continue  # 抓不到公众号名的一律丢弃，防止第三方文章混入
            if account not in real_acc and real_acc not in account:
                continue  # 别的号提到这个名字的文章，剔除
            ts_m = re.search(r"timeConvert\('(\d{10})'\)", b)
            date = datetime.datetime.fromtimestamp(int(ts_m.group(1))).date().isoformat() if ts_m else datetime.date.today().isoformat()
            dig_m = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', b, re.S)
            digest = H.unescape(re.sub(r"<[^>]+>", "", dig_m.group(1))).strip()[:120] if dig_m else ""
            # id 必须全局唯一且跨天稳定：搜狗 /link?url= 每次轮换，按 链接尾40字符 生成会同号全撞车、跨天重复
            art_id = "sg" + hashlib.md5(f"{real_acc}|{date}|{title}".encode("utf-8")).hexdigest()[:16]
            out.append({"id": art_id, "link": link, "title": title,
                        "account": real_acc or account, "date": date,
                        "cover": "", "digest": digest, "tag": classify(title, digest), "status": "待看", "added": datetime.date.today().isoformat()})
    return out

def merge(old, items):
    # 双保险去重：id（跨天稳定）+ 标准化链接（搜狗链接每次轮换，不能只靠它）
    norm = lambda u: (u or "").split("#")[0].split("&amp;token=")[0].split("&token=")[0].strip()
    seen_id = {a.get("id") for a in old}
    seen_link = {norm(a.get("link")) for a in old}
    added = 0
    for it in items:
        if it["id"] in seen_id or norm(it.get("link")) in seen_link or not it["title"]: continue
        seen_id.add(it["id"]); seen_link.add(norm(it.get("link"))); old.append(it); added += 1
    return added

def main():
    accounts = load_json(ACCOUNTS_F, {}).get("accounts", [])
    argv = sys.argv[1:]
    if "--accounts" in argv:
        i = argv.index("--accounts"); accounts = argv[i+1:]; argv = argv[:i]
    db = load_json(DATA, [])
    total = 0
    urls = [a for a in argv if a.startswith("http")]
    if urls:
        for u in urls:
            try:
                art = fetch_mp(u)
                n = merge(db, [art]); total += n
                print(f"[+] {art['account']} | {art['title']} | {art['date']}" if n else f"[=] 已存在: {u[:60]}")
            except Exception as e:
                print(f"[-] 抓取失败 {u}: {e}")
    elif accounts:
        print(f"搜狗模式抓取 {len(accounts)} 个对标号...")
        for acc in accounts:
            items = sogou_search(acc)
            n = merge(db, items); total += n
            print(f"  {acc}: 新增 {n} 篇")
    else:
        print("accounts.json 为空，且未提供 --add-url"); return
    save(db, DATA)
    print(f"共新增 {total} 篇，库内总计 {len(db)} 篇")
    os.system(f'python "{os.path.join(BASE, "build.py")}"')

if __name__ == "__main__":
    main()
