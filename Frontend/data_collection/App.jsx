import { useState, useEffect } from 'react';
import FileList from './components/FileList';
import JobList from './components/JobList';
import LogViewer from './components/LogViewer';
import CollectionBrowser from './components/CollectionBrowser';
import './index.css';

function App() {
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [currentView, setCurrentView] = useState('scraper');

  // Simple hash-based routing
  useEffect(() => {
    const hash = window.location.hash.slice(1) || 'scraper';
    setCurrentView(hash);
    
    const handleHashChange = () => {
      const newHash = window.location.hash.slice(1) || 'scraper';
      setCurrentView(newHash);
    };
    
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  function handleJobStarted(jobId) {
    setSelectedJobId(jobId);
  }

  function handleJobSelect(jobId) {
    setSelectedJobId(jobId);
  }

  function handleJobStopped(jobId) {
    // Optionally refresh or update UI
    if (selectedJobId === jobId) {
      // Keep selected, logs will show termination
    }
  }

  return (
    <div>
      {/* Navigation Bar */}
      <nav style={{
        background: '#fafafa',
        borderBottom: '1px solid #e0e0e0',
        padding: '12px 20px',
        display: 'flex',
        gap: '20px',
        alignItems: 'center'
      }}>
        <div style={{ fontWeight: '600', fontSize: '18px', marginRight: '20px' }}>
          Loop PC Builder
        </div>
        <a
          href="#scraper"
          onClick={(e) => {
            e.preventDefault();
            window.location.hash = 'scraper';
          }}
          style={{
            padding: '8px 16px',
            textDecoration: 'none',
            color: currentView === 'scraper' ? '#007bff' : '#666',
            borderBottom: currentView === 'scraper' ? '2px solid #007bff' : '2px solid transparent',
            fontWeight: currentView === 'scraper' ? '600' : '400'
          }}
        >
          Scraper Dashboard
        </a>
        <a
          href="#collections"
          onClick={(e) => {
            e.preventDefault();
            window.location.hash = 'collections';
          }}
          style={{
            padding: '8px 16px',
            textDecoration: 'none',
            color: currentView === 'collections' ? '#007bff' : '#666',
            borderBottom: currentView === 'collections' ? '2px solid #007bff' : '2px solid transparent',
            fontWeight: currentView === 'collections' ? '600' : '400'
          }}
        >
          Collection Browser
        </a>
      </nav>

      {/* Content Area */}
      {currentView === 'scraper' ? (
        <div className="app-container">
          <div className="panel panel-left">
            <div className="panel-header">Data Files</div>
            <FileList onJobStarted={handleJobStarted} />
          </div>
          
          <div className="panel panel-middle">
            <div className="panel-header">Jobs</div>
            <JobList
              selectedJobId={selectedJobId}
              onJobSelect={handleJobSelect}
              onJobStopped={handleJobStopped}
            />
          </div>
          
          <div className="panel panel-right">
            <LogViewer jobId={selectedJobId} />
          </div>
        </div>
      ) : (
        <CollectionBrowser />
      )}
    </div>
  );
}

export default App;

