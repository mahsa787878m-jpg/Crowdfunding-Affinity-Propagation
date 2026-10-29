"""رابط وب برای بارگذاری اکسل فرابورس و دریافت جدول استخراج‌شده."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from ifb_extract.excel_io import excel_bytes
from ifb_extract.pipeline import detect_text_column, process_dataframe, summary
from ifb_extract.platforms import build_matchers, load_platform_file

def _json_cell(row: dict[str, object]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in row.items():
        if isinstance(value, float) and value.is_integer():
            cleaned[key] = int(value)
        else:
            cleaned[key] = "" if value is None else value
    return cleaned


app = FastAPI(title="استخراج طرح‌های تأمین مالی جمعی")
_PAGE = Path(__file__).with_name("templates") / "index.html"


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _PAGE.read_text(encoding="utf-8")


def _read_excel(upload: UploadFile) -> pd.DataFrame:
    name = (upload.filename or "").lower()
    if not name.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="فقط فایل xlsx پذیرفته می‌شود.")
    payload = upload.file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="فایل خالی است.")
    if len(payload) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="حجم فایل بیشتر از ۱۵ مگابایت است.")
    try:
        return pd.read_excel(io.BytesIO(payload))
    except Exception as exc:  # noqa: BLE001 - پیام فارسی برای فایل خراب
        raise HTTPException(status_code=400, detail="فایل اکسل خوانده نشد. آن را با فرمت xlsx ذخیره کنید.") from exc


@app.post("/api/extract")
async def extract(
    file: UploadFile = File(...),
    platforms: UploadFile | None = File(default=None),
) -> dict[str, object]:
    frame = _read_excel(file)
    matchers = None
    if platforms is not None and platforms.filename:
        if not platforms.filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="فایل سکوها باید xlsx باشد.")
        temporary = Path("/tmp/ifb-platforms.xlsx")
        temporary.write_bytes(await platforms.read())
        try:
            extra = load_platform_file(str(temporary))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            temporary.unlink(missing_ok=True)
        matchers = build_matchers(extra)

    try:
        text_column = detect_text_column(frame)
        cleaned = process_dataframe(frame, text_column, matchers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    preview = cleaned.drop(columns=["متن مرجع"]).head(40)
    preview = preview.where(pd.notna(preview), "")
    records = [_json_cell(row) for row in preview.to_dict(orient="records")]
    counts = {name: {"filled": filled, "total": total} for name, (filled, total) in summary(cleaned).items()}
    return {
        "text_column": text_column,
        "rows": int(len(cleaned)),
        "summary": counts,
        "preview": records,
        "columns": list(preview.columns),
        "xlsx_base64": base64.b64encode(excel_bytes(cleaned)).decode("ascii"),
        "filename": "IFB_CrowdFunding_Projects_Clean.xlsx",
    }
