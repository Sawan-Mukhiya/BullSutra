import os
import uuid
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from bullsutra.core.errors import NotFound, ValidationError, Conflict
from bullsutra.core.security import Principal
from bullsutra.db.repositories import uploads, jobs, prices, fundamentals, securities
from bullsutra.schemas.uploads import UploadOut, UploadRowError

UPLOAD_DIR = Path("data/raw/uploads")

async def validate_upload(
    db: AsyncSession,
    upload_type: str,
    file: UploadFile,
    principal: Principal
) -> UploadOut:
    if upload_type not in ("prices_csv", "fundamentals_csv"):
        raise ValidationError(f"Invalid upload_type '{upload_type}'. Must be 'prices_csv' or 'fundamentals_csv'")

    if not file.filename.endswith(".csv"):
        raise ValidationError("Only .csv files are supported")

    # Read content
    contents = await file.read()
    if len(contents) > 20 * 1024 * 1024:
        raise ValidationError("File size exceeds 20 MB limit")

    upload_id = uuid.uuid4()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    staged_path = UPLOAD_DIR / f"{upload_id}.csv"
    with open(staged_path, "wb") as f:
        f.write(contents)

    # Validate with pandas
    errors: List[Dict[str, Any]] = []
    preview: List[Dict[str, Any]] = []
    row_count = 0

    try:
        df = pd.read_csv(staged_path, dtype=str)
        row_count = len(df)
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        errors.append({"row": 0, "field": "file", "message": f"Malformed CSV: {str(e)}"})
        df = pd.DataFrame()

    if not df.empty:
        if upload_type == "prices_csv":
            required = ["symbol", "trade_date", "close", "volume"]
            for req in required:
                if req not in df.columns:
                    errors.append({"row": 0, "field": req, "message": f"Missing required column '{req}'"})
            
            if not errors:
                for idx, row in df.iterrows():
                    row_num = idx + 1
                    # Validate date
                    try:
                        d = date.fromisoformat(str(row["trade_date"]).strip())
                    except Exception:
                        if len(errors) < 200:
                            errors.append({"row": row_num, "field": "trade_date", "message": "Invalid date format, expected YYYY-MM-DD"})
                    # Validate close
                    try:
                        c = float(row["close"])
                        if c <= 0:
                            if len(errors) < 200:
                                errors.append({"row": row_num, "field": "close", "message": "Close must be > 0"})
                    except Exception:
                        if len(errors) < 200:
                            errors.append({"row": row_num, "field": "close", "message": "Close must be a valid number"})
                    # Validate volume
                    try:
                        v = int(float(row["volume"]))
                        if v < 0:
                            if len(errors) < 200:
                                errors.append({"row": row_num, "field": "volume", "message": "Volume must be >= 0"})
                    except Exception:
                        if len(errors) < 200:
                            errors.append({"row": row_num, "field": "volume", "message": "Volume must be an integer"})

                    # Envelope check
                    try:
                        if "high" in row and "low" in row and pd.notna(row["high"]) and pd.notna(row["low"]):
                            h = float(row["high"])
                            l = float(row["low"])
                            c = float(row["close"])
                            if l > h or c > h or c < l:
                                if len(errors) < 200:
                                    errors.append({"row": row_num, "field": "envelope", "message": "Low <= Close <= High violated"})
                    except Exception:
                        pass
        else: # fundamentals_csv
            required = ["symbol", "fiscal_year", "quarter"]
            for req in required:
                if req not in df.columns:
                    errors.append({"row": 0, "field": req, "message": f"Missing required column '{req}'"})
            if not errors:
                for idx, row in df.iterrows():
                    row_num = idx + 1
                    try:
                        q = int(row["quarter"])
                        if q < 1 or q > 4:
                            if len(errors) < 200:
                                errors.append({"row": row_num, "field": "quarter", "message": "Quarter must be between 1 and 4"})
                    except Exception:
                        if len(errors) < 200:
                            errors.append({"row": row_num, "field": "quarter", "message": "Quarter must be an integer between 1 and 4"})

        # Preview first 20 valid rows
        preview = df.head(20).to_dict(orient="records")

    status = "validated" if len(errors) == 0 else "rejected"
    upload_rec = await uploads.create_upload(
        db,
        upload_type=upload_type,
        filename=file.filename,
        staged_path=str(staged_path),
        created_by=principal.id if principal else None
    )
    upload_rec.id = upload_id
    upload_rec.status = status
    upload_rec.row_count = row_count
    upload_rec.error_count = len(errors)
    upload_rec.errors = errors
    await db.commit()

    return UploadOut(
        id=str(upload_id),
        upload_type=upload_type,
        filename=file.filename,
        status=status,
        row_count=row_count,
        error_count=len(errors),
        errors=errors,
        preview=preview,
        created_at=upload_rec.created_at,
        committed_at=None
    )

async def commit_upload(
    db: AsyncSession,
    upload_id: uuid.UUID,
    principal: Principal
) -> UploadOut:
    rec = await uploads.get_upload(db, upload_id)
    if not rec:
        raise NotFound(f"Upload '{upload_id}' not found")
    if rec.status != "validated":
        raise Conflict(f"Upload cannot be committed in status '{rec.status}'")

    if rec.row_count > 50000 and rec.upload_type == "prices_csv":
        raise ValidationError("Files above 50,000 rows should use the CLI")

    if rec.row_count > 5000 and rec.upload_type == "fundamentals_csv":
        # Enqueue job
        job = await jobs.enqueue(
            db,
            kind="fundamentals_import",
            payload={"upload_id": str(upload_id), "path": rec.staged_path},
            created_by=principal.id if principal else None
        )
        rec.status = "processing"
        await db.commit()
        return UploadOut(
            id=str(rec.id),
            upload_type=rec.upload_type,
            filename=rec.filename,
            status="processing",
            row_count=rec.row_count,
            error_count=rec.error_count,
            errors=rec.errors or [],
            preview=None,
            created_at=rec.created_at,
            committed_at=None
        )

    # Inline commit
    df = pd.read_csv(rec.staged_path)
    df.columns = [c.strip().lower() for c in df.columns]

    if rec.upload_type == "prices_csv":
        bars_to_insert = []
        for _, row in df.iterrows():
            sym = str(row["symbol"]).strip().upper()
            sec = await securities.get_by_symbol(db, sym)
            sec_id = sec.id if sec else None
            if not sec_id:
                continue
            bars_to_insert.append({
                "security_id": sec_id,
                "symbol": sym,
                "trade_date": date.fromisoformat(str(row["trade_date"]).strip()),
                "open": float(row["open"]) if pd.notna(row.get("open")) else None,
                "high": float(row["high"]) if pd.notna(row.get("high")) else None,
                "low": float(row["low"]) if pd.notna(row.get("low")) else None,
                "close": float(row["close"]),
                "volume": int(float(row["volume"])),
                "turnover": float(row["turnover"]) if pd.notna(row.get("turnover")) else 0.0,
                "bar_source": "upload",
                "quality_tier": "A",
                "limit_pct": 10.0,
                "regime_id": "regime_1"
            })
        if bars_to_insert:
            await prices.upsert_bars(db, bars_to_insert)

    await uploads.mark_committed(db, upload_id)
    await db.commit()
    rec = await uploads.get_upload(db, upload_id)

    return UploadOut(
        id=str(rec.id),
        upload_type=rec.upload_type,
        filename=rec.filename,
        status=rec.status,
        row_count=rec.row_count,
        error_count=rec.error_count,
        errors=rec.errors or [],
        preview=None,
        created_at=rec.created_at,
        committed_at=rec.committed_at
    )

async def list_uploads_service(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[UploadOut], int]:
    recs, total = await uploads.list_uploads(db, limit=limit, offset=offset)
    items = [
        UploadOut(
            id=str(r.id),
            upload_type=r.upload_type,
            filename=r.filename,
            status=r.status,
            row_count=r.row_count,
            error_count=r.error_count,
            errors=r.errors or [],
            preview=None,
            created_at=r.created_at,
            committed_at=r.committed_at
        ) for r in recs
    ]
    return items, total
