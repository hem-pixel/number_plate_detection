import React from 'react';
import { Bus, Video, Database, ListFilter } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, isConnected }) {
  return (
    <nav className="navbar" id="main-navbar">
      <div className="nav-brand">
        <div className="nav-logo-icon">
          <Bus size={24} />
        </div>
        <div>
          <h1 className="nav-title">CAMPUS VEHICLE ACCESS</h1>
          <p className="nav-subtitle">Automatic Number Plate Recognition & Fleet Monitor</p>
        </div>
      </div>

      <div className="nav-tabs" role="tablist">
        <button
          id="tab-live-monitor"
          className={`nav-tab-btn ${activeTab === 'live' ? 'active' : ''}`}
          onClick={() => setActiveTab('live')}
          type="button"
        >
          <Video size={16} />
          <span>Live Monitor</span>
        </button>

        <button
          id="tab-college-fleet"
          className={`nav-tab-btn ${activeTab === 'fleet' ? 'active' : ''}`}
          onClick={() => setActiveTab('fleet')}
          type="button"
        >
          <Bus size={16} />
          <span>College Fleet Master</span>
        </button>

        <button
          id="tab-movement-logs"
          className={`nav-tab-btn ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
          type="button"
        >
          <ListFilter size={16} />
          <span>All Movements</span>
        </button>
      </div>

      <div className="nav-status-badge" id="ws-status-indicator">
        <div className="pulse-dot" style={{ backgroundColor: isConnected ? '#10b981' : '#f43f5e', boxShadow: isConnected ? '0 0 10px #10b981' : '0 0 10px #f43f5e' }} />
        <span>{isConnected ? 'LIVE FEED CONNECTED' : 'OFFLINE'}</span>
      </div>
    </nav>
  );
}
