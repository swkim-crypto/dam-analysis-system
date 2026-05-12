import React from 'react';
import './CriteriaPanel.css';

const CriteriaPanel = ({ criteria, onChange }) => {
  const handleChange = (field, value) => {
    onChange({ ...criteria, [field]: parseFloat(value) || value });
  };

  const reset = () => {
    onChange({
      min_order: 3,
      max_order: 5,
      min_drainage: 50,
      max_drainage: 5000,
      min_volume: 5.0,
      max_dam_length: 1000,
      max_slope: 35,
      search_interval: 500
    });
  };

  return (
    <div className="criteria-panel">
      <h2 className="section-title">⚙️ 선정 조건</h2>
      
      <div className="criteria-group">
        <label>하천 등급 범위</label>
        <div className="range-inputs">
          <input
            type="number"
            value={criteria.min_order}
            onChange={(e) => handleChange('min_order', e.target.value)}
            min="1"
            max="6"
          />
          <span>~</span>
          <input
            type="number"
            value={criteria.max_order}
            onChange={(e) => handleChange('max_order', e.target.value)}
            min="1"
            max="6"
          />
        </div>
      </div>

      <div className="criteria-grid">
        <div className="criteria-group">
          <label>최소 유역면적 (km²)</label>
          <input
            type="number"
            value={criteria.min_drainage}
            onChange={(e) => handleChange('min_drainage', e.target.value)}
          />
        </div>

        <div className="criteria-group">
          <label>최대 유역면적 (km²)</label>
          <input
            type="number"
            value={criteria.max_drainage}
            onChange={(e) => handleChange('max_drainage', e.target.value)}
          />
        </div>

        <div className="criteria-group">
          <label>최소 저수량 (Mm³)</label>
          <input
            type="number"
            step="0.1"
            value={criteria.min_volume}
            onChange={(e) => handleChange('min_volume', e.target.value)}
          />
        </div>

        <div className="criteria-group">
          <label>최대 댐길이 (m)</label>
          <input
            type="number"
            value={criteria.max_dam_length}
            onChange={(e) => handleChange('max_dam_length', e.target.value)}
          />
        </div>

        <div className="criteria-group">
          <label>최대 경사 (도)</label>
          <input
            type="number"
            value={criteria.max_slope}
            onChange={(e) => handleChange('max_slope', e.target.value)}
          />
        </div>

        <div className="criteria-group">
          <label>탐색 간격 (m)</label>
          <input
            type="number"
            value={criteria.search_interval}
            onChange={(e) => handleChange('search_interval', e.target.value)}
          />
        </div>
      </div>

      <button className="btn-secondary btn-sm" onClick={reset}>
        초기화
      </button>
    </div>
  );
};

export default CriteriaPanel;
