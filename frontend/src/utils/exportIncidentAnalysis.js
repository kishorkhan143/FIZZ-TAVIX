/**
 * AuthSentinel — Incident Analysis Exporter
 * Generates and downloads real CSV, JSON, and PDF analysis reports
 * from live and historical incident records.
 */

import { fmtDateTime, fmtTime, formatDisplayDate, getItemDateString } from '../dateFilterUtils.js';

/**
 * Normalizes raw alert types to readable labels matching the UI
 */
export function getIncidentTypeLabel(type) {
  if (!type) return 'SECURITY ALERT';
  if (type === 'REPEATED_FAILURE') return 'BRUTE FORCE';
  if (type === 'SUCCESS_AFTER_FAILURES') return 'ANOMALY';
  return type.replace(/_/g, ' ');
}

/**
 * Calculates dynamic statistics and summary from actual alert records
 */
export function computeIncidentSummary(alerts = []) {
  const totalIncidents = alerts.length;
  let totalOccurrences = 0;
  const byType = {};
  const byRisk = { HIGH: 0, MEDIUM: 0, LOW: 0 };

  const validDates = [];

  alerts.forEach((al) => {
    const typeLabel = getIncidentTypeLabel(al.alert_type);
    const count = Number(al.failure_count) > 0 ? Number(al.failure_count) : 1;
    totalOccurrences += count;

    if (!byType[typeLabel]) {
      byType[typeLabel] = {
        incident_count: 0,
        total_occurrences: 0,
      };
    }
    byType[typeLabel].incident_count += 1;
    byType[typeLabel].total_occurrences += count;

    const risk = (al.risk_level || 'HIGH').toUpperCase();
    byRisk[risk] = (byRisk[risk] || 0) + 1;

    if (al.triggered_at) {
      const dt = new Date(al.triggered_at);
      if (!isNaN(dt.getTime())) {
        validDates.push(dt);
      }
    }
  });

  validDates.sort((a, b) => a.getTime() - b.getTime());

  let timeRangeStart = '—';
  let timeRangeEnd = '—';
  let timeRangeDisplay = 'All recorded timestamps';

  if (validDates.length > 0) {
    timeRangeStart = validDates[0].toISOString();
    timeRangeEnd = validDates[validDates.length - 1].toISOString();
    const startFormatted = fmtDateTime(timeRangeStart);
    const endFormatted = fmtDateTime(timeRangeEnd);
    timeRangeDisplay = `${startFormatted} to ${endFormatted}`;
  }

  const now = new Date();
  const generatedAtIso = now.toISOString();
  const generatedAtDisplay = fmtDateTime(generatedAtIso);

  return {
    total_incidents: totalIncidents,
    total_occurrences: totalOccurrences,
    by_incident_type: byType,
    by_risk_level: byRisk,
    time_range: {
      start: timeRangeStart,
      end: timeRangeEnd,
      display: timeRangeDisplay,
    },
    generated_at_iso: generatedAtIso,
    generated_at_display: generatedAtDisplay,
  };
}

/**
 * Triggers a file download in the browser
 */
export function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, 200);
}

/**
 * CSV Exporter
 */
export function exportIncidentAnalysisCsv(alerts = []) {
  if (!alerts || alerts.length === 0) {
    throw new Error('No incident data available to export.');
  }

  const summary = computeIncidentSummary(alerts);
  const escapeCsv = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const lines = [];

  // Summary Metadata Header
  lines.push('# TAVIX GUARD - Security Incident Analysis Report');
  lines.push(`# Generated At: ${summary.generated_at_display} (${summary.generated_at_iso})`);
  lines.push(`# Time Range Covered: ${summary.time_range.display}`);
  lines.push(`# Total Incidents Detected: ${summary.total_incidents}`);
  lines.push(`# Total Occurrences / Attempts: ${summary.total_occurrences}`);
  lines.push('#');
  lines.push('# --- SUMMARY BY INCIDENT TYPE ---');
  lines.push('Incident Type,Incidents Count,Total Occurrences');

  Object.entries(summary.by_incident_type).forEach(([type, data]) => {
    lines.push(`${escapeCsv(type)},${data.incident_count},${data.total_occurrences}`);
  });

  lines.push('#');
  lines.push('# --- SUMMARY BY RISK LEVEL ---');
  lines.push('Risk Level,Incidents Count');
  Object.entries(summary.by_risk_level).forEach(([lvl, count]) => {
    lines.push(`${escapeCsv(lvl)},${count}`);
  });

  lines.push('#');
  lines.push('# --- DETAILED INCIDENT RECORDS ---');

  // Table Headers
  const headers = [
    'Incident ID',
    'Incident Type',
    'Raw Alert Type',
    'Username / Account',
    'Source IP',
    'Source Host',
    'Target Computer',
    'Risk Level',
    'Risk Score',
    'Occurrence Count',
    'Status',
    'Triggered At',
    'Analysis Summary',
  ];
  lines.push(headers.map(escapeCsv).join(','));

  // Table Rows
  alerts.forEach((al) => {
    const row = [
      al.id || '',
      getIncidentTypeLabel(al.alert_type),
      al.alert_type || '',
      al.username || 'UNKNOWN',
      al.source_ip || '—',
      al.source_host || '—',
      al.target_computer || '—',
      al.risk_level || 'HIGH',
      al.risk_score !== undefined ? al.risk_score : '',
      al.failure_count || 1,
      al.status || (al.resolved ? 'RESOLVED' : 'OPEN'),
      al.triggered_at ? fmtDateTime(al.triggered_at) : '—',
      al.reason || '',
    ];
    lines.push(row.map(escapeCsv).join(','));
  });

  const csvContent = '\uFEFF' + lines.join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  triggerDownload(blob, 'TAVIX_GUARD_Incident_Analysis.csv');
  return { success: true, count: alerts.length };
}

/**
 * JSON Exporter
 */
export function exportIncidentAnalysisJson(alerts = []) {
  if (!alerts || alerts.length === 0) {
    throw new Error('No incident data available to export.');
  }

  const summary = computeIncidentSummary(alerts);

  const report = {
    report_title: 'TAVIX GUARD Security Incident Analysis Report',
    system: 'TAVIX GUARD Monitoring & Threat Detection',
    generated_at: summary.generated_at_iso,
    generated_at_display: summary.generated_at_display,
    summary: {
      total_incidents: summary.total_incidents,
      total_occurrences: summary.total_occurrences,
      time_range: summary.time_range,
      by_incident_type: summary.by_incident_type,
      by_risk_level: summary.by_risk_level,
    },
    incidents: alerts.map((al) => ({
      id: al.id,
      incident_type: getIncidentTypeLabel(al.alert_type),
      raw_alert_type: al.alert_type,
      username: al.username || 'UNKNOWN',
      source_ip: al.source_ip || null,
      source_host: al.source_host || null,
      target_computer: al.target_computer || null,
      risk_level: al.risk_level || 'HIGH',
      risk_score: al.risk_score,
      occurrence_count: al.failure_count || 1,
      status: al.status || (al.resolved ? 'RESOLVED' : 'OPEN'),
      resolved: !!al.resolved,
      triggered_at: al.triggered_at,
      triggered_at_formatted: al.triggered_at ? fmtDateTime(al.triggered_at) : null,
      reason: al.reason || null,
    })),
  };

  const jsonStr = JSON.stringify(report, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
  triggerDownload(blob, 'TAVIX_GUARD_Incident_Analysis.json');
  return { success: true, count: alerts.length };
}

/**
 * Pure JavaScript PDF-1.4 Exporter
 */
export function exportIncidentAnalysisPdf(alerts = []) {
  if (!alerts || alerts.length === 0) {
    throw new Error('No incident data available to export.');
  }

  const summary = computeIncidentSummary(alerts);

  const pageWidth = 595.28;  // A4 standard points
  const pageHeight = 841.89;
  const margin = 36;
  const contentWidth = pageWidth - margin * 2;

  function escapePdf(str) {
    return (str || '')
      .toString()
      .replace(/\\/g, '\\\\')
      .replace(/\(/g, '\\(')
      .replace(/\)/g, '\\)');
  }

  const pages = [];
  let currentPage = [];
  let y = pageHeight - margin;

  function startPage() {
    currentPage = [];
    pages.push(currentPage);
    y = pageHeight - margin - 15;

    // Top primary accent bar
    currentPage.push(`0.00 0.40 1.00 rg ${margin} ${pageHeight - 20} ${contentWidth} 3.5 re f`);
  }

  startPage();

  // Document Header
  currentPage.push(`BT /F2 17 Tf 0.10 0.15 0.22 rg ${margin} ${y -= 15} Td (TAVIX GUARD - Security Incident Analysis) Tj ET`);
  currentPage.push(`BT /F1 9 Tf 0.40 0.45 0.52 rg ${margin} ${y -= 15} Td (Generated: ${escapePdf(summary.generated_at_display)}  |  Time Range: ${escapePdf(summary.time_range.display)}) Tj ET`);

  y -= 14;

  // Executive Summary Card
  const boxHeight = 58;
  currentPage.push(`0.96 0.97 0.99 rg ${margin} ${y - boxHeight} ${contentWidth} ${boxHeight} re f`);
  currentPage.push(`0.84 0.88 0.94 RG 0.75 w ${margin} ${y - boxHeight} ${contentWidth} ${boxHeight} re S`);

  currentPage.push(`BT /F2 9.5 Tf 0.12 0.22 0.38 rg ${margin + 12} ${y - 16} Td (INCIDENT ANALYSIS SUMMARY) Tj ET`);

  const typeSummaryText = Object.entries(summary.by_incident_type)
    .map(([t, d]) => `${t}: ${d.incident_count} (x${d.total_occurrences})`)
    .join('  |  ');

  currentPage.push(`BT /F1 8.5 Tf 0.20 0.25 0.32 rg ${margin + 12} ${y - 32} Td (Total Incidents: ${summary.total_incidents}    |    Total Occurrences: ${summary.total_occurrences}    |    High: ${summary.by_risk_level.HIGH || 0}   Med: ${summary.by_risk_level.MEDIUM || 0}   Low: ${summary.by_risk_level.LOW || 0}) Tj ET`);
  currentPage.push(`BT /F1 8 Tf 0.35 0.40 0.48 rg ${margin + 12} ${y - 48} Td (${escapePdf(typeSummaryText.slice(0, 110))}) Tj ET`);

  y -= (boxHeight + 20);

  // Table Columns Definition
  const cols = [
    { title: 'INCIDENT TYPE', x: margin, w: 125 },
    { title: 'ACCOUNT', x: margin + 125, w: 90 },
    { title: 'SOURCE IP', x: margin + 215, w: 95 },
    { title: 'COUNT', x: margin + 310, w: 45 },
    { title: 'RISK', x: margin + 355, w: 50 },
    { title: 'TRIGGERED AT', x: margin + 405, w: 118 },
  ];

  function drawTableHeader() {
    currentPage.push(`0.91 0.94 0.98 rg ${margin} ${y - 18} ${contentWidth} 20 re f`);
    currentPage.push(`0.78 0.83 0.90 RG 0.5 w ${margin} ${y - 18} ${contentWidth} 20 re S`);
    cols.forEach((c) => {
      currentPage.push(`BT /F2 8 Tf 0.18 0.26 0.38 rg ${c.x + 5} ${y - 13} Td (${escapePdf(c.title)}) Tj ET`);
    });
    y -= 22;
  }

  drawTableHeader();

  // Draw Incident Rows
  alerts.forEach((al, idx) => {
    if (y < 65) {
      startPage();
      drawTableHeader();
    }

    const typeLabel = getIncidentTypeLabel(al.alert_type);
    const userStr = al.username || 'UNKNOWN';
    const ipStr = al.source_ip || '—';
    const countStr = al.failure_count > 0 ? `x${al.failure_count}` : '1';
    const riskStr = (al.risk_level || 'HIGH').toUpperCase();
    const timeStr = al.triggered_at ? fmtDateTime(al.triggered_at) : '—';

    // Alternate row shading
    if (idx % 2 === 1) {
      currentPage.push(`0.97 0.98 0.99 rg ${margin} ${y - 16} ${contentWidth} 18 re f`);
    }
    currentPage.push(`0.88 0.90 0.93 RG 0.5 w ${margin} ${y - 16} ${contentWidth} 0.5 re S`);

    // Incident Type (in bold alert color)
    currentPage.push(`BT /F2 8 Tf 0.85 0.15 0.15 rg ${cols[0].x + 5} ${y - 12} Td (${escapePdf(typeLabel.slice(0, 22))}) Tj ET`);

    // Username
    currentPage.push(`BT /F1 8 Tf 0.00 0.38 0.80 rg ${cols[1].x + 5} ${y - 12} Td (${escapePdf(userStr.slice(0, 15))}) Tj ET`);

    // Source IP
    currentPage.push(`BT /F1 8 Tf 0.25 0.30 0.35 rg ${cols[2].x + 5} ${y - 12} Td (${escapePdf(ipStr.slice(0, 16))}) Tj ET`);

    // Occurrence Count
    currentPage.push(`BT /F2 8 Tf 0.70 0.20 0.20 rg ${cols[3].x + 10} ${y - 12} Td (${escapePdf(countStr)}) Tj ET`);

    // Risk level badge
    const riskColor = riskStr === 'HIGH' ? '0.85 0.15 0.15' : riskStr === 'MEDIUM' ? '0.85 0.55 0.05' : '0.10 0.65 0.35';
    currentPage.push(`BT /F2 7.5 Tf ${riskColor} rg ${cols[4].x + 10} ${y - 12} Td (${escapePdf(riskStr)}) Tj ET`);

    // Timestamp
    currentPage.push(`BT /F1 7.5 Tf 0.40 0.45 0.50 rg ${cols[5].x + 5} ${y - 12} Td (${escapePdf(timeStr.slice(0, 24))}) Tj ET`);

    y -= 19;
  });

  // Footer on all pages
  const totalPages = pages.length;
  pages.forEach((p, pIdx) => {
    p.push(`0.85 0.88 0.92 RG 0.5 w ${margin} 36 ${contentWidth} 0.5 re S`);
    p.push(`BT /F1 7.5 Tf 0.50 0.55 0.60 rg ${margin} 24 Td (TAVIX GUARD Security Analytics  |  Classified Incident Audit Report) Tj ET`);
    p.push(`BT /F1 7.5 Tf 0.50 0.55 0.60 rg ${pageWidth - margin - 55} 24 Td (Page ${pIdx + 1} of ${totalPages}) Tj ET`);
  });

  // PDF-1.4 File Construction
  const objects = [];
  objects.push('1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj');

  const pageObjIds = pages.map((_, i) => 3 + i * 2);
  objects.push(`2 0 obj << /Type /Pages /Kids [${pageObjIds.map((id) => `${id} 0 R`).join(' ')}] /Count ${pages.length} >> endobj`);

  pages.forEach((p, i) => {
    const pageId = 3 + i * 2;
    const contentId = pageId + 1;
    const stream = p.join('\n');
    const streamLen = new TextEncoder().encode(stream).length;
    objects.push(`${pageId} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 ${pageWidth} ${pageHeight}] /Contents ${contentId} 0 R /Resources << /Font << /F1 ${3 + pages.length * 2} 0 R /F2 ${4 + pages.length * 2} 0 R >> >> >> endobj`);
    objects.push(`${contentId} 0 obj << /Length ${streamLen} >> stream\n${stream}\nendstream endobj`);
  });

  const font1Id = 3 + pages.length * 2;
  const font2Id = font1Id + 1;
  objects.push(`${font1Id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj`);
  objects.push(`${font2Id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> endobj`);

  let pos = new TextEncoder().encode('%PDF-1.4\n').length;
  const xref = ['xref', `0 ${objects.length + 1}`, '0000000000 65535 f '];
  let body = '%PDF-1.4\n';

  objects.forEach((obj) => {
    xref.push(`${String(pos).padStart(10, '0')} 00000 n `);
    body += obj + '\n';
    pos = new TextEncoder().encode(body).length;
  });

  const startxref = pos;
  const trailer = `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${startxref}\n%%EOF`;
  const pdfString = body + xref.join('\n') + '\n' + trailer;

  const pdfBytes = new TextEncoder().encode(pdfString);
  const blob = new Blob([pdfBytes], { type: 'application/pdf' });
  triggerDownload(blob, 'TAVIX_GUARD_Incident_Analysis.pdf');
  return { success: true, count: alerts.length };
}
