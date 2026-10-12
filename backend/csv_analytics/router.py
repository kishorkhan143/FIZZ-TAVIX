"""
CSV Analytics API Endpoints
===========================
FastAPI routes exposing CSV upload, validation, parsing, grouping,
security alerts, paginated records, and secure exports.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from csv_analytics.service import CsvAnalyticsService

router = APIRouter(prefix="/api/csv", tags=["CSV Analytics"])


class AlertStatusUpdate(BaseModel):
    status: str  # OPEN, INVESTIGATING, RESOLVED


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload, validate, normalize, score, and analyze a CSV security log file.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected or invalid filename.")

    try:
        contents = await file.read()
        result = CsvAnalyticsService.process_csv_upload(
            file_bytes=contents,
            filename=file.filename,
            db=db,
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"CSV processing encountered an internal error: {str(exc)}"
        )


@router.get("/summary")
def get_csv_summary(
    import_id: Optional[str] = Query(None, description="UUID of import, or latest if omitted"),
    db: Session = Depends(get_db),
):
    """
    Get high-level summary and chart metrics for the specified CSV import (or latest).
    """
    summary = CsvAnalyticsService.get_summary(import_id=import_id, db=db)
    if not summary.get("found"):
        raise HTTPException(status_code=404, detail="No CSV import data found.")
    return summary


@router.get("/analysis/{import_id}")
def get_csv_analysis_by_id(
    import_id: str,
    db: Session = Depends(get_db),
):
    """
    Get full analysis summary for a specific import ID.
    """
    summary = CsvAnalyticsService.get_summary(import_id=import_id, db=db)
    if not summary.get("found"):
        raise HTTPException(status_code=404, detail=f"Import ID '{import_id}' not found.")
    return summary


@router.get("/groups")
def get_csv_groups(
    import_id: Optional[str] = Query(None),
    group_by: str = Query("user", description="user | ip | event_type | status | country | date | hour | severity"),
    db: Session = Depends(get_db),
):
    """
    Group imported records by chosen dimension (user, IP, event type, status, country, date, hour, severity).
    """
    groups = CsvAnalyticsService.get_groups(
        import_id=import_id,
        group_by=group_by,
        db=db,
    )
    return {
        "group_by": group_by,
        "count": len(groups),
        "groups": groups,
    }


@router.get("/alerts")
def get_csv_alerts(
    import_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None, description="ALL, CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="ALL, OPEN, INVESTIGATING, RESOLVED"),
    source: Optional[str] = Query(None, description="all | rule | ml | both"),
    db: Session = Depends(get_db),
):
    """
    List security alerts detected in the CSV file with optional filters.
    """
    alerts = CsvAnalyticsService.get_alerts(
        import_id=import_id,
        severity=severity,
        status=status,
        source=source,
        db=db,
    )
    return {
        "count": len(alerts),
        "alerts": alerts,
    }


@router.get("/records")
def get_csv_records(
    import_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="ALL, SUCCESS, FAILURE"),
    db: Session = Depends(get_db),
):
    """
    Retrieve paginated normalized records with search and status filtering.
    """
    return CsvAnalyticsService.get_records(
        import_id=import_id,
        limit=limit,
        offset=offset,
        search=search,
        status=status,
        db=db,
    )


@router.patch("/alerts/{alert_id}")
def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the triage status of an alert (OPEN, INVESTIGATING, RESOLVED).
    """
    try:
        updated = CsvAnalyticsService.update_alert_status(
            alert_id=alert_id,
            new_status=payload.status,
            db=db,
        )
        return {"success": True, "alert": updated}
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{import_id}")
def export_csv_data(
    import_id: str,
    type: str = Query("alerts", description="alerts | groups | risk"),
    format: str = Query("csv", description="csv | json"),
    db: Session = Depends(get_db),
):
    """
    Export alerts, groups summary, or risk summary as CSV or JSON.
    Protected against CSV formula injection.
    """
    content, media_type, filename = CsvAnalyticsService.generate_export(
        import_id=import_id,
        export_type=type.lower(),
        export_format=format.lower(),
        db=db,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
