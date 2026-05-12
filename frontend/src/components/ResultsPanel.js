import React, { useState } from 'react';
import MapView from './MapView';
import './ResultsPanel.css';

const ResultsPanel = ({ results, onDownload }) => {
  const [selectedSite, setSelectedSite] = useState(null);

  if (!results || !results.sites) {
    return <div>결과 로딩 중...</div>;
  }

  const { sites, total_sites } = results;

  // Calculate summary statistics
  const avgVolume = sites.reduce((sum, s) => sum + s.volume, 0) / sites.length;
  const avgLength = sites.reduce((sum, s) => sum + s.damLength, 0) / sites.length;
  const maxHeight = Math.max(...sites.map(s => s.height));

  return (
    <div className="results-container">
      {/* Map */}
      <div className="map-container">
        <MapView 
          sites={sites} 
          selectedSite={selectedSite}
          onSiteClick={setSelectedSite}
        />
      </div>

      {/* Results Summary */}
      <div className="results-summary">
        <h2 className="section-title">📊 분석 결과</h2>
        
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-label">발견된 후보지</div>
            <div className="stat-value">{total_sites}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">평균 저수량</div>
            <div className="stat-value">{avgVolume.toFixed(0)} Mm³</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">평균 댐길이</div>
            <div className="stat-value">{avgLength.toFixed(0)} m</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">최대 높이</div>
            <div className="stat-value">{maxHeight} m</div>
          </div>
        </div>

        {/* Download Buttons */}
        <div className="download-section">
          <h3>📥 결과 파일 다운로드</h3>
          <div className="download-grid">
            <button 
              className="btn-download"
              onClick={() => onDownload('candidates.js')}
            >
              candidates.js
            </button>
            <button 
              className="btn-download"
              onClick={() => onDownload('profiles.js')}
            >
              profiles.js
            </button>
            <button 
              className="btn-download"
              onClick={() => onDownload('floodPolygons.js')}
            >
              floodPolygons.js
            </button>
            <button 
              className="btn-download"
              onClick={() => onDownload('damLengths.js')}
            >
              damLengths.js
            </button>
          </div>
        </div>

        {/* Site List */}
        <div className="site-list">
          <h3>🎯 후보지 목록</h3>
          <div className="site-list-scroll">
            {sites.map(site => (
              <div 
                key={site.id}
                className={`site-item ${selectedSite?.id === site.id ? 'selected' : ''}`}
                onClick={() => setSelectedSite(site)}
              >
                <div className="site-header">
                  <span className="site-id">{site.id}</span>
                  <span className="site-badge">{site.volume.toFixed(0)} Mm³</span>
                </div>
                <div className="site-details">
                  <span>H: {site.height}m</span>
                  <span>L: {site.damLength}m</span>
                  <span>Order: {site.order}</span>
                  <span>Bed: {site.bed}m</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsPanel;
