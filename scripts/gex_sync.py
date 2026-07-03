import json
import os
import sys
import time
import urllib.request
from datetime import datetime, time as time_obj
from zoneinfo import ZoneInfo

CSV_HEADER = "datetime,expiration,callWall_strike,putWall_strike,gammaInflection,gammaZone,stockPrice"

BUCKET_MINUTES = 1  # change to 5, 15, etc. for coarser granularity

QUANTWHEEL_COOKIE = (
    "_gcl_au=1.1.2141382235.1780555467; "
    "_ga=GA1.1.2048354470.1780555467; "
    "_ga_5MRTTZNM3J=GS2.1.s1783098824$o57$g1$t1783098876$j8$l0$h1935861514; "
    "options_anon_id=aa04365f-4b2b-47f4-880b-642dbf4f1494; "
    "__Host-authjs.csrf-token=d8ec1f1e0c3dd21fe5fc7de2a016ffd7884b48a0976d2eabd6ce8d1732e07d95%7C4d5dda5fdf139fdffb21fbe43ac3991ad1a233cb34c04540b669f2481a10b767; "
    "__Secure-authjs.session-token=eyJhbGciOiJkaXIiLCJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwia2lkIjoiTVVZX0p2ZDlxS1JfYXgxRktnR1VWZ1pKSEJ2QnRFNHdpU3hzSEFtYmc3R1FpeGRISXBKNEFBY0pIeDF6a0VnNmhQMWpkb3VZSVY2LUVYTXVpQi1jUmcifQ..b3_7_QrM8vqfBm47QXx7UA.47BH2hGlafzz_ReevX-xGFkVVDCBempsvVr0G_ZJ9t9RWtQ1C_U_xHwrBtNuIFCfUy8rNrdQixzG87gdHE0MaUWH22uSS6oeNDqE1QOuRX3upbNwe94Gg3kQ5x9XuSFGvKppeXi5LkC8VtVegDlinmzlnbU6V75er44jAJ9YQV5r9iyDGxML0nbte7Yqsu-mam9zDE0ge3ppPX3Ix65SvXzPP_AknAUPE9FyDVfKYxogoaoZUcIZQy_f348sOxJEDIbF0s8v35uDMhaDrh65ikrCyIPo5wUTBBB04zu8V8EmGabMGeIEHl2hDWYqZ5c4-A6erUOfhYGLiZGWZIYNCprs1S_Z01rs6ICaQGJfrIMNrPd55-9cdZZvUwhxctFeKsJkgelSNhxoj_lqVNRmXkLzfhkHrmhDXtvHEo0IuNuDpNyfB2D09AhCNtj5-wEKF-_CFIH4v-6KnJGxVTgzIhvf59y3IfP0C8fyUJDlcn0R4GrVT9YfD0muXKIOAufE.R8b1Q35MeLWZCO0CnDZtl9wquQLnxwSgRWsBv3NkPP0; "
    "__kla_id=eyJjaWQiOiJaV1E0TmpRd1pEY3RZakZqTUMwME5qZzFMVGt5TURNdFlUUm1aV05tTm1ZNVptSmoifQ==; "
    "_fbp=fb.1.1780555470208.69147752917263889; "
    "__Secure-authjs.callback-url=https%3A%2F%2Fquantwheel.com%2Fdashboard%3Fregistration_page%3Dtools-gex-calculator"
)


def get_bucket_interval(dt: datetime) -> int:
    return (dt.minute // BUCKET_MINUTES) * BUCKET_MINUTES


def floor_to_bucket(dt: datetime) -> datetime:
    m = get_bucket_interval(dt)
    return dt.replace(minute=m, second=0, microsecond=0)


def build_gex_url(expirations: str) -> str:
    return f"https://quantwheel.com/api/tools/gex?ticker=SPX&expirations={expirations}&deltaRange=all&formula=per_1pct"


def _format_csv_row(floored, expiration, cw_strike, pw_strike, gamma_infl, gamma_zone, stock_price):
    ts = floored.strftime("%Y-%m-%d %H:%M:%S")
    return f"{ts},{expiration} 00:00:00,{cw_strike},{pw_strike},{gamma_infl},{gamma_zone},{stock_price}"


def _already_in_csv(ts: str, path: str = "gex.csv") -> bool:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    with open(path) as f:
        return any(line.startswith(ts) for line in f)


def write_gex_csv(floored, expiration, cw_strike, pw_strike, gamma_infl, gamma_zone, stock_price,
                  path: str = "gex.csv") -> bool:
    ts = floored.strftime("%Y-%m-%d %H:%M:%S")
    if _already_in_csv(ts, path):
        print(f"[{datetime.now():%H:%M:%S}]  interval {ts} already in {path}, skipping")
        return False
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    row = _format_csv_row(floored, expiration, cw_strike, pw_strike, gamma_infl, gamma_zone, stock_price)
    with open(path, "a") as f:
        if new_file:
            f.write(CSV_HEADER + "\n")
        f.write(row + "\n")
    print(f"[{datetime.now():%H:%M:%S}]  NEW INTERVAL  ->  appended {ts}")
    return True


def fetch_gex(expirations: str) -> dict | None:
    url = build_gex_url(expirations)
    print(f"Fetching: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}
    if QUANTWHEEL_COOKIE:
        headers["Cookie"] = QUANTWHEEL_COOKIE
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
            data = json.loads(resp.read().decode())
        if "error" in data:
            print(f"API error: {data['error']}")
            return None
        return data
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.reason}")
        return None


ROME_TZ = ZoneInfo("Europe/Rome")


def _is_in_gex_window(now_rome: datetime) -> bool:
    """Return True if we're inside the GEX data window: 15:30–21:59 Europe/Rome."""
    start = time_obj(15, 30)
    end = time_obj(21, 59)
    return start <= now_rome.time() <= end


def sync_loop(expiration: str, interval_seconds: float = 5.0):
    print(f"Expiration: {expiration}")
    print(f"Bucket: {BUCKET_MINUTES}min  |  Polling every {interval_seconds}s")
    print(f"Window: 15:30–21:59 Europe/Rome\nCtrl+C to stop\n")
    last = None
    try:
        while True:
            now_rome = datetime.now(ROME_TZ)
            if not _is_in_gex_window(now_rome):
                print(f"[{now_rome:%H:%M:%S}]  outside GEX window (15:30–21:59 Rome), waiting...")
                time.sleep(interval_seconds)
                continue
            now = datetime.now()
            floored = floor_to_bucket(now)
            if floored == last:
                print(f"[{now:%H:%M:%S}]  same interval ({floored:%H:%M}), waiting...")
                time.sleep(interval_seconds)
                continue
            last = floored
            ts = floored.strftime("%Y-%m-%d %H:%M:%S")
            # Second guard: covers restarts where the interval is already on disk.
            # The first guard (floored==last) only works within the same process lifetime.
            if _already_in_csv(ts):
                print(f"[{now:%H:%M:%S}]  interval {ts} already in gex.csv, skipping")
                time.sleep(interval_seconds)
                continue
            data = fetch_gex(expiration)
            cw = data["callWall"]["strike"] if data else ""
            pw = data["putWall"]["strike"] if data else ""
            gi = data.get("gammaInflection", "") if data else ""
            gz = data.get("gammaZone", "") if data else ""
            sp = data.get("stockPrice", "") if data else ""
            write_gex_csv(floored, expiration, cw, pw, gi, gz, sp)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    expiration = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    sync_loop(expiration)
