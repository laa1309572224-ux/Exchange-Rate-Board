import json
import re
import ssl
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://mybank.icbc.com.cn/icbc/newperbank/perbank3/gold/realgold_query_out.jsp"
OUT = Path(__file__).with_name("gold_data.json")


def extract(html):
    price = float(re.search(r'id="last_080020000214">([\d.]+)', html).group(1))
    previous = float(re.search(r'id="lstclose_080020000214">([\d.]+)', html).group(1))
    date, time = re.search(r"TRANSDATE','(\d{8})'[\s\S]*?TRANSTIME','(\d{6})'", html).groups()
    return price, previous, f"{date[:4]}-{date[4:6]}-{date[6:]}", f"{time[:2]}:{time[2:4]}"


def main():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    context = ssl.create_default_context()
    context.options |= ssl.OP_LEGACY_SERVER_CONNECT
    html = urlopen(request, timeout=30, context=context).read().decode("gbk", errors="ignore")
    price, previous, date, time = extract(html)
    data = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"history": []}
    history = data.get("history", [])
    if not history and previous:
        yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        history.append({"date": yesterday, "price": previous, "time": "昨日收盘"})
    item = {"date": date, "price": price, "time": time}
    history = [row for row in history if row["date"] != date] + [item]
    OUT.write_text(json.dumps({"source": URL, "history": history[-30:]}, ensure_ascii=False, indent=2), "utf-8")


if __name__ == "__main__":
    assert extract('<i id="last_080020000214">864.00</i><i id="lstclose_080020000214">861.41</i><script>TRANSDATE\',\'20261027\';TRANSTIME\',\'043009\'</script>') == (864.0, 861.41, "2026-10-27", "04:30")
    main()
