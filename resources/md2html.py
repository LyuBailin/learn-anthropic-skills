"""
md2html.py - 把 chapters/*.md 转成独立 HTML 页面
特点：
- 深色 GitHub 风格
- 顶部章节导航栏
- 左侧大纲 (TOC)
- 代码高亮 (Pygments)
- 纯静态、零外部依赖（除 Pygments CSS）
- 锚点支持：每个标题自动生成 ID
"""

import re
import sys
from pathlib import Path
import markdown
from markdown.extensions.toc import TocExtension
from markdown.extensions.codehilite import CodeHiliteExtension


# ============ 配置 ============
PROJECT_ROOT = Path(__file__).parent.parent
CHAPTERS_DIR = PROJECT_ROOT / "chapters"
SITE_DIR = PROJECT_ROOT / "site"

# GitHub Pages 部署在 /learn-anthropic-skills/ 子路径下
# 用 <base href> 让所有相对路径自动正确解析
# 本地预览（直接双击 html）时设为 "./" —— 但 GitHub Pages 必须带前缀
BASE_URL = "/learn-anthropic-skills/"

CHAPTERS = [
    ("01-concept",     "第 1 章 · 概念入门",          "15 min · 入门"),
    ("02-anatomy",     "第 2 章 · 文件解剖",          "25 min · 核心"),
    ("03-loading",     "第 3 章 · 加载机制",          "20 min · 核心"),
    ("04-writing",     "第 4 章 · 实战编写",          "40 min · 实践"),
    ("05-api",         "第 5 章 · API 集成",          "30 min · 进阶"),
    ("06-design",      "第 6 章 · 体系设计",          "30 min · 架构"),
    ("07-ecosystem",   "第 7 章 · 生态对照",          "20 min · 横向"),
    ("08-debug",       "第 8 章 · 调试与反模式",      "20 min · 实战"),
]


# ============ HTML 模板 ============
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<base href="{base_url}">
<title>{title} · learn-skills</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/[email protected]/styles/github-dark.min.css">
<style>
:root {{
    --bg: #0d1117;
    --panel: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #f0883e;
    --accent-2: #58a6ff;
    --link: #58a6ff;
    --code-bg: #161b22;
}}
* {{ box-sizing: border-box; }}
html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    line-height: 1.7;
    font-size: 16px;
}}

/* 顶部导航 */
header.nav {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(13, 17, 23, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    padding: 12px 0;
}}
.nav-container {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}}
.nav-brand {{
    font-weight: 700;
    font-size: 1.05rem;
    color: var(--accent);
    text-decoration: none;
    margin-right: 16px;
}}
.nav-brand:hover {{ color: var(--text); }}
.nav-link {{
    color: var(--muted);
    text-decoration: none;
    font-size: 0.88rem;
    padding: 4px 10px;
    border-radius: 6px;
    transition: all 0.15s;
    white-space: nowrap;
}}
.nav-link:hover {{
    color: var(--text);
    background: var(--panel);
}}
.nav-link.active {{
    color: var(--accent);
    background: rgba(240, 136, 62, 0.1);
    border: 1px solid rgba(240, 136, 62, 0.3);
}}
.nav-spacer {{ flex: 1; }}
.nav-extra {{
    color: var(--muted);
    font-size: 0.8rem;
    padding: 4px 8px;
    border: 1px solid var(--border);
    border-radius: 6px;
}}

/* 主体布局 */
.layout {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 32px 24px;
    display: grid;
    grid-template-columns: 220px 1fr;
    gap: 32px;
}}
@media (max-width: 900px) {{
    .layout {{ grid-template-columns: 1fr; }}
    aside.toc {{ display: none; }}
}}

/* TOC */
aside.toc {{
    position: sticky;
    top: 70px;
    max-height: calc(100vh - 90px);
    overflow-y: auto;
    font-size: 0.85rem;
}}
.toc-title {{
    color: var(--muted);
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}}
.toc ul {{
    list-style: none;
    padding-left: 0;
    margin: 0;
}}
.toc ul ul {{
    padding-left: 16px;
    border-left: 1px solid var(--border);
    margin-top: 4px;
}}
.toc li {{ margin: 4px 0; }}
.toc a {{
    color: var(--muted);
    text-decoration: none;
    display: block;
    padding: 3px 8px;
    border-radius: 4px;
    transition: all 0.15s;
}}
.toc a:hover {{
    color: var(--accent-2);
    background: var(--panel);
}}
.toc a.active {{
    color: var(--accent);
    background: rgba(240, 136, 62, 0.08);
}}

/* 内容 */
article {{
    min-width: 0;
    max-width: 920px;
}}
article h1 {{
    font-size: 2.2rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
    margin-top: 0;
    margin-bottom: 24px;
    color: var(--text);
    letter-spacing: -0.02em;
}}
article h2 {{
    font-size: 1.55rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
    margin-top: 40px;
    color: var(--text);
}}
article h3 {{
    font-size: 1.2rem;
    color: var(--text);
    margin-top: 28px;
}}
article h4 {{
    font-size: 1rem;
    color: var(--accent-2);
    margin-top: 20px;
}}
article p {{ margin: 12px 0; }}
article a {{
    color: var(--link);
    text-decoration: none;
    border-bottom: 1px dashed transparent;
}}
article a:hover {{
    border-bottom-color: var(--link);
}}
article a.example-link {{
    color: var(--muted);
    border-bottom: 1px dashed var(--muted);
    font-style: italic;
}}
article ul, article ol {{ padding-left: 28px; }}
article li {{ margin: 4px 0; }}
article hr {{
    border: 0;
    border-top: 1px solid var(--border);
    margin: 32px 0;
}}
article blockquote {{
    margin: 16px 0;
    padding: 8px 16px;
    border-left: 4px solid var(--accent);
    background: rgba(240, 136, 62, 0.06);
    color: var(--muted);
    border-radius: 0 6px 6px 0;
}}
article blockquote p {{ margin: 4px 0; }}
article strong {{ color: var(--text); }}
article em {{ color: var(--accent); font-style: normal; }}

/* 标题锚点 */
article h1, article h2, article h3, article h4 {{
    position: relative;
}}
article h1:hover .headerlink,
article h2:hover .headerlink,
article h3:hover .headerlink,
article h4:hover .headerlink {{
    opacity: 1;
}}
.headerlink {{
    position: absolute;
    left: -24px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--muted);
    text-decoration: none;
    opacity: 0;
    font-weight: 400;
    transition: opacity 0.15s;
}}
.headerlink:hover {{ color: var(--accent); }}

/* 表格 */
article table {{
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 0.92rem;
}}
article th, article td {{
    border: 1px solid var(--border);
    padding: 8px 14px;
    text-align: left;
}}
article th {{
    background: var(--panel);
    color: var(--accent-2);
    font-weight: 600;
}}
article tr:nth-child(even) td {{ background: rgba(255,255,255,0.02); }}

/* 代码 */
article code {{
    background: rgba(110, 118, 129, 0.2);
    color: #ff7b72;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.88em;
    font-family: "JetBrains Mono", "Cascadia Code", Consolas, monospace;
}}
article pre {{
    background: #161b22 !important;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    overflow-x: auto;
    font-size: 0.86rem;
    line-height: 1.5;
    margin: 14px 0;
}}
article pre code {{
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
}}

/* 任务列表 */
article input[type="checkbox"] {{ margin-right: 6px; }}

/* 底部 */
footer {{
    max-width: 1280px;
    margin: 60px auto 0;
    padding: 24px;
    border-top: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.85rem;
    text-align: center;
}}
footer a {{ color: var(--accent-2); text-decoration: none; }}

/* 章节元信息 */
.chapter-meta {{
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 32px;
    display: flex;
    gap: 16px;
    align-items: center;
}}
.chapter-meta .tag {{
    background: rgba(240, 136, 62, 0.12);
    color: var(--accent);
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}}

/* 返回顶部 */
.back-to-top {{
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 40px;
    height: 40px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 50%;
    color: var(--muted);
    display: none;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    transition: all 0.2s;
    z-index: 50;
}}
.back-to-top.visible {{
    display: flex;
}}
.back-to-top:hover {{
    color: var(--accent);
    border-color: var(--accent);
}}
</style>
</head>
<body>

<header class="nav">
    <div class="nav-container">
        <a href="index.html" class="nav-brand">learn-skills</a>
        {nav_links}
        <div class="nav-spacer"></div>
        <a href="index.html" class="nav-extra">总览</a>
    </div>
</header>

<div class="layout">
    <aside class="toc">
        <div class="toc-title">本页目录</div>
        {toc}
    </aside>
    <article>
        <div class="chapter-meta">
            <span class="tag">{chapter_label}</span>
            <span>{duration}</span>
        </div>
        {content}
    </article>
</div>

<a href="#" class="back-to-top" id="backToTop" title="返回顶部">↑</a>

<footer>
    <p>learn-skills · 基于 Anthropic Agent Skills 官方文档整理 · 2026-06</p>
    <p>Skill 机制持续演进，请以 <a href="https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview">官方文档</a> 为准</p>
</footer>

<script>
// 滚动出现"返回顶部"按钮
const backBtn = document.getElementById('backToTop');
window.addEventListener('scroll', () => {{
    backBtn.classList.toggle('visible', window.scrollY > 400);
}});
backBtn.addEventListener('click', e => {{
    e.preventDefault();
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
}});

// 当前滚动位置高亮 TOC
const tocLinks = document.querySelectorAll('.toc a');
const headings = Array.from(tocLinks).map(a => document.getElementById(a.getAttribute('href').slice(1)));
if (headings.length > 0) {{
    window.addEventListener('scroll', () => {{
        const offset = 100;
        let activeIdx = 0;
        for (let i = 0; i < headings.length; i++) {{
            if (headings[i] && headings[i].offsetTop - offset < window.scrollY) {{
                activeIdx = i;
            }}
        }}
        tocLinks.forEach((a, i) => {{
            a.classList.toggle('active', i === activeIdx);
        }});
    }});
}}
</script>
</body>
</html>
"""


# ============ 工具函数 ============
def slugify(text: str) -> str:
    """把标题转成 URL 友好的 slug（用于锚点）"""
    # 去掉 markdown 标记
    text = re.sub(r'[`*_~]', '', text)
    # 中文保留，英文转小写
    text = text.lower().strip()
    # 空格转连字符
    text = re.sub(r'\s+', '-', text)
    # 去掉特殊字符
    text = re.sub(r'[^\w\u4e00-\u9fff\-]+', '', text)
    return text


def add_headerlinks(html: str) -> str:
    """给每个标题加锚点链接"""
    def replacer(m):
        level = len(m.group(1))
        title = m.group(2).strip()
        slug = slugify(title)
        return f'<h{level} id="{slug}">{title} <a class="headerlink" href="#{slug}">#</a></h{level}>'
    return re.sub(
        r'<h([1-6])>(.+?)</h\1>',
        replacer,
        html
    )


def extract_first_h1(content: str) -> str:
    """提取第一个 H1 作为页面标题"""
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else "Untitled"


def build_nav_links(current_idx: int) -> str:
    """生成顶部章节导航"""
    links = []
    for i, (slug, label, _duration) in enumerate(CHAPTERS):
        active = ' class="nav-link active"' if i == current_idx else ' class="nav-link"'
        href = f"{slug}.html"
        # 简化标签
        short = label.split("·")[1].strip() if "·" in label else label
        links.append(f'<a href="{href}"{active}>{i+1:02d}. {short}</a>')
    return "\n        ".join(links)


def build_toc(html: str) -> str:
    """从 HTML 里提取 h2/h3 生成 TOC
    兼容 add_headerlinks 生成的格式：<h2 id="slug">标题 <a class="headerlink" href="#slug">#</a></h2>
    """
    # 用更稳健的正则：先匹配整个标题块
    pattern = r'<h([23])\s+id="([^"]+)"[^>]*>(.+?)</h\1>'
    matches = re.findall(pattern, html, re.DOTALL)
    if not matches:
        return "<p style='color: var(--muted); font-size: 0.8rem;'>无章节</p>"

    toc_html = ['<ul>']
    prev_level = 2

    for level_str, slug, raw_title in matches:
        level = int(level_str)
        # 清理标题文本（去掉所有 HTML 标签）
        clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
        # 去掉尾部 # 符号（来自 headerlink）
        clean_title = re.sub(r'\s*#\s*$', '', clean_title).strip()

        if level == 2:
            # 关闭之前的 ul（如果之前是 h3）
            if prev_level == 3:
                toc_html.append('</ul></li>')
            toc_html.append(f'<li><a href="#{slug}">{clean_title}</a>')
        elif level == 3:
            # 如果之前是 h2，开启新的嵌套 ul
            if prev_level == 2:
                toc_html.append('<ul>')
            toc_html.append(f'<li><a href="#{slug}">{clean_title}</a>')

        prev_level = level

    # 收尾
    if prev_level == 3:
        toc_html.append('</ul></li>')
    toc_html.append('</ul>')

    return "".join(toc_html)


# ============ 主转换流程 ============
def convert_chapter(slug: str, label: str, duration: str, idx: int) -> None:
    md_path = CHAPTERS_DIR / f"{slug}.md"
    if not md_path.exists():
        print(f"[SKIP] {slug}: source not found")
        return

    md_content = md_path.read_text(encoding="utf-8")

    # 配置 markdown 渲染器
    md = markdown.Markdown(
        extensions=[
            'fenced_code',       # ``` 代码块
            'tables',            # 表格
            'sane_lists',        # 列表
            'nl2br',             # 换行转 <br>
            CodeHiliteExtension( # 代码高亮
                css_class='codehilite',
                guess_lang=False,
                noclasses=False,
                pygments_style='github-dark'
            ),
            TocExtension(        # 提取目录
                permalink=False,
                anchorlink=False,
                toc_depth='2-3'
            ),
        ]
    )

    body_html = md.convert(md_content)
    body_html = add_headerlinks(body_html)

    # ---- 路径修正 ----
    # HTML 渲染在 site/ 目录，源 md 在 chapters/ 目录
    # 所以 chapters 内的相对引用要加 ../ 前缀

    # 章节互链（已在同一目录里）：
    #   02-anatomy.md      → 02-anatomy.html
    #   ./02-anatomy.md    → ./02-anatomy.html
    body_html = re.sub(
        r'href="(\./)?(\d{2}-[a-z-]+)\.md(#[^"]*)?"',
        lambda m: f'href="{m.group(1) or ""}{m.group(2)}.html{m.group(3) or ""}"',
        body_html
    )

    # 跨目录引用（指向 examples/、resources/）：
    # HTML 文件在 site/，源 md 用 ../examples/xxx 引用
    # 因为 HTML 头部有 <base href="/learn-anthropic-skills/">，
    # 浏览器把"examples/xxx"解析为"/learn-anthropic-skills/examples/xxx"
    # 所以这里把 "../examples/" 去掉 ../ 前缀
    body_html = re.sub(
        r'href="\.\./(examples|resources|chapters)/',
        r'href="\1/',
        body_html
    )
    # 同上，把直接写 "examples/xxx"（少了 ../）也归一化为 "examples/xxx"
    # （虽然源 md 都用 ../，但为稳健性还是处理一下）

    # 教程里的"虚构"占位引用（如 configuration.md、review-standards.md、good-pr.md）
    # 这些是教程正文里举例说明"skill 该长什么样"的占位符，实际并不存在
    # 标记成示例链接（target="_blank" + dashed style）
    body_html = re.sub(
        r'<a href="([^"]+\.md)"',
        lambda m: (
            f'<a href="{m.group(1)}" target="_blank" class="example-link" '
            f'title="教程示例引用，点击查看源 md 文件">'
            if (SITE_DIR / m.group(1).replace("../", "")).suffix == ".md"
            and not (PROJECT_ROOT / m.group(1).replace("../", "")).exists()
            else f'<a href="{m.group(1)}"'
        ),
        body_html
    )

    # 提取标题
    page_title = extract_first_h1(md_content)

    # 生成 TOC
    toc = build_toc(body_html)

    # 生成顶部导航
    nav = build_nav_links(idx)

    # 渲染最终 HTML
    final_html = HTML_TEMPLATE.format(
        title=page_title,
        base_url=BASE_URL,
        nav_links=nav,
        toc=toc,
        chapter_label=label,
        duration=duration,
        content=body_html,
    )

    out_path = SITE_DIR / f"{slug}.html"
    out_path.write_text(final_html, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"[OK] {slug}.html ({size_kb} KB)")


# ============ 入口 ============
if __name__ == "__main__":
    SITE_DIR.mkdir(exist_ok=True)
    print(f"Converting: {CHAPTERS_DIR} -> {SITE_DIR}\n")
    for idx, (slug, label, duration) in enumerate(CHAPTERS):
        convert_chapter(slug, label, duration, idx)
    print(f"\n[DONE] {len(CHAPTERS)} HTML pages generated")
    print(f"  Entry: {SITE_DIR / 'index.html'}")
