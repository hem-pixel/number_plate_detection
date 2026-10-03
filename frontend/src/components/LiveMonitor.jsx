import React from 'react';
import { Bus, Car, ArrowDownRight, ArrowUpRight, Clock, ShieldCheck, HelpCircle, Eye } from 'lucide-react';
import { getImageUrl } from '../services/api';

export default function LiveMonitor({ summary, recentCollegeEvents, recentOtherEvents, latestDetection, onSelectImage }) {
  const collegeStats = summary?.college_vehicles || { total: 0, inside: 0, outside: 0, today_movements: 0 };
  const otherStats = summary?.other_vehicles || { total: 0, inside: 0, outside: 0, today_movements: 0 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }} id="live-monitoring-view">
      {/* LATEST LIVE DETECTION HERO BANNER */}
      {latestDetection ? (
        <div
          className={`latest-detection-banner ${latestDetection.vehicle_category === 'COLLEGE_VEHICLE' ? 'college' : 'other'}`}
          id="latest-detection-hero"
        >
          <div className="detection-hero-left">
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
                <span className={`detection-badge-tag ${latestDetection.vehicle_category === 'COLLEGE_VEHICLE' ? 'college' : 'other'}`}>
                  {latestDetection.vehicle_category === 'COLLEGE_VEHICLE' ? '🚌 COLLEGE VEHICLE' : '🚗 OTHER VEHICLE'}
                </span>
                <span className={`detection-movement-pill ${latestDetection.movement_type === 'ENTRY' ? 'entry' : 'exit'}`}>
                  {latestDetection.movement_type === 'ENTRY' ? <ArrowDownRight size={14} /> : <ArrowUpRight size={14} />}
                  <span>{latestDetection.movement_type}</span>
                </span>
                <span className={`badge-status ${latestDetection.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                  STATUS: {latestDetection.current_status}
                </span>
              </div>

              <div className="detection-hero-plate">
                <span className="mono">{latestDetection.plate_number}</span>
                {latestDetection.vehicle_name && (
                  <span className="detection-hero-name">({latestDetection.vehicle_name})</span>
                )}
              </div>
            </div>
          </div>

          <div className="detection-hero-metrics">
            <div className="hero-metric-item">
              <span className="hero-metric-label">Observed Time</span>
              <span className="hero-metric-value mono">
                {new Date(latestDetection.recognized_at || latestDetection.created_at || Date.now()).toLocaleTimeString()}
              </span>
            </div>

            <div className="hero-metric-item">
              <span className="hero-metric-label">YOLO Model</span>
              <span className="hero-metric-value" style={{ color: '#10b981' }}>
                {Math.round((latestDetection.yolo_confidence || 0) * 100)}%
              </span>
            </div>

            <div className="hero-metric-item">
              <span className="hero-metric-label">OCR Confidence</span>
              <span className="hero-metric-value" style={{ color: '#38bdf8' }}>
                {Math.round((latestDetection.ocr_confidence || 0) * 100)}%
              </span>
            </div>

            {latestDetection.plate_image_path && (
              <button
                className="sim-btn"
                onClick={() => onSelectImage(latestDetection)}
                title="View capture photos"
                type="button"
              >
                <Eye size={14} />
                <span>View Photo</span>
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="latest-detection-banner" style={{ borderLeft: '4px solid #64748b' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Clock size={20} color="#94a3b8" />
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
              Camera monitoring active. Waiting for vehicle plates in camera field of view...
            </span>
          </div>
        </div>
      )}

      {/* TWO SEPARATED MONITORING CATEGORIES */}
      <div className="monitoring-dual-grid">
        {/* ========================================================
            CATEGORY A: REGISTERED COLLEGE VEHICLES
           ======================================================== */}
        <section className="stream-panel college" id="section-college-vehicles">
          <div className="stream-header">
            <div className="stream-title-group">
              <div className="stream-icon-box college">
                <Bus size={20} />
              </div>
              <div>
                <h2 className="stream-title">COLLEGE VEHICLES</h2>
                <p className="stream-desc">Predefined college buses, staff vans & institutional fleet</p>
              </div>
            </div>
            <span className="detection-badge-tag college">REGISTERED FLEET</span>
          </div>

          {/* College Metric Stats */}
          <div className="stream-stats-row">
            <div className="stat-box">
              <span className="stat-box-label">Total Fleet</span>
              <span className="stat-box-number">{collegeStats.total}</span>
            </div>
            <div className="stat-box inside">
              <span className="stat-box-label">Currently Inside</span>
              <span className="stat-box-number">{collegeStats.inside}</span>
            </div>
            <div className="stat-box outside">
              <span className="stat-box-label">Currently Outside</span>
              <span className="stat-box-number">{collegeStats.outside}</span>
            </div>
          </div>

          {/* Recent College Vehicle Movements */}
          <div className="stream-content-title">
            <span>Recent College Vehicle Movements</span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {recentCollegeEvents.length} recorded
            </span>
          </div>

          <div className="activity-list" id="college-vehicle-activity-list">
            {recentCollegeEvents.length === 0 ? (
              <div className="empty-state">
                <Bus className="empty-state-icon" />
                <p>No recent college vehicle movements recorded yet.</p>
                <p style={{ fontSize: '0.78rem' }}>Use the simulator above to test Bus 01 or Bus 02 detection.</p>
              </div>
            ) : (
              recentCollegeEvents.map((item) => (
                <div key={item.id} className="activity-card" id={`college-card-${item.id}`}>
                  <div className="activity-left">
                    <div
                      className="plate-thumb-container"
                      onClick={() => onSelectImage(item)}
                      title="Click to zoom images"
                    >
                      {item.plate_image_path ? (
                        <img src={getImageUrl(item.plate_image_path)} alt="Crop" />
                      ) : (
                        <span style={{ fontSize: '0.65rem', color: '#64748b' }}>No Crop</span>
                      )}
                    </div>

                    <div className="activity-info">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="activity-plate mono">{item.plate_number}</span>
                        <span className={`badge-movement ${item.movement_type === 'ENTRY' ? 'entry' : 'exit'}`}>
                          {item.movement_type}
                        </span>
                      </div>
                      <span className="activity-name-tag">
                        🚌 {item.vehicle_name || 'College Vehicle'}
                      </span>
                      <span className="activity-time mono">
                        {new Date(item.recognized_at || item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  <div className="activity-right">
                    <span className={`badge-status ${item.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                      {item.current_status}
                    </span>
                    <span className="conf-pill mono">
                      Y: {Math.round((item.yolo_confidence || 0) * 100)}% • OCR: {Math.round((item.ocr_confidence || 0) * 100)}%
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* ========================================================
            CATEGORY B: OTHER / UNREGISTERED VEHICLES
           ======================================================== */}
        <section className="stream-panel other" id="section-other-vehicles">
          <div className="stream-header">
            <div className="stream-title-group">
              <div className="stream-icon-box other">
                <Car size={20} />
              </div>
              <div>
                <h2 className="stream-title">OTHER VEHICLES</h2>
                <p className="stream-desc">Visitors, private cars, cabs & unlisted campus vehicles</p>
              </div>
            </div>
            <span className="detection-badge-tag other">UNREGISTERED</span>
          </div>

          {/* Other Metric Stats */}
          <div className="stream-stats-row">
            <div className="stat-box">
              <span className="stat-box-label">Total Detected</span>
              <span className="stat-box-number">{otherStats.total}</span>
            </div>
            <div className="stat-box inside">
              <span className="stat-box-label">Currently Inside</span>
              <span className="stat-box-number">{otherStats.inside}</span>
            </div>
            <div className="stat-box outside">
              <span className="stat-box-label">Currently Outside</span>
              <span className="stat-box-number">{otherStats.outside}</span>
            </div>
          </div>

          {/* Recent Other Vehicle Movements */}
          <div className="stream-content-title">
            <span>Recent Other Vehicle Movements</span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {recentOtherEvents.length} recorded
            </span>
          </div>

          <div className="activity-list" id="other-vehicle-activity-list">
            {recentOtherEvents.length === 0 ? (
              <div className="empty-state">
                <Car className="empty-state-icon" />
                <p>No recent other vehicle movements recorded yet.</p>
                <p style={{ fontSize: '0.78rem' }}>Visitor plates will automatically appear here.</p>
              </div>
            ) : (
              recentOtherEvents.map((item) => (
                <div key={item.id} className="activity-card" id={`other-card-${item.id}`}>
                  <div className="activity-left">
                    <div
                      className="plate-thumb-container"
                      onClick={() => onSelectImage(item)}
                      title="Click to zoom images"
                    >
                      {item.plate_image_path ? (
                        <img src={getImageUrl(item.plate_image_path)} alt="Crop" />
                      ) : (
                        <span style={{ fontSize: '0.65rem', color: '#64748b' }}>No Crop</span>
                      )}
                    </div>

                    <div className="activity-info">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="activity-plate mono">{item.plate_number}</span>
                        <span className={`badge-movement ${item.movement_type === 'ENTRY' ? 'entry' : 'exit'}`}>
                          {item.movement_type}
                        </span>
                      </div>
                      <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                        🚗 Unregistered Vehicle
                      </span>
                      <span className="activity-time mono">
                        {new Date(item.recognized_at || item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  </div>

                  <div className="activity-right">
                    <span className={`badge-status ${item.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                      {item.current_status}
                    </span>
                    <span className="conf-pill mono">
                      Y: {Math.round((item.yolo_confidence || 0) * 100)}% • OCR: {Math.round((item.ocr_confidence || 0) * 100)}%
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
