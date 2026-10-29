#!/usr/bin/env python3
"""پر کردن خانه‌های خالی اکسل از https://crowdfa.ir/projects

این فایل کنار extract_ifb.py است. شناسه ملی هر طرح از داخل صفحهٔ همان طرح
خوانده می‌شود و فقط همان ردیف اکسل کامل می‌شود.

    python fill_crowdfa.py output/فایل.xlsx
    python extract_ifb.py output/فایل.xlsx --crowdfa
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from ifb_extract.crowdfa import (
    DEFAULT_FROM_PAGE,
    DEFAULT_TO_PAGE,
    LIST_URL,
    CrowdfaError,
    apply_catalog,
    fetch_catalog,
)
from ifb_extract.excel_io import write_excel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="پر کردن سود، ضمانت و مبلغ خالی اکسل از کرادفا با شناسه ملی")
    parser.add_argument("input", help="فایل اکسل برنامه اصلی")
    parser.add_argument("--from-page", type=int, default=DEFAULT_FROM_PAGE, help="اولین صفحه فهرست کرادفا. پیش‌فرض ۱")
    parser.add_argument("--to-page", type=int, default=DEFAULT_TO_PAGE, help="آخرین صفحه فهرست کرادفا. پیش‌فرض ۲۳۵")
    parser.add_argument("--pause", type=float, default=0.12, help="مکث بین باز کردن طرح‌ها، به ثانیه")
    parser.add_argument("-o", "--output", help="مسیر فایل خروجی")
    args = parser.parse_args(argv)

    source = Path(args.input)
    if not source.is_file():
        print(f"فایل پیدا نشد: {source}", file=sys.stderr)
        return 1
    if args.from_page < 1 or args.to_page < args.from_page:
        print("بازه صفحه نامعتبر است.", file=sys.stderr)
        return 1

    frame = pd.read_excel(source)
    print(f"اکسل خوانده شد: {len(frame)} ردیف")
    print(f"اتصال به {LIST_URL}")
    print(f"بررسی صفحه {args.from_page} تا {args.to_page} و ورود به هر طرح برای شناسه ملی ...")
    try:
        catalog = fetch_catalog(args.from_page, args.to_page, pause_seconds=args.pause, log=print)
    except CrowdfaError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    filled, stats = apply_catalog(frame, catalog)
    print(f"ردیف‌های منطبق با شناسه ملی: {stats['matched']}")
    print(f"شناسه ملی نوشته‌شده: {stats['national_id']}")
    print(f"درصد سود پر شده: {stats['profit']}")
    print(f"نوع ضمانت پر شده: {stats['guarantee']}")
    print(f"مبلغ پر شده: {stats['amount']}")
    print(f"مدت طرح پر شده: {stats['months']}")
    print(f"ردیف بدون تطبیق: {stats['skipped']}")

    if args.output:
        destination = Path(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = Path.cwd() / "output" / f"IFB_CrowdFunding_Projects_Filled_{stamp}.xlsx"
    write_excel(filled, destination)
    print("فایل کامل‌شده ساخته شد.")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
