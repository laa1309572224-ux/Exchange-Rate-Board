import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "push_config.json"
GOLD_DATA = ROOT / "gold_data.json"
CURRENCIES = {
    "USD": ("美元", 665.95), "EUR": ("欧元", 743.35),
    "GBP": ("英镑", 887.34), "CAD": ("加拿大元", 473.68),
    "HKD": ("港币", 84.88), "AUD": ("澳大利亚元", 466.65),
    "JPY": ("日元", 4.218), "SGD": ("新加坡元", 518.97),
}
DEFAULT_CONFIG = {
    "amount_mxn": 10000,
    "spreads": {"USD": 3, "EUR": 4, "GBP": 5, "CAD": 5, "HKD": 6, "AUD": 6, "JPY": 7, "SGD": 6},
}


def get_json(url, payload=None):
    body = json.dumps(payload, ensure_ascii=False).encode() if payload else None
    request = Request(url, data=body, headers={"User-Agent": "MXN-CNY-Monitor/1.0", "Content-Type": "application/json"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode())


def boc_cash_rates():
    request = Request("https://www.boc.cn/sourcedb/whpj/", headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        page = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    result = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
        if len(cells) >= 3:
            for code, (name, _) in CURRENCIES.items():
                if cells[0] == name and cells[2]:
                    try:
                        result[code] = float(cells[2])
                    except ValueError:
                        pass
    return result


def calculate(config):
    market = get_json("https://open.er-api.com/v6/latest/MXN")
    if market.get("result") != "success" or not market.get("rates", {}).get("CNY"):
        raise RuntimeError("在线汇率接口返回失败")
    try:
        cash = boc_cash_rates()
    except Exception:
        cash = {}
    amount = float(config["amount_mxn"])
    rows = []
    for code, (name, fallback_cash) in CURRENCIES.items():
        cash_rate = cash.get(code, fallback_cash)
        spread = float(config["spreads"][code])
        foreign = amount * market["rates"][code] * (1 - spread / 100)
        cny = foreign * cash_rate / 100
        rows.append({"code": code, "name": name, "foreign": foreign, "cash": cash_rate, "spread": spread, "cny": cny})
    rows.sort(key=lambda row: row["cny"], reverse=True)
    mexico = ZoneInfo("America/Mexico_City")
    fetched_at = datetime.now(mexico).strftime("%Y-%m-%d %H:%M")
    source_at = datetime.fromtimestamp(market["time_last_update_unix"], mexico).strftime("%Y-%m-%d %H:%M")
    return rows, bool(cash), fetched_at, source_at


def week_trends(code):
    end = datetime.now().date()
    start = end - timedelta(days=12)
    url = f"https://api.frankfurter.dev/v1/{start}..{end}?base=MXN&symbols={code},CNY"
    data = get_json(url)
    points = list(data.get("rates", {}).items())[-7:]
    first = [rates[code] for _, rates in points]
    second = [rates["CNY"] / rates[code] for _, rates in points]
    return [date[5:] for date, _ in points], first, second


def gold_snapshot():
    history = json.loads(GOLD_DATA.read_text(encoding="utf-8")).get("history", [])
    if not history or any(float(point["price"]) <= 0 for point in history):
        raise RuntimeError("金价历史数据无效")
    return history[-1], history[-7:]


def sparkline(values):
    blocks = "▁▂▃▄▅▆▇█"
    low, high = min(values), max(values)
    if high == low:
        return blocks[3] * len(values)
    return "".join(blocks[round((value - low) / (high - low) * 7)] for value in values)


def trend_line(label, dates, values, digits):
    change = (values[-1] / values[0] - 1) * 100 if values[0] else 0
    return f"**{label}**  `{sparkline(values)}`  {values[0]:.{digits}f} → {values[-1]:.{digits}f}（{change:+.2f}%）"


def chart_url(title, dates, series):
    config = {
        "type": "line",
        "data": {
            "labels": dates,
            "datasets": [{
                "label": label, "data": values, "borderColor": color,
                "backgroundColor": color + "12", "borderWidth": 3,
                "pointRadius": 3, "pointBackgroundColor": color, "fill": False,
            } for label, values, color in series],
        },
        "options": {
            "title": {"display": True, "text": title, "fontSize": 18, "fontColor": "#13213c"},
            "legend": {"display": True, "position": "bottom"},
            "scales": {
                "xAxes": [{"gridLines": {"display": False}}],
                "yAxes": [{"ticks": {"beginAtZero": False}, "gridLines": {"color": "#e7ebf2"}}],
            },
        },
    }
    result = get_json("https://quickchart.io/chart/create", {
        "chart": config, "width": 700, "height": 280,
        "devicePixelRatio": 2, "backgroundColor": "white",
    })
    if not result.get("success") or not result.get("url"):
        raise RuntimeError("趋势图生成失败")
    return result["url"]


def message(config, rows, live_boc, fetched_at, source_at):
    best, second = rows[:2]
    dates, first_trend, second_trend = week_trends(best["code"])
    gold, gold_week = gold_snapshot()
    market_rate = best["foreign"] / float(config["amount_mxn"])
    cny_rate = best["cash"] / 100
    normalize = lambda values: [round(value / values[0] * 100, 4) for value in values]
    try:
        summary_chart = chart_url("近一周两段汇率趋势（首日 = 100）", dates, [
            (f"MXN → {best['code']}", normalize(first_trend), "#2457e6"),
            (f"{best['code']} → CNY", normalize(second_trend), "#0b9f75"),
        ])
    except Exception:
        summary_chart = None
    try:
        gold_chart = chart_url("工商银行如意金条购买参考价 · 近一周", [point["date"][5:] for point in gold_week], [
            ("CNY/克", [float(point["price"]) for point in gold_week], "#b58a19"),
        ])
    except Exception:
        gold_chart = None
    lines = [
        "## 每日汇率分段报告",
        f"> 当天汇率抓取：**{fetched_at}（墨西哥城）**",
        f"> 市场汇率报价时间：{source_at}（墨西哥城）",
        f"> 本金：**{float(config['amount_mxn']):,.0f} MXN**",
        "",
        "### 工商银行如意金条｜50g",
        f"- 当日购买参考价：**¥{float(gold['price']):,.2f}/克**（{gold['date']}）",
        f"- 购买 50g 预计总价：**¥{float(gold['price']) * 50:,.2f}**",
        trend_line("近一周金价", [point["date"][5:] for point in gold_week], [float(point["price"]) for point in gold_week], 2),
        *([f"![近一周金价趋势]({gold_chart})"] if gold_chart else ["> 金价图片服务暂时不可用，以上字符趋势仍可正常参考。"]),
        "",
        f"### 第一段汇率｜MXN → {best['code']}",
        f"- 当前有效汇率：1 MXN = **{market_rate:.6f} {best['code']}**",
        f"- 第一段结果：**{float(config['amount_mxn']):,.0f} MXN → {best['foreign']:,.2f} {best['code']}**",
        f"- 已扣除墨西哥端损耗：{best['spread']:.1f}%",
        trend_line(f"近一周 MXN→{best['code']}", dates, first_trend, 6),
        "",
        f"### 第二段汇率｜{best['code']} → CNY",
        f"- 当前现钞汇率：1 {best['code']} = **{cny_rate:.4f} CNY**",
        f"- 中行现钞买入价：{best['cash']:.4f} CNY / 100 {best['code']}",
        f"- 第二段结果：**{best['foreign']:,.2f} {best['code']} → ¥{best['cny']:,.2f} CNY**",
        trend_line(f"近一周 {best['code']}→CNY", dates, second_trend, 4),
        "",
        "### 汇率结果总结",
        f"**{float(config['amount_mxn']):,.0f} MXN → {best['foreign']:,.2f} {best['code']} → ¥{best['cny']:,.2f} CNY**",
        f"- 最优路径：MXN → **{best['code']}** → CNY",
        f"- 比第二名 {second['code']} 多得：**¥{best['cny'] - second['cny']:,.2f}**",
        f"- 趋势区间：{dates[0]} 至 {dates[-1]}（最近 7 个工作日）",
        *([f"![两段汇率趋势总结]({summary_chart})"] if summary_chart else ["> 图片服务暂时不可用，以上字符趋势仍可正常参考。"]),
        "",
        "|排名|路径|预计人民币|",
        "|---:|---|---:|",
    ]
    lines.extend(f"|{index}|MXN → {row['code']} → CNY|¥{row['cny']:,.2f}|" for index, row in enumerate(rows, 1))
    source = "中国银行实时现钞买入价" if live_boc else "中行备用参考价"
    lines += ["", f"> 口径：在线市场汇率 + 当前损耗设置 + {source}。实际成交以柜台为准。"]
    return {"msgtype": "markdown", "markdown": {"title": "每日汇率最优结果", "text": "\n".join(lines)}}


def send_dingtalk(webhook, payload, attempts=3):
    for attempt in range(1, attempts + 1):
        result = get_json(webhook, payload)
        if result.get("errcode") == 0:
            return
        if attempt < attempts:
            time.sleep(attempt * 5)
    raise RuntimeError(f"钉钉推送失败：{result.get('errmsg', result)}")


def main(dry_run=False):
    config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else DEFAULT_CONFIG.copy()
    config["webhook"] = os.environ.get("DINGTALK_WEBHOOK", config.get("webhook", ""))
    if not dry_run and not config["webhook"]:
        raise RuntimeError("未配置 DINGTALK_WEBHOOK")
    rows, live_boc, fetched_at, source_at = calculate(config)
    payload = message(config, rows, live_boc, fetched_at, source_at)
    if dry_run:
        print(payload["markdown"]["text"])
        return
    send_dingtalk(config["webhook"], payload)
    print("钉钉汇率推送成功")


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
