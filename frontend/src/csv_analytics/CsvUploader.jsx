import { useState, useRef } from 'react';
import { BACKEND_URL } from '../useAuthSentinel';

export default function CsvUploader({ onUploadSuccess, latestImport }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const fileInputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file) => {
    if (!file) return 'No file selected.';
    if (!file.name.toLowerCase().endsWith('.csv')) {
      return 'Only .csv files are supported. Please select a valid CSV file.';
    }
    if (file.size === 0) {
      return 'The selected file is empty (0 bytes). Please select a file with data.';
    }
    if (file.size > 50 * 1024 * 1024) {
      return 'File size exceeds maximum allowed limit of 50 MB.';
    }
    return null;
  };

  const handleFileSelection = (file) => {
    setErrorMessage(null);
    setUploadResult(null);
    const err = validateFile(file);
    if (err) {
      setErrorMessage(err);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadProgress(20);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setUploadProgress(50);
      const res = await fetch(`${BACKEND_URL}/api/csv/upload`, {
        method: 'POST',
        body: formData,
      });

      setUploadProgress(85);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Upload and analysis failed.');
      }

      setUploadProgress(100);
      setUploadResult(data);
      if (onUploadSuccess) {
        onUploadSuccess(data);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Network error during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="csv-upload-card">
      {/* Dropzone */}
      <div
        className={`dropzone ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileSelection(e.target.files[0]);
            }
          }}
        />

        <div className="dropzone-icon-container">
          <div className="dropzone-icon">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div className="dropzone-add-badge" title="Add CSV File">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </div>
        </div>

        <div className="dropzone-title">Drag & Drop CSV File Here</div>
        <div className="dropzone-subtitle">Accepts .csv files up to 50 MB with flexible column detection</div>

        <div className="dropzone-divider">
          <span>or</span>
        </div>

        <button
          type="button"
          className="btn-secondary"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current && fileInputRef.current.click();
          }}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '9px 18px', fontWeight: 600 }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>Choose CSV File</span>
        </button>
      </div>


      {/* Selected File Bar */}
      {selectedFile && (
        <div className="file-preview-bar">
          <div className="file-preview-left">
            <div className="file-preview-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <div>
              <div className="file-preview-name">{selectedFile.name}</div>
              <div className="file-preview-meta">
                {formatFileSize(selectedFile.size)} • Ready for analysis
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                setSelectedFile(null);
                setErrorMessage(null);
                setUploadResult(null);
              }}
              disabled={isUploading}
            >
              Clear
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading ? 'Analyzing...' : 'Analyze CSV'}
            </button>
          </div>
        </div>
      )}

      {/* Progress */}
      {isUploading && (
        <div className="progress-container">
          <div className="progress-header">
            <span>Parsing and correlating events across 10 security rules...</span>
            <span>{uploadProgress}%</span>
          </div>
          <div className="progress-track">
            <div
              className={`progress-bar-fill ${uploadProgress < 100 ? 'indeterminate' : ''}`}
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="import-banner error">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
          <div className="banner-content">
            <h4>Import Validation Error</h4>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Success Notification */}
      {uploadResult && uploadResult.success && (
        <div className="import-banner success">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <div className="banner-content">
            <h4>✓ CSV Imported & Analyzed Successfully</h4>
            <ul>
              <li>✓ <strong>{uploadResult.valid_records?.toLocaleString()}</strong> records validated & normalized</li>
              <li>✓ <strong>{uploadResult.groups?.toLocaleString()}</strong> entity groups detected</li>
              <li>✓ <strong>{uploadResult.alerts?.toLocaleString()}</strong> security alerts generated ({uploadResult.high_risk} High / Critical)</li>
              {uploadResult.invalid_records > 0 && (
                <li style={{ color: '#d97706' }}>
                  ⚠ <strong>{uploadResult.invalid_records}</strong> invalid rows quarantined with logged reasons
                </li>
              )}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}