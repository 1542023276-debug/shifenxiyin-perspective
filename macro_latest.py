# -*- coding: utf-8 -*-
"""
macro_latest.py — 吸引子宏观数据服务 · 宏观指标最新状态查询

把「吸引子宏观数据服务」的结构化宏观指标接进《十分吸引》skill，
供钱货象限 / 序参量路标 / 资产负债表等宏观分析做数据底座。

用法:
    python macro_latest.py --list                 # 列出全部可查指标（中国 27 + 全球 24）
    python macro_latest.py --health               # 健康检查
    python macro_latest.py <指标1> [指标2 ...]     # 查询指标最新数据
    python macro_latest.py --key <apikey> ...     # 显式指定 API Key
    python macro_latest.py --base <url> ...       # 显式指定 Base URL

参数说明:
    - 每个参数可以是 secId（如 att_00000042），也可以是指标中文名
      （自动子串匹配，如 "中国-物价"、"物价"、"美元流动性"）
    - 中文名匹配到多个指标时会列出候选、不发起请求（避免误拉一堆）
    - 未知 secId 由服务端静默忽略；全部未知时 data 为空数组

API Key 读取顺序:
    1) 环境变量 ATTRACTOR_API_KEY
    2) 本脚本同目录下 macro_apikey.txt 的首个非注释行（本地配置）

读数口径:
    - value 已归一化至 [-1, 1]（0≈中性，越接近 ±1 越极端），保留 4 位
    - state        = 当期状态，三档: 上升/中性/下降（由最新 value 符号决定，value≈0 时报"中性"）
    - stateChange  = 相对上一期的状态跳变: 维持/转中性/转入上升/转入下降（不足两期时为 null）
    - tradeDate    = 最新交易日
    - 限流（按 API Key 计）: 每秒 10 次 / 每分钟 100 次 / 每天 1000 次

注意:
    - 指标是宏观状态指数、不是行情价格，请作"路标/背景板"用，配合联网研究一起判断
    - API Key 是服务授权凭证，从环境变量或 macro_apikey.txt 读取（见上）；macro_apikey.txt 不随 skill 分发
    - 服务方官方接口文档随包提供（macro_api.md）: Base URL / Key / 接口 / 指标清单 / 限流说明均以它为准
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_BASE = "https://jackal.attractorcap.com/crusty"

# 指标清单（由服务配置 macro.chinaMacro / macro.globalMacro 驱动）
CHINA = [
    ("att_00000366", "中国-产能利用趋势"),
    ("att_00003490", "中国-产能利用水平"),
    ("att_00000981", "中国-房地产"),
    ("att_00000363", "中国-就业"),
    ("att_00000055", "中国-库存动力指数"),
    ("att_00003388", "中国-库存周期"),
    ("att_00000980", "中国-企业利润"),
    ("att_00000979", "中国-市场风险偏好"),
    ("att_00000042", "中国-物价"),
    ("att_00003483", "中国-服务业景气度"),
    ("att_00000045", "中国-信用环境"),
    ("att_00000977", "中国-信用环境预警"),
    ("att_00003318", "中国-信用数量"),
    ("att_00003478", "中国-货币需求"),
    ("att_00000049", "中国-资金利率"),
    ("att_00000978", "中国-资金利率预警"),
    ("att_00000039", "中国-总需求"),
    ("att_00003378", "中国-总需求预警"),
    ("att_00001049", "中国-项目投资"),
    ("att_00003413", "中国-外部金融条件"),
    ("att_00000052", "新兴市场外部金融条件"),
    ("att_00001068", "中国-流动性"),
    ("att_00000923", "中国-航运运价（干散货）"),
    ("att_00000927", "中国-航运运价（集装箱）"),
    ("att_00000369", "中国-财政政策力度"),
    ("att_00001797", "中国-货币政策倾向"),
    ("att_00003510", "中国-内需"),
]
GLOBAL = [
    ("att_00000372", "美国-财政政策力度"),
    ("att_00000985", "美国-货币政策倾向"),
    ("att_00000984", "美国-市场风险偏好"),
    ("att_00000064", "美国-物价"),
    ("att_00000061", "美国-消费就业周期"),
    ("att_00000067", "美国-信用环境"),
    ("att_00000983", "美国-信用环境预警"),
    ("att_00000058", "美国-制造业周期"),
    ("att_00003382", "美国-制造业周期预警"),
    ("att_00000070", "美国-资金利率"),
    ("att_00003480", "美国-资金利率预警"),
    ("att_00003404", "美国-库存动力指数"),
    ("att_00001069", "全球-美元流动性"),
    ("att_00003416", "全球-风险偏好指数"),
    ("att_00003385", "欧洲-制造业周期预警"),
    ("att_00003407", "欧洲-物价周期"),
    ("att_00003410", "欧洲-消费就业周期"),
    ("att_00003459", "欧洲-资金利率"),
    ("att_00003465", "欧洲-流动性"),
    ("att_00003454", "欧洲-信用价格"),
    ("att_00003451", "欧洲-信用价格预警"),
    ("att_00003457", "欧洲-财政政策"),
    ("att_00003462", "欧洲-货币政策"),
    ("att_00003468", "欧洲-市场风险偏好"),
]
ALL_ITEMS = CHINA + GLOBAL
NAME_TO_ID = {name: sec_id for sec_id, name in ALL_ITEMS}
ID_TO_NAME = {sec_id: name for sec_id, name in ALL_ITEMS}


def load_apikey():
    env = os.environ.get("ATTRACTOR_API_KEY", "").strip()
    if env:
        return env
    key_file = Path(__file__).resolve().parent / "macro_apikey.txt"
    if key_file.is_file():
        for line in key_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return None


def resolve_args(tokens):
    """把 secId / 中文名参数解析为 secId 列表；无法唯一匹配时返回 (None, 候选)。"""
    sec_ids = []
    for tok in tokens:
        tok = tok.strip()
        if tok in NAME_TO_ID:
            sec_ids.append(NAME_TO_ID[tok])
            continue
        if tok.startswith("att_"):
            sec_ids.append(tok)
            continue
        cand = [sid for sid, name in ALL_ITEMS if tok in name]
        if len(cand) == 1:
            sec_ids.append(cand[0])
        elif len(cand) > 1:
            print(f"[macro_latest] 「{tok}」匹配到多个指标，请写得更具体：")
            for sid in cand:
                print(f"    {sid}  {ID_TO_NAME[sid]}")
            return None, None
        else:
            print(f"[macro_latest] 未找到指标: {tok}（可用 --list 查看全量清单）")
            return None, None
    return sec_ids, None


def call(base, key, method, path, body=None):
    req = urllib.request.Request(base + path, method=method)
    req.add_header("apikey", key)
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"message": raw}


def do_health(base, key):
    status, payload = call(base, key, "GET", "/macro/health")
    if status != 200:
        print(f"[macro_latest] 健康检查失败 HTTP {status}: {payload}")
        return 4
    data = payload.get("data", {})
    print(f"service: {data.get('service')}")
    print(f"status:  {data.get('status')}")
    print(f"initialized: {data.get('initialized')}")
    print(f"timestamp: {data.get('timestamp')}")
    print(f"message: {payload.get('message')}")
    return 0


def do_query(base, key, sec_ids):
    status, payload = call(base, key, "POST", "/macro/latest", {"sec_ids": sec_ids})
    if status == 401:
        print("[macro_latest] 认证失败（401）：请检查 ATTRACTOR_API_KEY / macro_apikey.txt")
        return 4
    if status == 429:
        print("[macro_latest] 请求超限（429）：请按 Retry-After 稍后重试（每秒10/每分钟100/每天1000）")
        return 4
    if status != 200:
        err = payload.get("error") or payload
        print(f"[macro_latest] 查询失败 HTTP {status}: {err}")
        return 4
    data = payload.get("data") or []
    if not data:
        print("[macro_latest] data 为空：secId 可能全部未知或服务暂无该指标数据。")
        return 0
    print("== 宏观指标最新状态 ==")
    for it in data:
        sid = it.get("secId")
        name = it.get("secName") or ID_TO_NAME.get(sid, sid)
        val = it.get("value")
        print(f"{name}  ({sid})")
        print(f"   tradeDate: {it.get('tradeDate')}   value: {val}"
              f"   state: {it.get('state')}   stateChange: {it.get('stateChange')}")
    return 0


def main():
    args = sys.argv[1:]
    if not args or args in (["-h"], ["--help"]):
        print(__doc__)
        return 0 if not args else 0
    key = None
    base = DEFAULT_BASE
    tokens = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--key" and i + 1 < len(args):
            key = args[i + 1]; i += 2
        elif a == "--base" and i + 1 < len(args):
            base = args[i + 1]; i += 2
        elif a in ("--list", "-l"):
            print("== 中国宏观指标（27）==")
            for sid, name in CHINA:
                print(f"  {sid}  {name}")
            print("== 全球宏观指标（24）==")
            for sid, name in GLOBAL:
                print(f"  {sid}  {name}")
            return 0
        elif a == "--health":
            key = key or load_apikey()
            if not key:
                print("[macro_latest] 未配置 API Key：请设置环境变量 ATTRACTOR_API_KEY，"
                      "或在脚本同目录放置 macro_apikey.txt")
                return 2
            return do_health(base, key)
        else:
            tokens.append(a); i += 1
    if not tokens:
        print(__doc__)
        return 1
    key = key or load_apikey()
    if not key:
        print("[macro_latest] 未配置 API Key：请设置环境变量 ATTRACTOR_API_KEY，"
              "或在脚本同目录放置 macro_apikey.txt")
        return 2
    sec_ids, _ = resolve_args(tokens)
    if sec_ids is None:
        return 3
    return do_query(base, key, sec_ids)


if __name__ == "__main__":
    sys.exit(main())
