import { useState, useEffect, useCallback, useRef } from 'react';
import './csvAnalytics.css';
import { BACKEND_URL } from '../useAuthSentinel';
import CsvAnalyticsCharts from './CsvAnalyticsCharts';
import CsvGroupsExplorer from './CsvGroupsExplorer';
import CsvAlertsExplorer from './CsvAlertsExplorer';
import PageTransition from '../components/PageTransition';

export default function CsvAnalyticsPage() {
  const [activeTab, setActiveTab] = useState('groups');
  const [currentImportId, setCurrentImportId] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);

  const fetchSummary = useCallback(async (importId = null) => {
    try {
      const url = importId
        ? `${BACKEND_URL}/api/csv/summary?import_id=${importId}`
        : `${BACKEND_URL}/api/csv/summary`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        if (data.found) {
          setSummaryData(data);
          setCurrentImportId(data.id);
        } else {
          setSummaryData(null);
          setCurrentImportId(null);
        }
      } else {
        setSummaryData(null);
      }
    } catch (e) {
      console.warn('Error fetching CSV summary:', e);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const handleFileChange = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Only .csv files are supported. Please select a valid CSV file.');
      return;
    }

    setUploadError(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${BACKEND_URL}/api/csv/upload`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Upload and security analysis failed.');
      }

      if (data && data.import_id) {
        setCurrentImportId(data.import_id);
        await fetchSummary(data.import_id);
        setActiveTab('dashboard');
      }
    } catch (err) {
      setUploadError(err.message || 'Failed to upload CSV file.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const triggerUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="csv-analytics-container">
      {/* Hidden file input controlled exclusively by the top-right Upload New CSV button */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,text/csv"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {/* Top Header */}
      <div className="csv-top-bar">
        <div className="csv-top-title">
          <h2 style={{ margin: 0 }}>CSV Security Analytics & Correlation</h2>
        </div>

        <div className="csv-actions-group">
          <button
            type="button"
            className="btn-primary"
            onClick={triggerUpload}
            disabled={isUploading}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            <span>{isUploading ? 'Uploading & Analyzing...' : 'Upload New CSV'}</span>
          </button>
        </div>
      </div>

      {/* Upload error banner if any */}
      {uploadError && (
        <div className="import-banner error" style={{ margin: 0 }}>
          <div className="banner-content">
            <h4>Upload Error</h4>
            <p>{uploadError}</p>
          </div>
        </div>
      )}

      {/* Clean Navigation Tabs (No icons) */}
      <div className="csv-tabs-nav">
        <button
          type="button"
          className={`csv-tab-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          <span>Grouped Dimensions</span>
        </button>

        <button
          type="button"
          className={`csv-tab-btn ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          <span>Security Alerts</span>
          {summaryData?.alerts_count > 0 && (
            <span className="csv-tab-badge">{summaryData.alerts_count}</span>
          )}
        </button>

        <button
          type="button"
          className={`csv-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          <span>Dashboard & Charts</span>
        </button>
      </div>

      {/* Tab Contents */}
      <PageTransition transitionKey={activeTab}>
        {activeTab === 'dashboard' && (
          <>
            {summaryData ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <CsvAnalyticsCharts summary={summaryData} />
              </div>
            ) : (
              <div className="csv-empty-state-card">
                <h3>No CSV Log File Analyzed Yet</h3>
                <p>
                  Click the <strong>Upload New CSV</strong> button above to load and correlate security events.
                </p>
              </div>
            )}
          </>
        )}

        {activeTab === 'alerts' && (
          <>
            {summaryData ? (
              <CsvAlertsExplorer importId={currentImportId} />
            ) : (
              <div className="csv-empty-state-card">
                <p style={{ color: 'var(--text-tertiary)' }}>Please upload a CSV file to inspect alerts.</p>
              </div>
            )}
          </>
        )}

        {activeTab === 'groups' && (
          <>
            {summaryData ? (
              <CsvGroupsExplorer importId={currentImportId} />
            ) : (
              <div className="csv-empty-state-card">
                <p style={{ color: 'var(--text-tertiary)' }}>Please upload a CSV file to inspect groups.</p>
              </div>
            )}
          </>
        )}
      </PageTransition>
    </div>
  );
}
