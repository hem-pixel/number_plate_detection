import React, { useState, useEffect } from 'react';
import { ListFilter, Search, RefreshCw, Eye, ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { fetchRecognitions, getImageUrl } from '../services/api';

export default function MovementLogs({ onSelectImage, showToast }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState('');
  const [movementFilter, setMovementFilter] = useState('');
  const [searchPlate, setSearchPlate] = useState('');

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await fetchRecognitions({
        limit: 100,
        category: categoryFilter || null,
        movement: movementFilter || null,
        search: searchPlate || null,
      });
      setLogs(data);
    } catch (err) {
      console.error(err);
      if (showToast) showToast(`Failed to load logs: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, [categoryFilter, movementFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadLogs();
  };

  return (
    <div className="master-page-container" id="movement-logs-page">
      <div className="master-header-row">
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ListFilter size={24} color="#06b6d4" />
            <span>Complete Movement Audit Trail</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Historical entries and exits for both registered college fleet and visitor vehicles
          </p>
        </div>

        <div className="master-controls">
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              className="search-input"
              id="search-logs-input"
              placeholder="Filter by plate (e.g. TN45BD7321)"
              value={searchPlate}
              onChange={(e) => setSearchPlate(e.target.value)}
            />
            <button className="sim-btn" type="submit" id="btn-search-logs">
              <Search size={15} />
              <span>Filter</span>
            </button>
          </form>

          <select
            className="form-select"
            id="filter-category-select"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ width: '180px' }}
          >
            <option value="">All Categories</option>
            <option value="COLLEGE_VEHICLE">🚌 College Vehicles Only</option>
            <option value="OTHER_VEHICLE">🚗 Other Vehicles Only</option>
          </select>

          <select
            className="form-select"
            id="filter-movement-select"
            value={movementFilter}
            onChange={(e) => setMovementFilter(e.target.value)}
            style={{ width: '150px' }}
          >
            <option value="">All Movements</option>
            <option value="ENTRY">Entry Only</option>
            <option value="EXIT">Exit Only</option>
          </select>

          <button className="icon-btn" onClick={loadLogs} title="Refresh Logs" type="button">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="custom-table" id="movement-logs-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Time</th>
              <th>Plate Number</th>
              <th>Vehicle Name</th>
              <th>Category</th>
              <th>Movement</th>
              <th>Status</th>
              <th>Camera</th>
              <th>OCR Conf</th>
              <th style={{ textAlign: 'right' }}>Photos</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  {loading ? 'Retrieving movement records...' : 'No movement events match criteria.'}
                </td>
              </tr>
            ) : (
              logs.map((item) => {
                const dateObj = new Date(item.recognized_at || item.created_at || Date.now());
                const dateStr = dateObj.toLocaleDateString();
                const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                return (
                  <tr key={item.id} id={`log-row-${item.id}`}>
                    <td className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      {dateStr}
                    </td>
                    <td className="mono" style={{ fontSize: '0.82rem', color: '#38bdf8' }}>
                      {timeStr}
                    </td>
                    <td>
                      <span className="mono" style={{ fontWeight: 700, color: '#ffffff', letterSpacing: '0.04em' }}>
                        {item.plate_number}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.85rem', color: item.vehicle_name ? '#f8fafc' : 'var(--text-muted)' }}>
                        {item.vehicle_name || '—'}
                      </span>
                    </td>
                    <td>
                      {item.vehicle_category === 'COLLEGE_VEHICLE' ? (
                        <span className="detection-badge-tag college">
                          COLLEGE VEHICLE
                        </span>
                      ) : (
                        <span className="detection-badge-tag other">
                          OTHER VEHICLE
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`detection-movement-pill ${item.movement_type === 'ENTRY' ? 'entry' : 'exit'}`} style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}>
                        {item.movement_type === 'ENTRY' ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}
                        <span>{item.movement_type}</span>
                      </span>
                    </td>
                    <td>
                      <span className={`badge-status ${item.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                        {item.current_status || 'UNKNOWN'}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                      {item.camera_id || 'GATE_CAMERA_01'}
                    </td>
                    <td className="mono" style={{ fontSize: '0.8rem', color: '#10b981' }}>
                      {Math.round((item.ocr_confidence || 0) * 100)}%
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="sim-btn"
                        onClick={() => onSelectImage(item)}
                        style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                        type="button"
                        title="View Full Frame and Plate Crop"
                      >
                        <Eye size={13} />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
