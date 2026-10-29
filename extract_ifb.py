#!/usr/bin/env python3
"""خواندن طرح‌ها از سایت فرابورس و استخراج ستون‌ها.

بدون مسیر فایل، از این نشانی می‌خواند:
https://www.ifb.ir/Finstars/AllCrowdFundingProject.aspx

    python extract_ifb.py
    python extract_ifb.py --from-page 77 --to-page 3
    python extract_ifb.py --pages 10
    python extract_ifb.py مسیر/فایل.xlsx
    python fill_crowdfa.py مسیر/فایل.xlsx
    python extract_ifb.py مسیر/فایل.xlsx --crowdfa
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from ifb_extract.excel_io import write_excel
from ifb_extract.fetch import (
    LIST_URL,
    RANGE_END_DATE,
    RANGE_FROM_PAGE,
    RANGE_START_DATE,
    RANGE_TO_PAGE,
    FetchError,
    fetch_projects,
)
from ifb_extract.pipeline import matchers_from_file, process_dataframe, process_workbook, summary

PAGE_SIZE = 10


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="خواندن طرح‌های تأمین مالی جمعی از سایت فرابورس")
    parser.add_argument("input", nargs="?", help="اگر فایل اکسل بدهید همان پردازش می‌شود؛ وگرنه از سایت خوانده می‌شود")
    parser.add_argument("--pages", type=int, default=None, help="از صفحه ۱ به این تعداد صفحه. اگر ندهید از صفحه ۷۷ تا ۳ خوانده می‌شود")
    parser.add_argument("--from-page", type=int, default=None, help="صفحهٔ شروع. پیش‌فرض ۷۷، ابتدای ۱۴۰۵/۰۱/۰۹")
    parser.add_argument("--to-page", type=int, default=None, help="صفحهٔ پایان. پیش‌فرض ۳، انتهای ۱۴۰۵/۰۶/۳۱")
    parser.add_argument("-o", "--output", help="مسیر فایل خروجی")
    parser.add_argument("--platforms", help="فایل اختیاری سکوها با ستون‌های نام سکو و دامنه")
    parser.add_argument("--text-column", help="نام ستون متن، فقط وقتی فایل اکسل می‌دهید")
    parser.add_argument("--crowdfa", action="store_true", help="خانه‌های خالی همین اکسل را از crowdfa.ir با شناسه ملی پر می‌کند")
    args = parser.parse_args(argv)

    if args.crowdfa:
        if not args.input:
            print("فایل اکسل را هم بدهید: python fill_crowdfa.py مسیر/فایل.xlsx", file=sys.stderr)
            return 1
        from fill_crowdfa import main as fill_crowdfa

        forwarded = [args.input]
        if args.output:
            forwarded.extend(["-o", args.output])
        return fill_crowdfa(forwarded)

    base = Path.cwd()
    if args.input:
        source = Path(args.input)
        if not source.is_file():
            print(f"فایل پیدا نشد: {source}", file=sys.stderr)
            return 1
        print(f"در حال خواندن فایل {source.name} ...")
        frame = process_workbook(source, args.text_column, args.platforms)
    else:
        if args.from_page is not None or args.to_page is not None or args.pages is None:
            from_page = RANGE_FROM_PAGE if args.from_page is None else args.from_page
            to_page = RANGE_TO_PAGE if args.to_page is None else args.to_page
            pages = None
        else:
            from_page = None
            to_page = None
            pages = args.pages if args.pages >= 1 else 1
        print(f"اتصال به {LIST_URL}")
        if from_page is not None and to_page is not None:
            print(
                f"خواندن از ابتدای صفحه {from_page} تا انتهای صفحه {to_page}، "
                f"هر صفحه {PAGE_SIZE} طرح ({RANGE_START_DATE} تا {RANGE_END_DATE}) ..."
            )
        else:
            print(f"خواندن {pages} صفحه از ابتدای فهرست، هر صفحه {PAGE_SIZE} طرح ...")
        try:
            source_frame = fetch_projects(pages=pages, from_page=from_page, to_page=to_page, log=print)
        except FetchError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"از سایت {len(source_frame)} طرح گرفته شد.")
        print("نام شرکت، نام سکو و تاریخ‌ها با شناسه ملی جدول پر می‌شوند. تاریخِ نخوانده هشدار ۱ می‌گیرد.")
        frame = process_dataframe(source_frame, matchers=matchers_from_file(args.platforms))

    print(f"تعداد طرح‌ها: {len(frame)}")
    for name, (filled, total) in summary(frame).items():
        print(f"  {name}: {filled} از {total}")

    if args.output:
        destination = Path(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = base / "output" / f"IFB_CrowdFunding_Projects_Clean_{stamp}.xlsx"
    write_excel(frame, destination)
    print("فایل خروجی ساخته شد.")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
