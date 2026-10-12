"""
CSV batch importer with validation, quarantine, and duplicate detection.
Provides deterministic import: same CSV → same events always.
"""

import csv
import hashlib
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CSVImportResult:
    """Result of CSV import operation with detailed reporting."""
    
    def __init__(self):
        self.imported_rows: int = 0
        self.quarantined_rows: List[Dict] = []
        self.merged_duplicates: int = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "imported_rows": self.imported_rows,
            "quarantined_rows": len(self.quarantined_rows),
            "quarantine_details": self.quarantined_rows,
            "merged_duplicates": self.merged_duplicates,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": len(self.errors) == 0
        }
    
    def __repr__(self) -> str:
        return (
            f"CSVImportResult(imported={self.imported_rows}, "
            f"quarantined={len(self.quarantined_rows)}, "
            f"duplicates={self.merged_duplicates}, "
            f"errors={len(self.errors)})"
        )


class CSVImporter:
    """
    CSV importer with comprehensive validation.
    
    Features:
    - Multiple timestamp format support
    - Duplicate detection via content hash
    - Detailed quarantine reporting
    - Deterministic processing
    """
    
    # Supported timestamp formats (tried in order)
    TIMESTAMP_FORMATS = [
        "%Y-%m-%d %H:%M:%S",           # 2024-01-15 10:30:45
        "%Y-%m-%dT%H:%M:%S",           # 2024-01-15T10:30:45
        "%Y-%m-%dT%H:%M:%SZ",          # 2024-01-15T10:30:45Z (ISO with Z)
        "%Y/%m/%d %H:%M:%S",           # 2024/01/15 10:30:45
        "%m/%d/%Y %H:%M:%S",           # 01/15/2024 10:30:45
        "%Y-%m-%d %H:%M:%S.%f",        # 2024-01-15 10:30:45.123456
        "%d-%m-%Y %H:%M:%S",           # 15-01-2024 10:30:45
    ]
    
    # Required fields in CSV
    REQUIRED_FIELDS = ['username', 'computer', 'source_ip', 'timestamp', 'event_type']
    
    # Optional fields (will map if present)
    OPTIONAL_FIELDS = ['logon_type', 'status', 'source_host', 'raw_record_id']
    
    @staticmethod
    def parse_timestamp(ts_str: str) -> Optional[datetime]:
        """
        Try parsing timestamp with multiple formats.
        
        Args:
            ts_str: Timestamp string
        
        Returns:
            Parsed datetime (UTC, timezone-aware) or None if all formats fail
        """
        if not ts_str or not ts_str.strip():
            return None
        
        ts_str = ts_str.strip()
        from datetime import timezone
        
        for fmt in CSVImporter.TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(ts_str, fmt)
                # Make timezone-aware (UTC)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def compute_event_hash(row: Dict) -> str:
        """
        Compute deterministic hash for duplicate detection.
        Hash is based on core event identity fields.
        
        Args:
            row: Event dict
        
        Returns:
            16-char hex hash (first 16 chars of SHA256)
        """
        # Key fields uniquely identify an event
        key_fields = f"{row.get('username', '')}:{row.get('computer', '')}:{row.get('source_ip', '')}:{row.get('timestamp', '')}:{row.get('event_type', '')}"
        hash_result = hashlib.sha256(key_fields.encode()).hexdigest()
        return hash_result[:16]
    
    @staticmethod
    def normalize_row(row: Dict) -> Dict:
        """
        Normalize CSV row for database storage.
        Maps CSV field names to database field names.
        
        Args:
            row: Raw CSV row dict
        
        Returns:
            Normalized event dict
        """
        normalized = {
            'username': (row.get('username') or '').strip(),
            'target_computer': (row.get('computer') or '').strip(),
            'source_ip': (row.get('source_ip') or '').strip(),
            'timestamp': row.get('timestamp'),  # Already parsed
            'event_id': 4625 if row.get('event_type', '').upper() == 'FAILURE' else 4624,  # 4625=failure, 4624=success
            'status': row.get('status', row.get('event_type', '').upper()),
            'logon_type': int(row.get('logon_type', 3)) if row.get('logon_type') else 3,
            'source_host': (row.get('source_host') or '').strip(),
            'raw_record_id': int(row.get('raw_record_id', 0)) if row.get('raw_record_id') else None,
        }
        return normalized
    
    @staticmethod
    def import_csv(
        filepath: str,
        existing_hashes: Optional[set] = None
    ) -> Tuple[List[Dict], CSVImportResult]:
        """
        Import and validate CSV file.
        
        Process:
        1. Check file exists and is readable
        2. Verify headers
        3. For each row:
           - Parse and validate timestamp
           - Check required fields
           - Detect duplicates
           - Normalize field names
           - Quarantine invalid rows with reason
        4. Return valid events and detailed result
        
        Args:
            filepath: Path to CSV file
            existing_hashes: Set of event hashes already in database
                           (for duplicate detection)
        
        Returns:
            Tuple of (valid_events, result)
            - valid_events: List of normalized event dicts ready for DB
            - result: CSVImportResult with import stats and quarantine details
        """
        if existing_hashes is None:
            existing_hashes = set()
        
        result = CSVImportResult()
        valid_events = []
        seen_hashes = set(existing_hashes)
        
        # Check file exists
        path = Path(filepath)
        if not path.exists():
            result.errors.append(f"File not found: {filepath}")
            return valid_events, result
        
        if not path.is_file():
            result.errors.append(f"Not a file: {filepath}")
            return valid_events, result
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                
                # Check headers exist
                if reader.fieldnames is None:
                    result.errors.append("CSV file is empty or unreadable")
                    return valid_events, result
                
                # Check for required fields
                missing_fields = [
                    f for f in CSVImporter.REQUIRED_FIELDS 
                    if f not in reader.fieldnames
                ]
                if missing_fields:
                    result.errors.append(
                        f"Missing required fields: {', '.join(missing_fields)}"
                    )
                    logger.error(f"CSV header validation failed: {result.errors[-1]}")
                    return valid_events, result
                
                # Process each row
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    quarantine_reason = None
                    
                    # === Validation Phase ===
                    
                    # 1. Validate timestamp format
                    ts_str = row.get('timestamp', '').strip()
                    if not ts_str:
                        quarantine_reason = "Missing or empty timestamp"
                    else:
                        ts = CSVImporter.parse_timestamp(ts_str)
                        if ts is None:
                            quarantine_reason = f"Invalid timestamp format: '{ts_str}' (expected formats: YYYY-MM-DD HH:MM:SS or ISO 8601)"
                    
                    # 2. Validate required text fields
                    if not quarantine_reason:
                        for field in ['username', 'computer', 'source_ip', 'event_type']:
                            if not row.get(field) or not row.get(field).strip():
                                quarantine_reason = f"Missing or empty required field: {field}"
                                break
                    
                    # 3. Validate event_type is FAILURE or SUCCESS
                    if not quarantine_reason:
                        event_type = row.get('event_type', '').upper()
                        if event_type not in ('FAILURE', 'SUCCESS', 'FAILED'):
                            quarantine_reason = f"Invalid event_type '{event_type}'. Must be FAILURE or SUCCESS"
                    
                    # === Duplicate Detection ===
                    if not quarantine_reason:
                        # Compute hash before timestamp parsing (use original string)
                        temp_row = dict(row)
                        temp_row['timestamp'] = ts_str  # Use string for hash
                        event_hash = CSVImporter.compute_event_hash(temp_row)
                        
                        if event_hash in seen_hashes:
                            result.merged_duplicates += 1
                            continue
                        
                        row['event_hash'] = event_hash
                        seen_hashes.add(event_hash)
                    
                    # === Quarantine or Accept ===
                    if quarantine_reason:
                        result.quarantined_rows.append({
                            "row_number": row_num,
                            "reason": quarantine_reason,
                            "data": dict(row)  # Copy for safety
                        })
                    else:
                        # Parse timestamp now that we know it's valid
                        ts = CSVImporter.parse_timestamp(row.get('timestamp', ''))
                        row['timestamp'] = ts
                        
                        # Normalize field names for database
                        normalized = CSVImporter.normalize_row(row)
                        valid_events.append(normalized)
                        result.imported_rows += 1
        
        except UnicodeDecodeError as e:
            result.errors.append(f"File encoding error: {str(e)}. Try UTF-8 encoding.")
            logger.error(f"CSV encoding error: {e}")
        
        except Exception as e:
            result.errors.append(f"CSV read error: {type(e).__name__}: {str(e)}")
            logger.error(f"CSV import error: {e}", exc_info=True)
        
        # Log import summary
        logger.info(
            f"CSV import complete: imported={result.imported_rows}, "
            f"quarantined={len(result.quarantined_rows)}, "
            f"duplicates={result.merged_duplicates}, errors={len(result.errors)}"
        )
        
        return valid_events, result
