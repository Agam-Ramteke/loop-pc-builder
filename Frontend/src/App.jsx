import { useState } from 'react';
import FileList from './components/FileList';
import JobList from './components/JobList';
import LogViewer from './components/LogViewer';
import './index.css';

function App() {
  const [selectedJobId, setSelectedJobId] = useState(null);

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
  );
}

export default App;

