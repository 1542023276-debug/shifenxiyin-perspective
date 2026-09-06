# -*- coding: utf-8 -*-
"""
corpus_build.py — 十分吸引全量逐字稿语料索引构建器

用法:
    python corpus_build.py <corpus_dir> [out_json]

把 corpus_dir 下的 *.md / *.txt（每期一期逐字稿）解析为
“发言段”列表，输出 corpus_index.json（UTF-8）。

发言段规则: 形如「敏姐（0:02）」「石磊（0:08）」「主持人A（01:23）」
的行是新段起点，后续非空行并入该段直到下一个发言行。
无法识别发言行的文件退化为按空行切块，保证都能被检索。
"""
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 章节标题: ## 完整逐字稿 / ### xxx / ## xxx
SEC_HEAD = re.compile(r"^\s*#{1,3}\s*(.*?)\s*$")
# 发言行: 人名（时间） / 人名（时间)  / 人名(时间)  中文或英文括号
SPEAK_RE = re.compile(
    r"^\s*([\u4e00-\u9fa5A-Za-z0-9·\u30fb]{1,16})"
    r"[（(]\s*(?:\d{1,2}:)?\d{1,2}[:：]\d{2}\s*[)）]\s*$"
)
SPEAK_RE2 = re.compile(
    r"^\s*([\u4e00-\u9fa5A-Za-z0-9·\u30fb]{1,16})\s*[:：]\s*$"
)
META_HEAD = ("#", "## 节目简介", "## 章节列表", "## 完整逐字稿")


_SENT_END = re.compile(r"(?<=[。！？!?；;])")
_CLAUSE_END = re.compile(r"[，、；;：]|\s+")

def _further_cut(text, limit):
    out, cur = [], ""
    for piece in _CLAUSE_END.split(text):
        if not piece:
            continue
        cur += piece
        if len(cur) >= limit:
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out

def split_text(text, limit=240):
    """长段按句末标点切成 ~limit 字小段，保证检索粒度细。"""
    text = text.replace("\n", "")
    if len(text) <= limit:
        return [text]
    chunks, cur = [], ""
    for piece in _SENT_END.split(text):
        cur += piece
        if len(cur) >= limit:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        if len(c) > limit * 3:
            out.extend(_further_cut(c, limit))
        else:
            out.append(c)
    return [c.strip() for c in out if len(c.strip()) >= 4]


def parse_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.splitlines()
    title = ""
    meta = []
    in_meta = True
    entries = []
    cur_ch = ""
    cur = None  # {ch, spk, t, text[], line}

    def flush():
        nonlocal cur
        if cur is not None and any(l.strip() for l in cur["text"]):
            text = "\n".join(l.rstrip() for l in cur["text"]).strip()
            if len(text) >= 4:
                for piece in split_text(text):
                    entries.append({
                        "ch": cur["ch"], "spk": cur["spk"], "t": cur["t"],
                        "line": cur["line"], "text": piece,
                    })
        cur = None

    for i, line in enumerate(lines, 1):
        s = line.strip()
        if in_meta:
            if s.startswith("# "):
                title = s[2:].strip()
            if s.startswith("## "):
                # 到达正文区标志
                if "逐字稿" in s or "完整" in s:
                    in_meta = False
                    cur_ch = s[3:].strip()
                else:
                    meta.append(s[3:].strip())
                continue
            if not s:
                continue
            if not s.startswith("#"):
                meta.append(s)
            continue
        # 正文区
        m_sec = SEC_HEAD.match(s) if (s.startswith("#") and not s.startswith("## ")) else None
        if s.startswith("###"):
            flush()
            cur_ch = s[3:].strip()
            continue
        if s.startswith("## "):
            # 正文中出现次级 ## 标题（少见），继续当章节
            flush()
            cur_ch = s[3:].strip()
            continue
        m = SPEAK_RE.match(s)
        if not m:
            m = SPEAK_RE2.match(s)
        if m:
            flush()
            cur = {"ch": cur_ch, "spk": m.group(1), "t": m.group(2) if len(m.groups()) > 1 else "",
                   "text": [], "line": i}
            continue
        if cur is not None:
            if s:
                cur["text"].append(s)
            continue
        # 正文开头的游离文本（如 "（音乐）" 等）
        if s:
            if cur is None:
                cur = {"ch": cur_ch, "spk": "", "t": "", "text": [], "line": i}
            cur["text"].append(s)
    flush()

    # 兜底: 没有任何发言段时退化为空行切块
    if not entries:
        blocks, curb = [], []
        for ln in lines:
            if not ln.strip():
                if curb:
                    blocks.append("\n".join(curb).strip())
                    curb = []
                continue
            curb.append(ln.strip())
        if curb:
            blocks.append("\n".join(curb).strip())
        entries = [{"ch": "", "spk": "", "t": "", "line": 1, "text": b}
                   for b in blocks if len(b) >= 4]
        for e in entries:
            e["text"] = "\n".join(split_text(e["text"])) if e["text"] else e["text"]
        # 空行块可能很大，再统一切小
        small = []
        for e in entries:
            for piece in split_text(e["text"]):
                small.append({"ch": "", "spk": "", "t": "", "line": e["line"], "text": piece})
        entries = small

    return {"title": title, "meta": meta, "entries": entries}


def resolve_dir():
    env = os.environ.get("SHIFENXIYIN_CORPUS_DIR", "")
    if env:
        return Path(env)
    return Path.home() / "shifenxiyin-corpus"


def main():
    if len(sys.argv) < 2:
        d = resolve_dir()
        print(f"用法: python corpus_build.py <语料目录> [out_json]\n"
              f"未提供目录，默认语料目录: {d}")
        corpus_dir = d
    else:
        corpus_dir = Path(sys.argv[1])
    out_json = Path(sys.argv[2]) if len(sys.argv) > 2 else corpus_dir / "corpus_index.json"
    if not corpus_dir.is_dir():
        print(f"[corpus_build] 语料目录不存在: {corpus_dir}")
        sys.exit(2)

    docs = []
    files = sorted(corpus_dir.glob("*.md")) + sorted(corpus_dir.glob("*.txt"))
    files = [f for f in files if f.stem.lower() != "readme"]
    total_entries = 0
    for f in files:
        try:
            d = parse_file(f)
        except Exception as e:  # noqa
            print(f"PARSE FAIL {f.name}: {e}")
            continue
        n = len(d["entries"])
        total_entries += n
        docs.append({"file": f.name, "title": d["title"], "meta": d["meta"],
                     "entries": d["entries"]})
        print(f"{f.name}: {n} segments")

    payload = {"version": 1, "doc_count": len(docs), "segment_count": total_entries,
               "corpus_dir": str(corpus_dir), "docs": docs}
    out_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out_json} | docs={len(docs)} segments={total_entries}")


if __name__ == "__main__":
    main()
