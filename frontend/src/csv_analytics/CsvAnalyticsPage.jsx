import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import './csvAnalytics.css';
import { BACKEND_URL } from '../useAuthSentinel';
import CsvAnalyticsCharts from './CsvAnalyticsCharts';
import CsvGroupsExplorer from './CsvGroupsExplorer';
import CsvAlertsExplorer from './CsvAlertsExplorer';

const TABS = [
  { id: 'groups', label: 'Grouped Dimensions' },
  { id: 'alerts', label: 'Security Alerts', hasBadge: true },
  { id: 'dashboard', label: 'Dashboard & Charts' },
];

export default function CsvAnalyticsPage() {
  const [activeTab, setActiveTab] = useState('groups');
  const [currentImportId, setCurrentImportId] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const fileInputRef = useRef(null);
  const shouldReduceMotion = useReducedMotion();

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
        setActiveTab('groups');
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

      {/* Clean Navigation Tabs */}
      <div className="csv-tabs-nav" role="tablist">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`csv-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <span>{tab.label}</span>
              {tab.hasBadge && summaryData?.alerts_count > 0 && (
                <span className="csv-tab-badge">{summaryData.alerts_count}</span>
              )}
              {isActive && (
                <motion.div
                  layoutId="csv-active-tab-indicator"
                  className="csv-tab-active-indicator"
                  transition={
                    shouldReduceMotion
                      ? { duration: 0 }
                      : { type: 'spring', stiffness: 500, damping: 38, mass: 0.8 }
                  }
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Contents with smooth fade transition and persistent state */}
      <div className="csv-tab-content-container">
        {/* Tab 1: Grouped Dimensions */}
        <div
          className={`csv-tab-pane ${activeTab === 'groups' ? 'active' : ''}`}
          role="tabpanel"
          aria-hidden={activeTab !== 'groups'}
        >
          {summaryData ? (
            <CsvGroupsExplorer importId={currentImportId} />
          ) : (
            <div className="csv-empty-state-card">
              <p style={{ color: 'var(--text-tertiary)' }}>Please upload a CSV file to inspect groups.</p>
            </div>
          )}
        </div>

        {/* Tab 2: Security Alerts */}
        <div
          className={`csv-tab-pane ${activeTab === 'alerts' ? 'active' : ''}`}
          role="tabpanel"
          aria-hidden={activeTab !== 'alerts'}
        >
          {summaryData ? (
            <CsvAlertsExplorer importId={currentImportId} />
          ) : (
            <div className="csv-empty-state-card">
              <p style={{ color: 'var(--text-tertiary)' }}>Please upload a CSV file to inspect alerts.</p>
            </div>
          )}
        </div>

        {/* Tab 3: Dashboard & Charts */}
        <div
          className={`csv-tab-pane ${activeTab === 'dashboard' ? 'active' : ''}`}
          role="tabpanel"
          aria-hidden={activeTab !== 'dashboard'}
        >
          {summaryData ? (
            <div className="csv-dashboard-charts-container">
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
        </div>
      </div>
    </div>
  );
}
