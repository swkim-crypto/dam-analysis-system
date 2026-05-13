import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import CriteriaPanel from './components/CriteriaPanel';
import ResultsPanel from './components/ResultsPanel';
import MapView from './components/MapView';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [files, setFiles] = useState({
    dem: null,
    rivers: null,
    boundary: null
  });
  
  const [criteria, setCriteria] = useState({
    min_order: 3,
    max_order: 5,
    min_drainage: 50,
    max_drainage: 5000,
    min_volume: 5.0,
    max_dam_length: 1000,
    max_slope: 35,
    search_interval: 500
  });
  
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Poll for status updates
  useEffect(() => {
    if (!taskId || !isAnalyzing) return;
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_URL}/api/status/${taskId}`);
        const data = await response.json();
        setStatus(data);
        
        if (data.status === 'completed') {
          setIsAnalyzing(false);
          loadResults(taskId);
        } else if (data.status === 'failed') {
          setIsAnalyzing(false);
          alert(`분석 실패: ${data.message || data.error || '알 수 없는 오류'}`);
        }
      } catch (error) {
        console.error('Status check failed:', error);
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [taskId, isAnalyzing]);

  const handleFileChange = (type, file) => {
    setFiles(prev => ({ ...prev, [type]: file }));
  };

  const handleCriteriaChange = (newCriteria) => {
    setCriteria(newCriteria);
  };

  const startAnalysis = async () => {
    if (!files.dem || !files.rivers || !files.boundary) {
      alert('모든 파일을 업로드해주세요.');
      return;
    }
    
    const formData = new FormData();
    formData.append('dem', files.dem);
    formData.append('rivers', files.rivers);
    formData.append('boundary', files.boundary);
    formData.append('criteria', JSON.stringify(criteria));
    
    setIsAnalyzing(true);
    setStatus({ progress: 0, message: '업로드 중...' });
    
    try {
      const response = await fetch(`${API_URL}/api/analyze`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      setTaskId(data.task_id);
    } catch (error) {
      console.error('Analysis failed:', error);
      alert('분석 시작 실패: ' + error.message);
      setIsAnalyzing(false);
    }
  };

  const loadResults = async (tid) => {
    try {
      const response = await fetch(`${API_URL}/api/results/${tid}`);
      const data = await response.json();
      setResults(data);
    } catch (error) {
      console.error('Failed to load results:', error);
    }
  };

  const downloadFile = async (filename) => {
    if (!taskId) return;
    
    const url = `${API_URL}/api/download/${taskId}/${filename}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  const filesReady = files.dem && files.rivers && files.boundary;

  return (
    <div className="App">
      <header className="header">
        <div className="header-content">
          <h1>🏞️ Dam Site Analysis System</h1>
          <p>Automated Geospatial Analysis for Hydropower Development</p>
        </div>
      </header>

      <div className="main-container">
        <div className="left-panel">
          <FileUpload 
            files={files} 
            onFileChange={handleFileChange} 
          />
          
          <CriteriaPanel 
            criteria={criteria}
            onChange={handleCriteriaChange}
          />
          
          <div className="action-section">
            <button 
              className="btn-primary btn-lg"
              onClick={startAnalysis}
              disabled={!filesReady || isAnalyzing}
            >
              {isAnalyzing ? '⏳ 분석 중...' : '🚀 분석 시작'}
            </button>
            
            {status && isAnalyzing && (
              <div className="progress-container">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${status.progress}%` }}
                  />
                </div>
                <div className="progress-text">{status.message}</div>
              </div>
            )}
          </div>
        </div>

        <div className="right-panel">
          {results ? (
            <ResultsPanel 
              results={results}
              onDownload={downloadFile}
            />
          ) : (
            <div className="empty-state">
              <MapView sites={[]} />
              <div className="empty-message">
                <h3>분석 결과가 여기에 표시됩니다</h3>
                <p>파일을 업로드하고 분석을 시작하세요</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
