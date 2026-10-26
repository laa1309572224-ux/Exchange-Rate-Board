import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://www.huilvbiao.com/gold/tz_ruyi"
OUT = Path(__file__).with_name("gold_data.json")


def extract(html):
    raw = re.search(r"const data = (\[[^;]+\]);", html).group(1)
    return [
        {
            "date": row["update_time"].replace("年", "-").replace("月", "-").replace("日", ""),
            "price": float(row["jiage"]),
            "time": "每日挂牌",
        }
        for row in json.loads(raw)
    ]


def main():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(request, timeout=30).read().decode("utf-8", errors="ignore")
    fetched = extract(html)
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"history": []}
    merged = {row["date"]: row for row in data.get("history", []) if row.get("time") == "每日挂牌"} if data.get("source") == URL else {}
    merged.update({row["date"]: row for row in fetched})
    history = sorted(merged.values(), key=lambda row: datetime.strptime(row["date"], "%Y-%m-%d"))[-366:]
    OUT.write_text(json.dumps({"source": URL, "product": "工商银行如意金条购买参考价", "history": history}, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    assert extract('<script>const data = [{"jiage": 874.59, "update_time": "2026年10月26日"}];</script>') == [{"date": "2026-10-26", "price": 874.59, "time": "每日挂牌"}]
    main()
