# -*- coding: utf-8 -*-
"""
corpus_search.py — 十分吸引逐字稿本地语料检索

用法:
    python corpus_search.py [<index.json>] <词1> [词2 ...] [-n N] [-any]

行为:
    - index.json 缺省时依次尝试:
        1) 环境变量 SHIFENXIYIN_CORPUS_DIR 指向的 corpus_index.json
        2) ~/shifenxiyin-corpus/corpus_index.json
    - 默认多词 AND（每词都必须命中发言段正文）；-any 任意一词命中即可
    - 命中时返回: 期号/文件名、章节、说话人、时间、发言段文本

注意:
    - 所有逐字稿（Vol.01-77 与 EP.01 等）均为节目版权内容，不随 skill 分发。
    - 如需检索往期原话，请自行准备获授权的语料目录，
      先运行 corpus_build.py 生成索引。
"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NOT_INSTALLED_MSG = (
    "[corpus_search] 未找到全量语料索引。\n"
    "所有逐字稿为节目版权内容，不随 skill 分发。"
    "如需检索往期逐字稿：\n"
    "  1) 准备一个语料目录（如 ~/shifenxiyin-corpus/transcripts，"
    "文件名形如 Vol.63_尼采与反脆弱.md，内容为逐字稿全文）\n"
    "  2) 运行: python corpus_build.py <语料目录>\n"
    "  3) 完成后本工具自动可用；也可用 -dir 显式指定目录。"
)


def resolve_index(arg):
    if arg and Path(arg).is_file():
        return arg
    env = os.environ.get("SHIFENXIYIN_CORPUS_DIR", "")
    cand = []
    if arg:
        cand.append(Path(arg) / "corpus_index.json")
    if env:
        cand.append(Path(env) / "corpus_index.json")
    cand.append(Path.home() / "shifenxiyin-corpus" / "corpus_index.json")
    for c in cand:
        if c.is_file():
            return str(c)
    return None


def load_index(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    args = sys.argv[1:]
    # 解析 <index.json> 是否为第一个存在的文件/路径
    idx_path = None
    i = 0
    if args and not args[0].startswith("-") and len(args) >= 2:
        cand = args[0]
        # 以 .json 结尾或含路径分隔符 => 视为索引参数
        if cand.endswith(".json") or os.sep in cand or "/" in cand:
            idx_path = cand
            i = 1
    n = 10
    any_mode = False
    rest = []
    while i < len(args):
        a = args[i]
        if a == "-n" and i + 1 < len(args):
            n = int(args[i + 1]); i += 2
        elif a == "-any":
            any_mode = True; i += 1
        elif a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            rest.append(a); i += 1
    if not rest:
        print(__doc__)
        sys.exit(1)
    resolved = resolve_index(idx_path)
    if not resolved:
        print(NOT_INSTALLED_MSG)
        sys.exit(2)
    keys = rest
    data = load_index(resolved)
    docs = data.get("docs", [])
    if any_mode:
        def text_ok(text):
            return any(k in text for k in keys)
    else:
        def text_ok(text):
            return all(k in text for k in keys)

    hits = []  # (score, doc, entry)  标题/简介命中分两类处理
    title_hits = []
    for doc in docs:
        title_blob = doc["title"]
        meta_blob = " | ".join(doc.get("meta", []))
        if text_ok(title_blob) or text_ok(meta_blob):
            title_hits.append(doc)
        for e in doc["entries"]:
            text = e.get("text", "")
            if not text:
                continue
            if text_ok(text):
                hits.append((doc, e))

    def rank(doc, e):
        return sum(e["text"].count(k) for k in keys)

    # 输出标题/简介命中（低置信提示，供辅助）
    if title_hits and not hits:
        print("== 仅命中标题/简介（无正文命中）==")
        for doc in title_hits[:10]:
            print(f"• {doc['file']}  |  {doc['title']}")
        print()

    if not hits:
        print("未命中任何发言段。尝试 -any（放宽为任意词）或换关键词。")
        return

    hits.sort(key=lambda h: -rank(h[0], h[1]))
    print(f"== 命中 {len(hits)} 段，显示前 {min(n, len(hits))} 段 ==")
    for idx, (doc, e) in enumerate(hits[:n], 1):
        head = doc["file"].replace(".md", "").replace(".txt", "")
        loc = []
        if e.get("ch"):
            loc.append(e["ch"])
        if e.get("spk"):
            loc.append(e["spk"])
        if e.get("t"):
            loc.append("@" + e["t"])
        locs = " · ".join(loc) if loc else ""
        print(f"\n[{idx}] {head}  (行 {e.get('line', '?')})")
        if locs:
            print(f"    {locs}")
        print(f"    {e['text']}")
        if idx >= n:
            break
    print(f"\n索引: {data.get('doc_count')} 篇 / {data.get('segment_count')} 段 | "
          f"来源目录: {data.get('corpus_dir')}")


if __name__ == "__main__":
    main()
