import React from 'react';
import './FileUpload.css';

const FileUpload = ({ files, onFileChange }) => {
  const handleFileSelect = (type, event) => {
    const file = event.target.files[0];
    if (file) {
      onFileChange(type, file);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="file-upload-section">
      <h2 className="section-title">📁 데이터 업로드</h2>
      
      <div className="upload-item">
        <label className="upload-label">DEM (GeoTIFF)</label>
        <input
          type="file"
          id="dem-file"
          accept=".tif,.tiff,.zip"
          onChange={(e) => handleFileSelect('dem', e)}
          style={{ display: 'none' }}
        />
        <button 
          className="btn-upload"
          onClick={() => document.getElementById('dem-file').click()}
        >
          {files.dem ? '✓ 변경' : '파일 선택'}
        </button>
        {files.dem && (
          <div className="file-info">
            ✓ {files.dem.name} ({formatFileSize(files.dem.size)})
          </div>
        )}
      </div>

      <div className="upload-item">
        <label className="upload-label">하천 레이어 (Shapefile)</label>
        <input
          type="file"
          id="rivers-file"
          accept=".shp,.zip"
          onChange={(e) => handleFileSelect('rivers', e)}
          style={{ display: 'none' }}
        />
        <button 
          className="btn-upload"
          onClick={() => document.getElementById('rivers-file').click()}
        >
          {files.rivers ? '✓ 변경' : '파일 선택'}
        </button>
        {files.rivers && (
          <div className="file-info">
            ✓ {files.rivers.name} ({formatFileSize(files.rivers.size)})
          </div>
        )}
      </div>

      <div className="upload-item">
        <label className="upload-label">유역 경계 (Shapefile)</label>
        <input
          type="file"
          id="boundary-file"
          accept=".shp,.zip"
          onChange={(e) => handleFileSelect('boundary', e)}
          style={{ display: 'none' }}
        />
        <button 
          className="btn-upload"
          onClick={() => document.getElementById('boundary-file').click()}
        >
          {files.boundary ? '✓ 변경' : '파일 선택'}
        </button>
        {files.boundary && (
          <div className="file-info">
            ✓ {files.boundary.name} ({formatFileSize(files.boundary.size)})
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
