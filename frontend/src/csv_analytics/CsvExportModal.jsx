import { useState } from 'react';
import { BACKEND_URL } from '../useAuthSentinel';
import ModalPortal from '../components/ModalPortal';

export default function CsvExportModal({ importId, onClose }) {
  const [exportType, setExportType] = useState('alerts');
  const [exportFormat, setExportFormat] = useState('csv');
  const [isExporting, setIsExporting] = useState(false);

  if (!importId) return null;

  const handleDownload = async () => {
    setIsExporting(true);
    try {
      const url = `${BACKEND_URL}/api/csv/export/${importId}?type=${exportType}&format=${exportFormat}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error('Export generation failed.');

      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `${exportType}_export_${importId.slice(0, 8)}.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      onClose();
    } catch (e) {
      alert('Error during export: ' + e.message);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <ModalPortal>
      <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" style={{ maxWidth: '440px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Export Analysis Report</h3>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body" style={{ gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
              Dataset to Export:
            </label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {[
                { id: 'alerts', title: 'Security Alerts Report', desc: 'Triggered detection rules and metadata' },
                { id: 'groups', title: 'Entity Groups Summary', desc: 'Aggregated metrics by entity dimension' },
                { id: 'risk', title: 'Risk Score & Signals Summary', desc: 'Detailed signal breakdown & explainable reasons' },
              ].map((opt) => (
                <label
                  key={opt.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    padding: '10px 12px',
                    border: '1px solid var(--border-light)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    background: exportType === opt.id ? 'var(--accent-hover)' : 'var(--bg-primary)',
                  }}
                >
                  <input
                    type="radio"
                    name="exportType"
                    value={opt.id}
                    checked={exportType === opt.id}
                    onChange={() => setExportType(opt.id)}
                    style={{ marginTop: '2px' }}
                  />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>{opt.title}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-tertiary)' }}>{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
              Format:
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              {[
                { id: 'csv', label: 'CSV (.csv)' },
                { id: 'json', label: 'JSON (.json)' },
              ].map((fmt) => (
                <label
                  key={fmt.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="radio"
                    name="exportFormat"
                    value={fmt.id}
                    checked={exportFormat === fmt.id}
                    onChange={() => setExportFormat(fmt.id)}
                  />
                  {fmt.label}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', padding: '16px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={isExporting}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleDownload} disabled={isExporting}>
            {isExporting ? 'Exporting...' : 'Download Export'}
          </button>
        </div>
      </div>
    </div>
  </ModalPortal>
);
}