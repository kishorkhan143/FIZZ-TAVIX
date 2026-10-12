"""
CSV Analytics Service
=====================
Orchestrates CSV parsing, column detection, data normalization,
risk scoring, security alert detection, database persistence,
grouping dimensions, and export generation with CSV formula injection protection.
"""

import csv
import io
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from csv_analytics.models import CsvImport, CsvAlert, CsvRecord
from csv_analytics.column_detector import ColumnDetector
from csv_analytics.normalizer import DataNormalizer
from csv_analytics.detector import SecurityDetector
from csv_analytics.scoring_bridge import ScoringBridge
from ws_manager import manager

logger = logging.getLogger("authsentinel.csv_analytics")

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB safeguard


class CsvAnalyticsService:
    """Core service for CSV file ingestion, analysis, querying, and exporting."""

    @staticmethod
    def _sanitize_for_csv(val: Any) -> str:
        """
        Protects against CSV Formula Injection (DDE injection).
        Prepends a single quote if string begins with =, +, -, @, or tab/CR.
        """
        if val is None:
            return ""
        s = str(val)
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{s}"
        return s

    @classmethod
    def process_csv_upload(
        cls,
        file_bytes: bytes,
        filename: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Parses, validates, normalizes, scores, and stores a CSV upload.
        """
        # 1. Validation checks
        if not filename.lower().endswith(".csv"):
            raise ValueError("Only .csv files are supported. Please upload a valid CSV file.")

        file_size = len(file_bytes)
        if file_size == 0:
            raise ValueError("The uploaded CSV file is empty (0 bytes).")

        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum limit of 50MB (received {file_size / (1024 * 1024):.1f}MB).")

        # 2. Encoding detection and safe decoding
        text_content = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                text_content = file_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            raise ValueError("Failed to decode CSV file. Please ensure it is saved in UTF-8 or standard ASCII format.")

        # 3. CSV parsing with DictReader
        try:
            f_stream = io.StringIO(text_content)
            reader = csv.DictReader(f_stream)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV format: {str(e)}")

        raw_headers = reader.fieldnames
        if not raw_headers:
            raise ValueError("CSV file contains no headers or is improperly formatted.")

        # Check for duplicate headers
        seen_h = set()
        for h in raw_headers:
            h_clean = (h or "").strip()
            if not h_clean:
                continue
            if h_clean in seen_h:
                logger.warning(f"Duplicate header detected: '{h_clean}'. Duplicate columns will be indexed.")
            seen_h.add(h_clean)

        # 4. Flexible Column Detection
        detected_mapping, unmapped_headers = ColumnDetector.detect_columns(raw_headers)

        rows = list(reader)

        # Content-based column detection fallback if timestamp, ip, or user are not mapped
        if rows:
            sample_row = rows[0]
            if "timestamp" not in detected_mapping:
                for col in list(unmapped_headers):
                    val = sample_row.get(col)
                    if val and DataNormalizer.parse_timestamp(val) is not None:
                        detected_mapping["timestamp"] = col
                        unmapped_headers.remove(col)
                        break

            if "ip" not in detected_mapping:
                for col in list(unmapped_headers):
                    val = sample_row.get(col)
                    if val and DataNormalizer.normalize_ip(val) is not None:
                        detected_mapping["ip"] = col
                        unmapped_headers.remove(col)
                        break

        # Check minimum essential requirements
        if not any(k in detected_mapping for k in ("timestamp", "user", "ip")):
            if raw_headers:
                first_col = raw_headers[0]
                detected_mapping["user"] = first_col
                if first_col in unmapped_headers:
                    unmapped_headers.remove(first_col)

        # 5. Normalization & Validation Phase
        import_id = str(uuid.uuid4())
        valid_records: List[Dict[str, Any]] = []
        quarantined_rows: List[Dict[str, Any]] = []

        for row_idx, row in enumerate(rows, start=2):  # row 1 is header
            norm_rec, quaran = DataNormalizer.normalize_record(
                row_idx=row_idx,
                raw_row=row,
                mapping=detected_mapping,
                unmapped_keys=unmapped_headers,
            )
            if quaran:
                quarantined_rows.append(quaran)
            elif norm_rec:
                valid_records.append(norm_rec)

        total_records_count = len(valid_records) + len(quarantined_rows)
        if total_records_count == 0:
            raise ValueError("CSV contains headers but no data rows.")

        # Graceful recovery: If all rows failed solely due to timestamp issues, recover them with sequential timestamps
        if not valid_records and quarantined_rows:
            all_ts_reasons = all("timestamp" in q.get("reason", "").lower() for q in quarantined_rows)
            if all_ts_reasons:
                logger.warning("Recovering records with unparseable timestamps using fallback sequence.")
                valid_records.clear()
                recovered_mapping = {k: v for k, v in detected_mapping.items() if k != "timestamp"}
                for q in quarantined_rows:
                    recovered_rec, _ = DataNormalizer.normalize_record(
                        row_idx=q["row_number"],
                        raw_row=q.get("raw_data", {}),
                        mapping=recovered_mapping,
                        unmapped_keys=unmapped_headers,
                    )
                    if recovered_rec:
                        valid_records.append(recovered_rec)
                quarantined_rows.clear()

        if not valid_records:
            sample_errors = [q["reason"] for q in quarantined_rows[:3]]
            raise ValueError(
                f"No valid records could be parsed out of {total_records_count} rows. "
                f"Sample errors: {'; '.join(sample_errors)}"
            )

        # 6. Entity Risk Scoring Bridge
        scoring_bridge = ScoringBridge()
        entity_risk_map = scoring_bridge.compute_records_risk(valid_records)

        # Assign per-record risk score
        for rec in valid_records:
            u_key = f"user:{rec['user']}"
            ip_key = f"ip:{rec['ip']}"
            u_risk = entity_risk_map.get(u_key, {}).get("score", 0.0)
            ip_risk = entity_risk_map.get(ip_key, {}).get("score", 0.0)
            rec["risk_score"] = max(u_risk, ip_risk)
            rec["risk_level"] = scoring_bridge.get_risk_band(rec["risk_score"])

        # 7. Security Alert Detection (Rules 1 to 10)
        alerts_list = SecurityDetector.detect_alerts(import_id=import_id, records=valid_records)

        # 7b. ML Predictor Integration (safe — never crashes the upload)
        try:
            from ml.predictor import predict as ml_predict
            ml_findings = ml_predict(valid_records)
            ml_findings = [f for f in ml_findings if f.get("prediction") != "NORMAL"]
        except Exception as ml_err:
            logger.warning(f"ML predictor skipped: {ml_err}")
            ml_findings = []

        if ml_findings:
            def _overlapping(ids_a, ids_b):
                return bool(set(ids_a) & set(ids_b))

            rule_lookup = {}  # (user, ip) -> index in alerts_list
            for idx, a in enumerate(alerts_list):
                rule_lookup[(a["user"], a["ip"])] = idx

            for finding in ml_findings:
                f_user = finding.get("user", "")
                f_ip = finding.get("ip", "")
                f_ids = finding.get("event_ids", [])
                match_idx = rule_lookup.get((f_user, f_ip))
                if match_idx is not None and _overlapping(
                        alerts_list[match_idx].get("related_events", []), f_ids):
                    a = alerts_list[match_idx]
                    a["source"] = "RULE+ML"
                    a["ml_prediction"] = finding["prediction"]
                    a["ml_risk"] = finding["ml_risk"]
                    a["ml_confidence"] = finding["confidence"]
                    a["ml_review_label"] = finding["review_label"]
                    a["suggested_step"] = finding["suggested_human_step"]
                    a["class_probabilities"] = finding.get("class_probabilities", {})
                    a["evidence"] = finding.get("evidence", {})
                    a["anomaly_score"] = finding.get("anomaly_score")
                else:
                    ml_alert = {
                        "id": str(uuid.uuid4())[:8],
                        "import_id": import_id,
                        "alert_type": finding["prediction"],
                        "severity": "HIGH" if (finding["ml_risk"] or 0) >= 70 else (
                                     "MEDIUM" if (finding["ml_risk"] or 0) >= 40 else "LOW"),
                        "risk_score": float(finding.get("ml_risk") or 0),
                        "user": f_user,
                        "ip": f_ip,
                        "country": None,
                        "message": finding.get("review_label", "Needs review"),
                        "first_seen": finding.get("first_seen"),
                        "last_seen": finding.get("last_seen"),
                        "event_count": len(f_ids),
                        "failed_count": finding.get("evidence", {}).get("failures", 0),
                        "time_window_seconds": int(
                            (finding["last_seen"] - finding["first_seen"]).total_seconds()
                            if finding.get("last_seen") and finding.get("first_seen") else 0),
                        "status": "OPEN",
                        "reasons": [finding.get("review_label", "Needs review")],
                        "related_events": f_ids,
                        "source": "ML",
                        "ml_prediction": finding["prediction"],
                        "ml_risk": finding["ml_risk"],
                        "ml_confidence": finding["confidence"],
                        "ml_review_label": finding["review_label"],
                        "suggested_step": finding["suggested_human_step"],
                        "class_probabilities": finding.get("class_probabilities", {}),
                        "evidence": finding.get("evidence", {}),
                        "anomaly_score": finding.get("anomaly_score"),
                        "created_at": datetime.now(timezone.utc),
                    }
                    alerts_list.append(ml_alert)

        # Recompute counts to include ML-only alerts
        high_risk_alerts = [a for a in alerts_list if a["severity"] in ("CRITICAL", "HIGH")]

        # 8. High-Level Aggregation & Analysis Summary
        unique_users = sorted(list({r["user"] for r in valid_records if r["user"]}))
        unique_ips = sorted(list({r["ip"] for r in valid_records if r["ip"] and r["ip"] != "0.0.0.0"}))
        event_types = sorted(list({r["event_type"] for r in valid_records if r["event_type"]}))
        countries = sorted(list({r["country"] for r in valid_records if r["country"]}))

        success_count = sum(1 for r in valid_records if r["status"] == "SUCCESS")
        failure_count = sum(1 for r in valid_records if r["status"] == "FAILURE")

        # Top risky users and IPs
        top_users = sorted(
            [v for k, v in entity_risk_map.items() if v["type"] == "USER"],
            key=lambda x: x["score"],
            reverse=True,
        )[:10]

        top_ips = sorted(
            [v for k, v in entity_risk_map.items() if v["type"] == "IP"],
            key=lambda x: x["score"],
            reverse=True,
        )[:10]

        # Timeline aggregation (by hour or 10-minute bins)
        sorted_records = sorted(valid_records, key=lambda r: r["timestamp"])
        timeline_buckets = defaultdict(lambda: {"timestamp": "", "events": 0, "failures": 0, "success": 0})
        for r in sorted_records:
            # Format bucket
            t_str = r["timestamp"].strftime("%Y-%m-%d %H:%M")
            timeline_buckets[t_str]["timestamp"] = t_str
            timeline_buckets[t_str]["events"] += 1
            if r["status"] == "FAILURE":
                timeline_buckets[t_str]["failures"] += 1
            else:
                timeline_buckets[t_str]["success"] += 1

        timeline_data = list(timeline_buckets.values())[:50]

        analysis_summary = {
            "users_count": len(unique_users),
            "unique_ips_count": len(unique_ips),
            "event_types_count": len(event_types),
            "countries_count": len(countries),
            "success_count": success_count,
            "failure_count": failure_count,
            "timeline": timeline_data,
            "top_users": top_users,
            "top_ips": top_ips,
            "event_type_distribution": {
                et: sum(1 for r in valid_records if r["event_type"] == et) for et in event_types
            },
            "severity_distribution": {
                "CRITICAL": sum(1 for a in alerts_list if a["severity"] == "CRITICAL"),
                "HIGH": sum(1 for a in alerts_list if a["severity"] == "HIGH"),
                "MEDIUM": sum(1 for a in alerts_list if a["severity"] == "MEDIUM"),
                "LOW": sum(1 for a in alerts_list if a["severity"] == "LOW"),
            },
            "risk_band_distribution": {
                "CRITICAL": sum(1 for r in valid_records if r["risk_level"] == "CRITICAL"),
                "HIGH": sum(1 for r in valid_records if r["risk_level"] == "HIGH"),
                "MEDIUM": sum(1 for r in valid_records if r["risk_level"] == "MEDIUM"),
                "NORMAL": sum(1 for r in valid_records if r["risk_level"] == "NORMAL"),
            },
            "country_distribution": {
                c: sum(1 for r in valid_records if r["country"] == c) for c in countries
            } if countries else {},
        }

        # 9. Database Persistence
        csv_import_obj = CsvImport(
            id=import_id,
            filename=filename,
            file_size_bytes=file_size,
            uploaded_at=datetime.now(timezone.utc),
            total_records=total_records_count,
            valid_records=len(valid_records),
            invalid_records=len(quarantined_rows),
            groups_count=len(unique_users),  # default groups count
            alerts_count=len(alerts_list),
            high_risk_count=len(high_risk_alerts),
            detected_columns=json.dumps(detected_mapping),
            quarantine_summary=json.dumps(quarantined_rows[:100]),  # store up to 100 samples
            analysis_summary=json.dumps(analysis_summary),
            status="COMPLETED",
        )
        db.add(csv_import_obj)

        # Bulk save records
        db_records = [
            CsvRecord(
                import_id=import_id,
                row_number=r["row_number"],
                timestamp=r["timestamp"],
                user=r["user"],
                ip=r["ip"],
                target_computer=r.get("target_computer"),
                event_type=r["event_type"],
                status=r["status"],
                country=r.get("country"),
                severity=r.get("severity"),
                risk_score=r["risk_score"],
                risk_level=r["risk_level"],
                extra_fields=json.dumps(r.get("extra_fields", {})),
            )
            for r in valid_records
        ]
        db.bulk_save_objects(db_records)

        # Bulk save alerts
        db_alerts = [
            CsvAlert(
                id=f"{import_id[:8]}-{a['id']}",
                import_id=import_id,
                alert_type=a["alert_type"],
                severity=a["severity"],
                risk_score=a["risk_score"],
                user=a["user"],
                ip=a["ip"],
                country=a.get("country"),
                message=a["message"],
                first_seen=a["first_seen"],
                last_seen=a["last_seen"],
                event_count=a["event_count"],
                failed_count=a["failed_count"],
                time_window_seconds=a["time_window_seconds"],
                status=a["status"],
                reasons=json.dumps(a["reasons"]),
                related_events=json.dumps(a.get("related_events", [])),
                source=a.get("source", "RULE"),
                ml_prediction=a.get("ml_prediction"),
                ml_risk=a.get("ml_risk"),
                ml_confidence=a.get("ml_confidence"),
                ml_review_label=a.get("ml_review_label"),
                suggested_step=a.get("suggested_step"),
                class_probabilities=json.dumps(a["class_probabilities"])
                    if a.get("class_probabilities") else None,
                evidence=json.dumps(a["evidence"])
                    if a.get("evidence") else None,
                anomaly_score=a.get("anomaly_score"),
                created_at=a["created_at"],
            )
            for a in alerts_list
        ]
        db.bulk_save_objects(db_alerts)

        db.commit()

        # 10. WebSocket Real-time Broadcast
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    manager.broadcast({
                        "type": "CSV_IMPORT_COMPLETED",
                        "import_id": import_id,
                        "filename": filename,
                        "total_records": total_records_count,
                        "valid_records": len(valid_records),
                        "alerts_count": len(alerts_list),
                        "high_risk": len(high_risk_alerts),
                    })
                )
                for ha in high_risk_alerts:
                    loop.create_task(
                        manager.broadcast({
                            "type": "NEW_ALERT",
                            "alert": {
                                "id": f"{import_id[:8]}-{ha['id']}",
                                "alert_type": ha["alert_type"],
                                "username": ha["user"],
                                "source_ip": ha["ip"],
                                "risk_score": ha["risk_score"],
                                "risk_level": ha["severity"],
                                "failure_count": ha["failed_count"],
                                "time_window_seconds": ha["time_window_seconds"],
                                "reason": "; ".join(ha["reasons"]),
                                "triggered_at": ha["created_at"].isoformat(),
                            }
                        })
                    )
            except RuntimeError:
                pass
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast skipped: {ws_err}")

        # Return structured JSON response matching specification
        return {
            "success": True,
            "import_id": import_id,
            "filename": filename,
            "total_records": total_records_count,
            "valid_records": len(valid_records),
            "invalid_records": len(quarantined_rows),
            "groups": len(unique_users),
            "alerts": len(alerts_list),
            "high_risk": len(high_risk_alerts),
            "detected_columns": detected_mapping,
            "unmapped_columns": unmapped_headers,
            "analysis": {
                "users": len(unique_users),
                "unique_ips": len(unique_ips),
                "event_types": len(event_types),
                "countries": len(countries),
                "success_events": success_count,
                "failed_events": failure_count,
            },
        }

    @classmethod
    def get_summary(cls, import_id: Optional[str], db: Session) -> Dict[str, Any]:
        """Fetch summary and analytics charts data for an import (or latest if omitted)."""
        stmt = select(CsvImport).order_by(desc(CsvImport.uploaded_at))
        if import_id:
            stmt = stmt.where(CsvImport.id == import_id)
        csv_import = db.execute(stmt).scalars().first()

        if not csv_import:
            return {"found": False, "message": "No CSV imports found."}

        data = csv_import.to_dict()
        data["found"] = True
        return data

    @classmethod
    def get_groups(
        cls,
        import_id: Optional[str],
        group_by: str,
        db: Session,
    ) -> List[Dict[str, Any]]:
        """
        Groups records by: user, ip, event_type, status, country, date, hour, severity.
        """
        # Resolve target import
        if not import_id:
            latest = db.execute(select(CsvImport.id).order_by(desc(CsvImport.uploaded_at))).scalars().first()
            if not latest:
                return []
            import_id = latest

        records = db.execute(
            select(CsvRecord).where(CsvRecord.import_id == import_id)
        ).scalars().all()

        if not records:
            return []

        group_map = defaultdict(list)
        norm_group_by = (group_by or "user").lower().strip()

        for r in records:
            if norm_group_by in ("user", "username"):
                key = r.user or "Unknown"
            elif norm_group_by in ("ip", "ip_address"):
                key = r.ip or "0.0.0.0"
            elif norm_group_by in ("event_type", "event"):
                key = r.event_type or "Unknown"
            elif norm_group_by == "status":
                key = r.status or "Unknown"
            elif norm_group_by == "country":
                key = r.country or "Unspecified"
            elif norm_group_by == "date":
                key = r.timestamp.strftime("%Y-%m-%d") if r.timestamp else "Unknown"
            elif norm_group_by == "hour":
                key = r.timestamp.strftime("%Y-%m-%d %H:00") if r.timestamp else "Unknown"
            elif norm_group_by == "severity":
                key = r.severity or r.risk_level or "NORMAL"
            else:
                key = r.user or "Unknown"

            group_map[key].append(r)

        result = []
        for key, rec_list in group_map.items():
            total = len(rec_list)
            failed = sum(1 for r in rec_list if r.status == "FAILURE")
            successful = total - failed
            unique_ips = len({r.ip for r in rec_list if r.ip and r.ip != "0.0.0.0"})
            unique_users = len({r.user for r in rec_list if r.user})
            unique_countries = len({r.country for r in rec_list if r.country})
            avg_risk = sum(r.risk_score for r in rec_list) / max(1, total)
            peak_risk = max((r.risk_score for r in rec_list), default=0.0)

            result.append({
                "group_name": key,
                "dimension": norm_group_by,
                "total_events": total,
                "failed_events": failed,
                "successful_events": successful,
                "unique_ips": unique_ips,
                "unique_users": unique_users,
                "countries_count": unique_countries,
                "risk_score": round(peak_risk, 1),
                "avg_risk_score": round(avg_risk, 1),
                "risk_level": ScoringBridge.get_risk_band(peak_risk),
            })

        # Sort by peak risk score descending, then by total events
        return sorted(result, key=lambda g: (g["risk_score"], g["total_events"]), reverse=True)

    @classmethod
    def get_alerts(
        cls,
        import_id: Optional[str],
        severity: Optional[str],
        status: Optional[str],
        db: Session,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch alerts with optional severity, status, and source filters."""
        stmt = select(CsvAlert)
        if import_id:
            stmt = stmt.where(CsvAlert.import_id == import_id)
        else:
            latest = db.execute(select(CsvImport.id).order_by(desc(CsvImport.uploaded_at))).scalars().first()
            if latest:
                stmt = stmt.where(CsvAlert.import_id == latest)
            else:
                return []

        if severity and severity.upper() != "ALL":
            stmt = stmt.where(CsvAlert.severity == severity.upper())

        if status and status.upper() != "ALL":
            stmt = stmt.where(CsvAlert.status == status.upper())

        if source and source.lower() not in ("all", ""):
            if source.lower() == "rule":
                stmt = stmt.where(CsvAlert.source == "RULE")
            elif source.lower() == "ml":
                stmt = stmt.where(CsvAlert.source.in_(["ML", "RULE+ML"]))
            elif source.lower() == "both":
                stmt = stmt.where(CsvAlert.source == "RULE+ML")

        stmt = stmt.order_by(desc(CsvAlert.risk_score), desc(CsvAlert.created_at))
        alerts = db.execute(stmt).scalars().all()
        return [a.to_dict() for a in alerts]

    @classmethod
    def get_records(
        cls,
        import_id: Optional[str],
        limit: int,
        offset: int,
        search: Optional[str],
        status: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        """Fetch paginated records for an import with search and status filtering."""
        if not import_id:
            latest = db.execute(select(CsvImport.id).order_by(desc(CsvImport.uploaded_at))).scalars().first()
            if not latest:
                return {"total": 0, "records": []}
            import_id = latest

        stmt = select(CsvRecord).where(CsvRecord.import_id == import_id)

        if status and status.upper() != "ALL":
            stmt = stmt.where(CsvRecord.status == status.upper())

        if search:
            s_pat = f"%{search.strip()}%"
            stmt = stmt.where(
                (CsvRecord.user.ilike(s_pat)) |
                (CsvRecord.ip.ilike(s_pat)) |
                (CsvRecord.event_type.ilike(s_pat)) |
                (CsvRecord.country.ilike(s_pat))
            )

        # Count total matches
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = db.execute(count_stmt).scalar_one()

        records = db.execute(
            stmt.order_by(CsvRecord.row_number).limit(limit).offset(offset)
        ).scalars().all()

        return {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "records": [r.to_dict() for r in records],
        }

    @classmethod
    def update_alert_status(cls, alert_id: str, new_status: str, db: Session) -> Dict[str, Any]:
        """Updates alert status (e.g. OPEN -> INVESTIGATING -> RESOLVED)."""
        valid_statuses = ("OPEN", "INVESTIGATING", "RESOLVED")
        new_status = new_status.upper().strip()
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

        alert = db.execute(
            select(CsvAlert).where(CsvAlert.id == alert_id)
        ).scalar_one_or_none()

        if not alert:
            raise ValueError(f"Alert with ID '{alert_id}' not found.")

        alert.status = new_status
        db.commit()
        db.refresh(alert)
        return alert.to_dict()

    @classmethod
    def generate_export(
        cls,
        import_id: str,
        export_type: str,
        export_format: str,
        db: Session,
    ) -> Tuple[str, str, str]:
        """
        Generates CSV or JSON export data with formula injection mitigation.
        Returns: (content_string, media_type, filename)
        """
        # Fetch relevant items
        if export_type == "alerts":
            alerts = cls.get_alerts(import_id=import_id, severity=None, status=None, db=db)
            if export_format == "json":
                return json.dumps(alerts, indent=2), "application/json", f"alerts_export_{import_id[:8]}.json"

            # CSV Format
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Alert ID", "Type", "Severity", "Risk Score", "User", "IP", "Events", "Failures", "Status", "Reasons"])
            for a in alerts:
                writer.writerow([
                    cls._sanitize_for_csv(a["alert_id"]),
                    cls._sanitize_for_csv(a["type"]),
                    cls._sanitize_for_csv(a["severity"]),
                    cls._sanitize_for_csv(a["risk_score"]),
                    cls._sanitize_for_csv(a["user"]),
                    cls._sanitize_for_csv(a["ip"]),
                    cls._sanitize_for_csv(a["event_count"]),
                    cls._sanitize_for_csv(a["failed_count"]),
                    cls._sanitize_for_csv(a["status"]),
                    cls._sanitize_for_csv("; ".join(a["reasons"])),
                ])
            return output.getvalue(), "text/csv", f"alerts_export_{import_id[:8]}.csv"

        elif export_type == "groups":
            groups = cls.get_groups(import_id=import_id, group_by="user", db=db)
            if export_format == "json":
                return json.dumps(groups, indent=2), "application/json", f"groups_summary_{import_id[:8]}.json"

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Group", "Dimension", "Total Events", "Failed Events", "Successful Events", "Unique IPs", "Risk Score", "Risk Level"])
            for g in groups:
                writer.writerow([
                    cls._sanitize_for_csv(g["group_name"]),
                    cls._sanitize_for_csv(g["dimension"]),
                    cls._sanitize_for_csv(g["total_events"]),
                    cls._sanitize_for_csv(g["failed_events"]),
                    cls._sanitize_for_csv(g["successful_events"]),
                    cls._sanitize_for_csv(g["unique_ips"]),
                    cls._sanitize_for_csv(g["risk_score"]),
                    cls._sanitize_for_csv(g["risk_level"]),
                ])
            return output.getvalue(), "text/csv", f"groups_summary_{import_id[:8]}.csv"

        else:  # risk summary
            summary = cls.get_summary(import_id=import_id, db=db)
            top_users = summary.get("analysis_summary", {}).get("top_users", [])
            if export_format == "json":
                return json.dumps(top_users, indent=2), "application/json", f"risk_summary_{import_id[:8]}.json"

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Entity", "Type", "Risk Score", "Band", "Events", "Failures", "Contributing Reasons"])
            for u in top_users:
                reasons_str = "; ".join([f"+{r['points']} {r['label']}" for r in u.get("reasons", [])])
                writer.writerow([
                    cls._sanitize_for_csv(u["entity"]),
                    cls._sanitize_for_csv(u["type"]),
                    cls._sanitize_for_csv(u["score"]),
                    cls._sanitize_for_csv(u["band"]),
                    cls._sanitize_for_csv(u["events_count"]),
                    cls._sanitize_for_csv(u["failures_count"]),
                    cls._sanitize_for_csv(reasons_str),
                ])
            return output.getvalue(), "text/csv", f"risk_summary_{import_id[:8]}.csv"
