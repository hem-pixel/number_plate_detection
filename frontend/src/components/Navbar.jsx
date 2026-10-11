import React from 'react';
import { Bus, Video, ListFilter, Users, LogOut, ShieldCheck, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Navbar({ activeTab, setActiveTab, wsConnected, isConnected }) {
  const { user, isAdmin, logout } = useAuth();
  const connected = wsConnected ?? isConnected ?? false;

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
          className={`nav-tab-btn ${activeTab === 'fleet' || activeTab === 'college-vehicles' ? 'active' : ''}`}
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

        {isAdmin && (
          <button
            id="tab-user-management"
            className={`nav-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
            type="button"
          >
            <Users size={16} />
            <span>User Management</span>
          </button>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div className="nav-status-badge" id="ws-status-indicator">
          <div
            className="pulse-dot"
            style={{
              backgroundColor: connected ? '#10b981' : '#f43f5e',
              boxShadow: connected ? '0 0 10px #10b981' : '0 0 10px #f43f5e'
            }}
          />
          <span>{connected ? 'LIVE FEED CONNECTED' : 'OFFLINE'}</span>
        </div>

        {user && (
          <div
            id="user-profile-badge"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              padding: '0.35rem 0.75rem',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '9999px'
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '0.15rem 0.5rem',
                borderRadius: '9999px',
                background: isAdmin ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                color: isAdmin ? '#34d399' : '#38bdf8',
                border: `1px solid ${isAdmin ? 'rgba(16, 185, 129, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`
              }}
            >
              {isAdmin ? <ShieldCheck size={12} /> : <Shield size={12} />}
              <span>{user.role}</span>
            </div>
            <span
              style={{
                fontSize: '0.8rem',
                color: '#e2e8f0',
                maxWidth: '150px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
              title={user.email}
            >
              {user.full_name || user.email}
            </span>
            <button
              id="btn-logout"
              onClick={logout}
              title="Sign Out"
              type="button"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                padding: '0.2rem',
                borderRadius: '4px',
                transition: 'color 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#f43f5e')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
            >
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}

