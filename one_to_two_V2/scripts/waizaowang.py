"""独立脚本：从歪枣网API拉取涨停数据并保存为标准AkShare缓存格式。

使用方式:
    python scripts/waizaowang.py --start 2025-08-01 --end 2025-12-31
    python scripts/waizaowang.py --start 2025-08-01  # 到今天
    python scripts/waizaowang.py --start 2025-08-01 --end 2025-08-05 --dry-run  # 预览

标准缓存格式（26列）:
    序号,代码,名称,涨跌幅,最新价,成交额,流通市值,总市值,换手率,封板资金,
    首次封板时间,最后封板时间,炸板次数,涨停统计,连板数,所属行业,
    date,symbol,name,board_count,change_pct,circ_mv,turnover,amount,first_seal_time,open_times
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

import pandas as pd
import requests

TOKEN = "2e7c7267f6d4d91aaf44de7b1aae5be3"
BASE_URL = "http://api.waizaowang.com/doc/getPoolZT"
CACHE_DIR = Path(__file__).parent.parent / "data" / "cache" / "zt"
CALENDAR_FILE = Path(__file__).parent.parent / "data" / "cache" / "trade_calendar.csv"

STANDARD_COLUMNS = [
    "序号", "代码", "名称", "涨跌幅", "最新价", "成交额", "流通市值", "总市值",
    "换手率", "封板资金", "首次封板时间", "最后封板时间", "炸板次数", "涨停统计",
    "连板数", "所属行业", "date", "symbol", "name", "board_count", "change_pct",
    "circ_mv", "turnover", "amount", "first_seal_time", "open_times"
]


def load_trade_calendar() -> Set[str]:
    """Load trade calendar and return set of trade dates (YYYYMMDD format)."""
    if not CALENDAR_FILE.exists():
        print(f"[WARN] 交易日历不存在: {CALENDAR_FILE}")
        print("[WARN] 将无法过滤非交易日数据")
        return set()
    
    df = pd.read_csv(CALENDAR_FILE)
    dates = df["date"].astype(str).str.replace("-", "").tolist()
    return set(dates)


def fetch_zt_pool(
    start_date: str,
    end_date: str,
    max_retries: int = 3,
    retry_sleep: float = 1.0,
    timeout: float = 60.0,
) -> pd.DataFrame:
    """从歪枣网API获取涨停池数据。
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD格式)
        end_date: 结束日期 (YYYY-MM-DD格式)
        max_retries: 最大重试次数
        retry_sleep: 重试间隔秒数
        timeout: 请求超时秒数
        
    Returns:
        DataFrame with raw API data
    """
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "fields": "all",
        "export": 1,
        "token": TOKEN,
    }
    
    last_err: Optional[Exception] = None
    
    for i in range(max_retries):
        try:
            print(f"  请求: {start_date} ~ {end_date} ...")
            response = requests.get(BASE_URL, params=params, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != 200:
                raise RuntimeError(f"API错误: {data.get('message')}")
            
            records = data.get("data", [])
            if not records:
                print(f"  无数据返回")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            print(f"  获取 {len(df)} 条记录")
            return df
            
        except requests.exceptions.Timeout as e:
            last_err = e
            print(f"  [WARN] 请求超时 (尝试 {i + 1}/{max_retries})")
        except requests.exceptions.ConnectionError as e:
            last_err = e
            print(f"  [WARN] 连接错误 (尝试 {i + 1}/{max_retries})")
        except Exception as e:
            last_err = e
            print(f"  [WARN] 请求失败 (尝试 {i + 1}/{max_retries}): {e}")
        
        if i < max_retries - 1:
            time.sleep(retry_sleep)
    
    raise RuntimeError(f"API请求失败: {last_err}")


def convert_to_akshare_format(df: pd.DataFrame) -> pd.DataFrame:
    """将歪枣网数据转换为标准AkShare缓存格式（26列）。
    
    歪枣网字段映射:
        tdate -> date (YYYYMMDD)
        code -> symbol (6位补零)
        n -> name
        lbc -> board_count
        zdp -> change_pct
        amount -> amount
        ltsz -> circ_mv
        tshare -> total_mv
        hs -> turnover
        fund -> seal_fund
        fbt -> first_seal_time (去掉冒号)
        lbt -> last_seal_time (去掉冒号)
        zbc -> open_times
        zttj -> zt_stat
        hybk -> industry
        p -> price
    """
    if df.empty:
        return pd.DataFrame()
    
    result = pd.DataFrame()
    
    result["序号"] = range(1, len(df) + 1)
    result["代码"] = df["code"].astype(str).str.zfill(6)
    result["名称"] = df["n"]
    result["涨跌幅"] = pd.to_numeric(df["zdp"], errors="coerce")
    result["最新价"] = pd.to_numeric(df.get("p", 0), errors="coerce")
    result["成交额"] = pd.to_numeric(df["amount"], errors="coerce")
    result["流通市值"] = pd.to_numeric(df["ltsz"], errors="coerce")
    result["总市值"] = pd.to_numeric(df.get("tshare", df["ltsz"]), errors="coerce")
    result["换手率"] = pd.to_numeric(df["hs"], errors="coerce")
    result["封板资金"] = pd.to_numeric(df.get("fund", 0), errors="coerce")
    
    result["首次封板时间"] = df["fbt"].astype(str).str.replace(":", "")
    result["最后封板时间"] = df["lbt"].astype(str).str.replace(":", "")
    
    result["炸板次数"] = pd.to_numeric(df["zbc"], errors="coerce").fillna(0).astype(int)
    result["涨停统计"] = df.get("zttj", "")
    result["连板数"] = pd.to_numeric(df["lbc"], errors="coerce").fillna(1).astype(int)
    result["所属行业"] = df.get("hybk", "")
    
    result["date"] = df["tdate"].astype(str).str.replace("-", "")
    result["symbol"] = df["code"].astype(str).str.zfill(6)
    result["name"] = df["n"]
    result["board_count"] = pd.to_numeric(df["lbc"], errors="coerce").fillna(1).astype(int)
    result["change_pct"] = pd.to_numeric(df["zdp"], errors="coerce")
    result["circ_mv"] = pd.to_numeric(df["ltsz"], errors="coerce")
    result["turnover"] = pd.to_numeric(df["hs"], errors="coerce")
    result["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    result["first_seal_time"] = df["fbt"].astype(str).str.replace(":", "")
    result["open_times"] = pd.to_numeric(df["zbc"], errors="coerce").fillna(0).astype(int)
    
    return result[STANDARD_COLUMNS]


def filter_trade_days(df: pd.DataFrame, trade_dates: Set[str]) -> pd.DataFrame:
    """Filter DataFrame to only include trade days.
    
    Args:
        df: DataFrame with 'date' column (YYYYMMDD format)
        trade_dates: Set of valid trade dates
        
    Returns:
        Filtered DataFrame
    """
    if df.empty or not trade_dates:
        return df
    
    original_count = len(df)
    df = df[df["date"].isin(trade_dates)].copy()
    filtered_count = original_count - len(df)
    
    if filtered_count > 0:
        print(f"  过滤非交易日: {filtered_count} 条记录")
    
    return df


def save_to_cache(df: pd.DataFrame, cache_dir: Path, trade_dates: Set[str]) -> dict[str, int]:
    """按日期分组保存到缓存文件。
    
    如果缓存文件已存在，会跳过该日期（不覆盖已有数据）。
    非交易日数据会被跳过。
    
    Args:
        df: 标准格式的DataFrame
        cache_dir: 缓存目录
        trade_dates: 有效交易日集合
        
    Returns:
        日期到记录数的映射
    """
    if df.empty or "date" not in df.columns:
        return {}
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    saved_counts = {}
    skipped_non_trade = []
    
    for date, group in df.groupby("date"):
        if trade_dates and date not in trade_dates:
            skipped_non_trade.append(date)
            continue
        
        cache_path = cache_dir / f"zt_{date}.csv"
        
        if cache_path.exists():
            print(f"    {date}: 跳过 (缓存已存在)")
            continue
        
        group.to_csv(cache_path, index=False)
        saved_counts[str(date)] = len(group)
        print(f"    {date}: 保存 {len(group)} 条")
    
    if skipped_non_trade:
        print(f"  跳过非交易日: {', '.join(skipped_non_trade)}")
    
    return saved_counts


def main():
    parser = argparse.ArgumentParser(
        description="从歪枣网API拉取涨停数据并保存为标准AkShare缓存格式"
    )
    parser.add_argument(
        "--start", "-s",
        required=True,
        help="开始日期 (YYYY-MM-DD格式)"
    )
    parser.add_argument(
        "--end", "-e",
        default=None,
        help="结束日期 (YYYY-MM-DD格式，默认为今天)"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="仅预览，不保存文件"
    )
    
    args = parser.parse_args()
    
    start_date = args.start
    end_date = args.end or datetime.now().strftime("%Y-%m-%d")
    
    print("=" * 60)
    print("歪枣网涨停数据拉取工具")
    print("=" * 60)
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"缓存目录: {CACHE_DIR}")
    print()
    
    trade_dates = load_trade_calendar()
    if trade_dates:
        print(f"交易日历: 已加载 {len(trade_dates)} 个交易日")
    print()
    
    df = fetch_zt_pool(start_date, end_date)
    
    if df.empty:
        print("无数据，退出")
        return
    
    print()
    print("转换格式...")
    df_std = convert_to_akshare_format(df)
    
    print(f"  标准格式: {len(df_std.columns)} 列")
    print(f"  日期范围: {df_std['date'].min()} ~ {df_std['date'].max()}")
    print(f"  原始日期数: {df_std['date'].nunique()}")
    
    df_std = filter_trade_days(df_std, trade_dates)
    
    print(f"  过滤后日期数: {df_std['date'].nunique()}")
    print()
    
    if args.dry_run:
        print("[DRY-RUN] 预览模式，不保存文件")
        print()
        print("列名:")
        print(f"  {list(df_std.columns)}")
        print()
        print("示例数据:")
        print(df_std.head(3).to_string())
        return
    
    print("保存缓存...")
    saved = save_to_cache(df_std, CACHE_DIR, trade_dates)
    
    print()
    print("=" * 60)
    print(f"完成: 保存 {len(saved)} 个文件")
    print("=" * 60)


if __name__ == "__main__":
    main()
