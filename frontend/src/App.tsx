import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ChatInterface from './components/ChatInterface';
import SessionList from './components/SessionList';
import AgentMonitor from './components/AgentMonitor';
import './App.css';

function App() {
  const [userId] = useState('user-' + Math.random().toString(36).substr(2, 9));

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>Manus AI Clone</h1>
          <p>Autonomous AI Agent Platform</p>
        </header>

        <div className="app-container">
          <Routes>
            <Route path="/" element={<ChatInterface userId={userId} />} />
            <Route path="/sessions" element={<SessionList userId={userId} />} />
            <Route path="/monitor" element={<AgentMonitor />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
