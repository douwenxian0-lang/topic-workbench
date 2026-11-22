# -*- coding: utf-8 -*-
"""选题工作台 · 看板生成器：扫描 data/articles.json + articles/ + social-cards/ → 工作台.html"""
import json, os, re, datetime, glob

BASE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(BASE, *p)

def load(p, default):
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: pass
    return default

# ---------- 我的文章：articles/*.md ----------
def scan_articles():
    out = []
    for f in sorted(glob.glob(D("articles", "*.md")), key=os.path.getmtime, reverse=True):
        txt = open(f, encoding="utf-8", errors="ignore").read()
        name = os.path.splitext(os.path.basename(f))[0]
        meta = {}
        m = re.match(r"^---\s*\n(.*?)\n---", txt, re.S)
        if m:
            for line in m.group(1).split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1); meta[k.strip().lower()] = v.strip().strip('"\'')
        body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", txt, flags=re.S)
        title = meta.get("title") or (re.search(r"^#\s+(.+)$", body, re.M).group(1) if re.search(r"^#\s+(.+)$", body, re.M) else name)
        img = re.search(r'!\[.*?\]\((.*?)\)', body)
        cover = img.group(1) if img else ""
        words = len(re.sub(r"\s", "", re.sub(r"!\[.*?\]\(.*?\)|\[.*?\]\(.*?\)", "", body)))
        if meta.get("status"): status = meta["status"]
        elif words < 300: status = "调研中"
        elif meta.get("date") or meta.get("published"): status = "已完稿"
        else: status = "写作中"
        date = meta.get("date") or datetime.date.fromtimestamp(os.path.getmtime(f)).isoformat()
        out.append({"title": title, "date": date, "status": status, "cover": cover, "words": words})
    return out

# ---------- 小红书图文：social-cards/<套名>/ ----------
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
def scan_social():
    out = []
    for d in sorted(glob.glob(D("social-cards", "*")), key=os.path.getmtime, reverse=True):
        if not os.path.isdir(d): continue
        # 递归扫描：info-card-systems 渲染器把 PNG 输出到 output/ 子目录，也要收录
        imgs = sorted(f for f in glob.glob(os.path.join(d, "**", "*"), recursive=True)
                      if os.path.isfile(f) and f.lower().endswith(IMG_EXT))
        if not imgs: continue
        status = "待发布"
        st = os.path.join(d, "status.txt")
        if os.path.exists(st): status = open(st, encoding="utf-8").read().strip() or status
        out.append({"name": os.path.basename(d), "pages": len(imgs),
                    "cover": os.path.relpath(imgs[0], BASE).replace("\\", "/"), "status": status})
    return out

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")

def main():
    arts = load(D("data", "articles.json"), [])
    mine = scan_articles()
    social = scan_social()
    payload = json.dumps({"arts": arts, "mine": mine, "social": social}, ensure_ascii=False, separators=(",", ":"))

    page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>选题工作台 · 公众号选题与复盘</title>
<style>
:root{--bg:#F7F6F3;--card:#fff;--ink:#333;--sub:#999;--line:#ECEAE5;--blue:#5B8DB8;--green:#7BA05B;--orange:#D9945B;--gray:#B0ABA3;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;background:var(--bg);color:var(--ink);padding:20px;}
.wrap{max-width:1360px;margin:0 auto;}
h1{font-size:22px;text-align:center;letter-spacing:2px;padding:14px 0 4px;}
.subt{text-align:center;color:var(--sub);font-size:12px;margin-bottom:18px;}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px;}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 18px;}
.stat b{font-size:24px;}
.stat small{color:var(--sub);font-size:12px;margin-left:6px;}
.stat .lb{font-size:13px;color:var(--sub);margin-top:4px;}
section{margin-bottom:26px;}
.shead{display:flex;align-items:center;gap:10px;margin-bottom:12px;}
.shead h2{font-size:16px;border-left:4px solid var(--blue);padding-left:9px;}
.toggle{font-size:12px;color:var(--sub);cursor:pointer;padding:3px 10px;border:1px solid var(--line);border-radius:12px;background:#fff;}
.toggle.on{background:var(--blue);color:#fff;border-color:var(--blue);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;}
.acard{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;transition:box-shadow .15s;cursor:pointer;}
.acard:hover{box-shadow:0 4px 14px rgba(0,0,0,.09);}
.athumb{height:130px;background:linear-gradient(135deg,#E8E4DC,#D8D2C6);background-size:cover;background-position:center;position:relative;}
.athumb .acc{position:absolute;left:0;bottom:0;right:0;background:linear-gradient(transparent,rgba(0,0,0,.55));color:#fff;font-size:11px;padding:14px 8px 5px;}
.abody{padding:9px 11px 11px;}
.abody .t{font-size:13px;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.abody .m{font-size:11px;color:var(--sub);margin-top:6px;display:flex;justify-content:space-between;}
.kanban{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;}
.kcol{background:#EFEEE9;border-radius:12px;padding:10px;min-height:180px;}
.kcol h3{font-size:13px;color:var(--sub);margin:2px 4px 10px;display:flex;justify-content:space-between;}
.kcol h3 b{color:var(--ink);}
.kcol.over{outline:2px dashed var(--blue);outline-offset:-4px;}
.kcard{background:#fff;border-radius:8px;padding:9px 11px;margin-bottom:8px;cursor:grab;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.kcard:active{cursor:grabbing;}
.kcard .t{font-size:12.5px;font-weight:600;line-height:1.4;}
.kcard .m{font-size:11px;color:var(--sub);margin-top:4px;}
.empty{color:var(--sub);font-size:12.5px;text-align:center;padding:26px 0;}
.scover{border-radius:10px 10px 0 0;background-size:cover;background-position:center;height:200px;position:relative;}
.sbadge{position:absolute;top:8px;right:8px;font-size:10.5px;color:#fff;padding:2px 8px;border-radius:9px;}
.st0{background:var(--orange);}.st1{background:var(--blue);}.st2{background:var(--green);}
.smeta{background:#fff;border-radius:0 0 10px 10px;padding:8px 11px;font-size:12.5px;}
.smeta small{color:var(--sub);}
.foot{text-align:center;color:var(--sub);font-size:11.5px;padding:16px 0;line-height:1.8;}
@media(max-width:900px){.stats{grid-template-columns:repeat(2,1fr);}.kanban{grid-template-columns:1fr;}}
</style>
</head>
<body>
<div class="wrap">
<h1>📝 选题工作台</h1>
<div class="subt">公众号选题 · 阅读进度 · 多平台产出 一板看清</div>
<div class="stats" id="stats"></div>

<section>
  <div class="shead"><h2>👀 同行在写什么</h2>
    <span class="toggle on" data-t="7">最近7天</span><span class="toggle" data-t="0">今天</span>
    <span style="font-size:12px;color:var(--sub)">收录 <b id="nAll">0</b> 篇 · 点击卡片打开原文</span>
  </div>
  <div class="grid" id="recent"></div>
</section>

<section>
  <div class="shead"><h2>📌 阅读进度看板</h2>
    <span style="font-size:12px;color:var(--sub)">拖动卡片换状态，进度自动保存在本机浏览器</span>
  </div>
  <div class="kanban" id="kb"></div>
</section>

<section>
  <div class="shead"><h2>🔴 小红书图文</h2><span style="font-size:12px;color:var(--sub)">social-cards/ 目录，每套一个文件夹 · 用「info-card-systems」技能做图卡（说「做图卡」即可触发），渲染完自动上板</span></div>
  <div class="grid" id="social"></div>
</section>

<section>
  <div class="shead"><h2>✍️ 我的文章</h2>
    <span class="toggle on" data-m="card">卡片</span><span class="toggle" data-m="table">按年分组</span>
    <span style="font-size:12px;color:var(--sub)">articles/ 目录，按字数/frontmatter 自动判断进度</span>
  </div>
  <div id="mineWrap"></div>
</section>

<div class="foot">选题雷达工作台 · 每天定时自动收集对标号更新<br>手动喂文章：<b>python collect.py --add-url 文章链接</b> · 对标号在 accounts.json 里改 · 图卡组用 info-card-systems 技能（触发词「做图卡 / 小红书图文」）</div>
</div>
<script>
const DB = __DATA__;
const COLS = ["待看","可借鉴","已看"];
const COLC = {待看:"#D9945B",可借鉴:"#7BA05B",已看:"#B0ABA3"};
const STC = {"制作中":"st0","待发布":"st1","已发布":"st2"};
let range = 7; // 7天 / 今天
const LS = localStorage.getItem("wxkb_status") ? JSON.parse(localStorage.getItem("wxkb_status")) : {};
const stOf = a => LS[a.id] || a.status || "待看";
const today = new Date().toISOString().slice(0,10);
const d7 = new Date(Date.now()-6*864e5).toISOString().slice(0,10);
const inRange = a => range===0 ? a.date===today : a.date>=d7;

function stats(){
  const recent = DB.arts.filter(inRange);
  const wait = DB.arts.filter(a=>stOf(a)==="待看").length;
  const socialUn = DB.social.filter(s=>s.status!=="已发布").length;
  const done = DB.mine.filter(m=>m.status==="已完稿").length;
  const wip = DB.mine.filter(m=>m.status!=="已完稿").length;
  document.getElementById("stats").innerHTML = `
   <div class="stat"><b>${recent.length}</b><small>近7天 ${DB.arts.filter(a=>a.date>=d7).length}</small><div class="lb">今日同行更新</div></div>
   <div class="stat"><b>${wait}</b><small>篇</small><div class="lb">待看文章</div></div>
   <div class="stat"><b>${DB.social.length}</b><small>未发 ${socialUn}</small><div class="lb">小红书图文（套）</div></div>
   <div class="stat"><b>${done}</b><small>写作中/调研中 ${wip}</small><div class="lb">已完稿文章</div></div>`;
  document.getElementById("nAll").textContent = DB.arts.length;
}
function recentHTML(){
  const list = DB.arts.filter(inRange).sort((a,b)=>b.date.localeCompare(a.date));
  document.getElementById("recent").innerHTML = list.length ? list.map(a=>`
    <div class="acard" onclick="window.open('${a.link||''}','_blank')">
      <div class="athumb" style="${a.cover?`background-image:url('${a.cover}')`:''}">
        <div class="acc">📺 ${a.account||'未知'}</div></div>
      <div class="abody"><div class="t">${a.title}</div>
      <div class="m"><span>${a.date}</span>${a.digest?`<span>${a.digest.slice(0,14)}</span>`:''}</div></div>
    </div>`).join("") : `<div class="empty">暂无收录文章 · 运行 collect.py 或等待每日自动收集</div>`;
}
function kanbanHTML(){
  const kb = document.getElementById("kb");
  kb.innerHTML = COLS.map(c=>{
    const list = DB.arts.filter(a=>stOf(a)===c).sort((a,b)=>b.date.localeCompare(a.date));
    return `<div class="kcol" data-col="${c}">
      <h3>${c} <b>${list.length}</b></h3>
      ${list.map(a=>`<div class="kcard" draggable="true" data-id="${a.id}">
        <div class="t">${a.title}</div><div class="m">${a.account||''} · ${a.date}</div></div>`).join('')||'<div class="empty">拖卡片到这里</div>'}
    </div>`;}).join("");
  bindDnD();
}
function bindDnD(){
  document.querySelectorAll(".kcard").forEach(c=>{
    c.addEventListener("dragstart",e=>{e.dataTransfer.setData("id",c.dataset.id);c.style.opacity=.4;});
    c.addEventListener("dragend",()=>c.style.opacity=1);
  });
  document.querySelectorAll(".kcol").forEach(col=>{
    col.addEventListener("dragover",e=>{e.preventDefault();col.classList.add("over");});
    col.addEventListener("dragleave",()=>col.classList.remove("over"));
    col.addEventListener("drop",e=>{
      e.preventDefault();col.classList.remove("over");
      const id=e.dataTransfer.getData("id"); if(!id)return;
      LS[id]=col.dataset.col; localStorage.setItem("wxkb_status",JSON.stringify(LS));
      kanbanHTML(); stats();
    });
  });
}
function socialHTML(){
  document.getElementById("social").innerHTML = DB.social.length ? DB.social.map(s=>`
    <div class="acard"><div class="scover" style="background-image:url('${s.cover}')">
      <span class="sbadge ${STC[s.status]||'st1'}">${s.status}</span></div>
      <div class="smeta">${s.name}<br><small>${s.pages} 页 · 竖版 3:4</small></div></div>`).join("")
    : `<div class="empty">social-cards/ 目录还没有图文套装</div>`;
}
function mineHTML(mode){
  const w = document.getElementById("mineWrap");
  if(mode==="table"){
    const years = [...new Set(DB.mine.map(m=>m.date.slice(0,4)))].sort().reverse();
    w.innerHTML = years.map(y=>`<div style="margin-bottom:14px"><div style="font-size:13px;color:var(--sub);margin-bottom:6px">📅 ${y}（${DB.mine.filter(m=>m.date.startsWith(y)).length} 篇）</div>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden;font-size:12.5px">
      ${DB.mine.filter(m=>m.date.startsWith(y)).sort((a,b)=>b.date.localeCompare(a.date)).map(m=>`
        <tr style="border-bottom:1px solid var(--line)"><td style="padding:8px 12px">${m.title}</td>
        <td style="padding:8px 12px;color:var(--sub);width:110px">${m.date}</td>
        <td style="padding:8px 12px;width:90px;color:${m.status==='已完稿'?'var(--green)':m.status==='写作中'?'var(--orange)':'var(--gray)'}">${m.status}</td>
        <td style="padding:8px 12px;color:var(--sub);width:80px">${m.words} 字</td></tr>`).join("")}</table></div>`).join("")
      || `<div class="empty">articles/ 目录还没有文章（支持 .md，frontmatter 可写 title/status/date）</div>`;
  } else {
    w.innerHTML = DB.mine.length ? `<div class="kanban">`+["调研中","写作中","已完稿"].map(c=>{
      const list=DB.mine.filter(m=>m.status===c);
      return `<div class="kcol"><h3>${c} <b>${list.length}</b></h3>${list.map(m=>`
        <div class="kcard"><div class="t">${m.title}</div><div class="m">${m.date} · ${m.words} 字</div></div>`).join('')||'<div class="empty">暂无</div>'}</div>`;
    }).join("")+`</div>` : `<div class="empty">articles/ 目录还没有文章（支持 .md，frontmatter 可写 title/status/date）</div>`;
  }
}
document.querySelectorAll(".toggle[data-t]").forEach(t=>t.onclick=()=>{
  range=+t.dataset.t;
  document.querySelectorAll(".toggle[data-t]").forEach(x=>x.classList.toggle("on",x===t));
  recentHTML(); stats();
});
document.querySelectorAll(".toggle[data-m]").forEach(t=>t.onclick=()=>{
  document.querySelectorAll(".toggle[data-m]").forEach(x=>x.classList.toggle("on",x===t));
  mineHTML(t.dataset.m);
});
stats(); recentHTML(); kanbanHTML(); socialHTML(); mineHTML("card");
</script>
</body>
</html>"""

    page = page.replace("__DATA__", payload)
    out = D("工作台.html")
    open(out, "w", encoding="utf-8").write(page)
    print(f"[看板] 已生成: {out}")
    print(f"       同行文章 {len(arts)} 篇 | 我的文章 {len(mine)} 篇 | 小红书 {len(social)} 套")

if __name__ == "__main__":
    main()
