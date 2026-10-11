import React, { useState, useEffect } from 'react';
import {
  Bus,
  Car,
  ArrowDownRight,
  ArrowUpRight,
  Clock,
  Eye,
  Camera,
  Activity,
  ArrowDown,
  ArrowUp,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { getImageUrl, fetchCameraConfig } from '../services/api';

export default function LiveMonitor({
  summary,
  collegeEvents = [],
  recentCollegeEvents = [],
  otherEvents = [],
  recentOtherEvents = [],
  liveMovements = [],
  latestDetection,
  onSelectImage,
  onViewImage
}) {
  // Support both prop conventions
  const collegeList = collegeEvents.length > 0 ? collegeEvents : recentCollegeEvents;
  const otherList = otherEvents.length > 0 ? otherEvents : recentOtherEvents;
  const handleViewPhoto = (item) => {
    if (onSelectImage) onSelectImage(item);
    else if (onViewImage) {
      const url = item.plate_image_path ? `/${item.plate_image_path}` : (item.vehicle_image_path ? `/${item.vehicle_image_path}` : '');
      const title = `${item.vehicle_name || item.plate_number} (${item.movement_type || 'MOVEMENT'})`;
      onViewImage(url, title);
    }
  };

  const [cameraConfig, setCameraConfig] = useState({
    camera_id: 'GATE_CAMERA_01',
    camera_name: 'Main Campus Gate (Single Camera)',
    line_position_percent: 50,
    dead_zone_pixels: 20,
    enabled: true
  });

  useEffect(() => {
    fetchCameraConfig()
      .then((cfg) => {
        if (cfg) setCameraConfig(cfg);
      })
      .catch(() => {});
  }, []);

  const collegeStats = summary?.college_vehicles || { total: 0, inside: 0, outside: 0 };
  const otherStats = summary?.other_vehicles || { total: 0, inside: 0, outside: 0 };
  const todayEntries = summary?.today_entries ?? (collegeStats.inside + otherStats.inside);
  const todayExits = summary?.today_exits ?? (collegeStats.outside + otherStats.outside);
  const otherVehiclesToday = summary?.other_vehicles_today ?? (otherStats.total || otherStats.inside + otherStats.outside);

  const linePercent = cameraConfig.line_position_percent || 50;
  const isCrossingEntry = latestDetection?.movement_type === 'ENTRY';
  const isCrossingExit = latestDetection?.movement_type === 'EXIT';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }} id="live-monitoring-view">
      {/* ========================================================
          PHASE 4: ADMIN DASHBOARD SUMMARY BAR (6 CORE METRICS)
         ======================================================== */}
      <section className="dashboard-summary-bar" id="phase4-dashboard-summary">
        {/* 1. Total Registered College Vehicles */}
        <div className="summary-stat-card" style={{ borderLeft: '4px solid #38bdf8' }}>
          <div className="summary-stat-header">
            <span className="summary-stat-label">TOTAL REGISTERED FLEET</span>
            <div className="stat-icon-bullet" style={{ background: '#38bdf8' }} />
          </div>
          <div className="summary-stat-value mono" style={{ color: '#38bdf8' }}>{collegeStats.total}</div>
          <span className="summary-stat-sub">Registered College Vehicles</span>
        </div>

        {/* 2. College Vehicles INSIDE */}
        <div className="summary-stat-card gold">
          <div className="summary-stat-header">
            <span className="summary-stat-label">COLLEGE INSIDE</span>
            <div className="stat-icon-bullet gold" />
          </div>
          <div className="summary-stat-value gold mono">{collegeStats.inside}</div>
          <span className="summary-stat-sub">Fleet Vehicles on Campus</span>
        </div>

        {/* 3. College Vehicles OUTSIDE */}
        <div className="summary-stat-card gray">
          <div className="summary-stat-header">
            <span className="summary-stat-label">COLLEGE OUTSIDE</span>
            <div className="stat-icon-bullet gray" />
          </div>
          <div className="summary-stat-value gray mono">{collegeStats.outside}</div>
          <span className="summary-stat-sub">Departed / On Route</span>
        </div>

        {/* 4. Today's ENTRY Count */}
        <div className="summary-stat-card green">
          <div className="summary-stat-header">
            <span className="summary-stat-label">TODAY ENTRY</span>
            <div className="stat-icon-bullet green" />
          </div>
          <div className="summary-stat-value green mono">{todayEntries}</div>
          <span className="summary-stat-sub">Top → Down Line Crossings</span>
        </div>

        {/* 5. Today's EXIT Count */}
        <div className="summary-stat-card rose">
          <div className="summary-stat-header">
            <span className="summary-stat-label">TODAY EXIT</span>
            <div className="stat-icon-bullet rose" />
          </div>
          <div className="summary-stat-value rose mono">{todayExits}</div>
          <span className="summary-stat-sub">Down → Up Line Crossings</span>
        </div>

        {/* 6. Other Vehicles Detected Today */}
        <div className="summary-stat-card cyan">
          <div className="summary-stat-header">
            <span className="summary-stat-label">OTHER DETECTED TODAY</span>
            <div className="stat-icon-bullet cyan" />
          </div>
          <div className="summary-stat-value cyan mono">{otherVehiclesToday}</div>
          <span className="summary-stat-sub">Visitors & Campus Guests</span>
        </div>
      </section>

      {/* ========================================================
          PHASE 3: SINGLE CAMERA VIRTUAL LINE FEED + LIVE MOVEMENTS
         ======================================================== */}
      <div className="phase3-monitor-grid">
        {/* CAMERA PREVIEW WITH VIRTUAL HORIZONTAL LINE & HUD */}
        <section className="camera-feed-card" id="single-camera-view">
          <div className="camera-feed-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <div className="camera-live-beacon">
                <span className="camera-live-dot" />
                <span className="camera-live-text mono">LIVE</span>
              </div>
              <div>
                <h3 className="camera-title mono">{cameraConfig.camera_id}</h3>
                <span className="camera-subtitle">{cameraConfig.camera_name}</span>
              </div>
            </div>

            <div className="camera-hud-pills">
              <span className="hud-pill mono">
                LINE: {linePercent}%
              </span>
              <span className="hud-pill mono" style={{ color: '#10b981' }}>
                <ArrowDown size={12} style={{ display: 'inline', marginRight: 2 }} />
                ENTRY: TOP → DOWN
              </span>
              <span className="hud-pill mono" style={{ color: '#f43f5e' }}>
                <ArrowUp size={12} style={{ display: 'inline', marginRight: 2 }} />
                EXIT: DOWN → UP
              </span>
            </div>
          </div>

          {/* VIRTUAL LINE CANVAS AREA */}
          <div
            className={`virtual-line-viewport ${isCrossingEntry ? 'crossing-entry' : ''} ${isCrossingExit ? 'crossing-exit' : ''}`}
            id="camera-viewport-container"
          >
            {/* Camera feed background simulation / stream */}
            <div className="viewport-grid-bg" />

            {/* Top Zone Label */}
            <div className="viewport-zone-tag top mono">
              ZONE A: ABOVE (OUTSIDE AREA)
            </div>

            {/* Virtual Horizontal Line */}
            <div
              className={`virtual-line-divider ${isCrossingEntry ? 'active-entry' : ''} ${isCrossingExit ? 'active-exit' : ''}`}
              style={{ top: `${linePercent}%` }}
              id="virtual-horizontal-line"
            >
              <div className="virtual-line-badge mono">
                <span>ENTRY ← → EXIT</span>
                <span className="line-pos-tag">Y: {linePercent}%</span>
              </div>
            </div>

            {/* Dead zone hysteresis indicator lines */}
            <div
              className="virtual-deadzone-upper"
              style={{ top: `calc(${linePercent}% - 14px)` }}
            />
            <div
              className="virtual-deadzone-lower"
              style={{ top: `calc(${linePercent}% + 14px)` }}
            />

            {/* Bottom Zone Label */}
            <div className="viewport-zone-tag bottom mono">
              ZONE B: BELOW (CAMPUS INSIDE)
            </div>

            {/* OVERLAY: DETECTED PLATE BOUNDING BOX & METRICS */}
            {latestDetection ? (
              <div
                className={`detected-plate-box ${latestDetection.vehicle_category === 'COLLEGE_VEHICLE' ? 'college' : 'other'} ${latestDetection.movement_type === 'ENTRY' ? 'entry-state' : 'exit-state'}`}
                style={{
                  top: latestDetection.movement_type === 'ENTRY' ? '56%' : '26%',
                  left: '50%',
                  transform: 'translateX(-50%)'
                }}
              >
                <div className="plate-box-header">
                  <span className="plate-box-category mono">
                    {latestDetection.vehicle_category === 'COLLEGE_VEHICLE' ? '🚌 COLLEGE VEHICLE' : '🚗 OTHER VEHICLE'}
                  </span>
                  <span className={`plate-box-direction-badge ${latestDetection.movement_type === 'ENTRY' ? 'entry' : 'exit'}`}>
                    {latestDetection.movement_type === 'ENTRY' ? '↓ TOP → DOWN (ENTRY)' : '↑ DOWN → UP (EXIT)'}
                  </span>
                </div>

                <div className="plate-box-body">
                  <div className="plate-box-plate mono">{latestDetection.plate_number}</div>
                  {latestDetection.vehicle_name && (
                    <div className="plate-box-name">{latestDetection.vehicle_name}</div>
                  )}
                </div>

                <div className="plate-box-footer mono">
                  <span>YOLO: {Math.round((latestDetection.yolo_confidence || 0) * 100)}%</span>
                  <span className="sep">•</span>
                  <span>OCR: {Math.round((latestDetection.ocr_confidence || 0) * 100)}%</span>
                  <span className="sep">•</span>
                  <span className={`plate-box-status ${latestDetection.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                    {latestDetection.current_status}
                  </span>
                </div>
              </div>
            ) : (
              <div className="viewport-idle-message">
                <Camera size={36} color="#64748b" style={{ opacity: 0.6 }} />
                <span className="mono" style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                  AWAITING VEHICLE APPROACH AT VIRTUAL LINE...
                </span>
                <span style={{ color: '#64748b', fontSize: '0.75rem' }}>
                  Vehicles crossing line will be tracked and classified automatically
                </span>
              </div>
            )}

            {/* Bottom HUD Bar */}
            <div className="viewport-bottom-hud mono">
              <span>SINGLE CAMERA: {cameraConfig.camera_id}</span>
              <span>DEAD ZONE: ±20px</span>
              <span>COOLDOWN: 5.0s</span>
              <span>MIN TRACK: 5 FRAMES</span>
            </div>
          </div>
        </section>

        {/* ========================================================
            REQUIREMENT 19: LIVE MOVEMENTS PANEL (NEWEST FIRST)
           ======================================================== */}
        <section className="live-movements-card" id="live-movements-panel">
          <div className="live-movements-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={18} color="#06b6d4" />
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                LIVE MOVEMENTS
              </h3>
            </div>
            <span className="hud-pill mono" style={{ fontSize: '0.72rem' }}>
              {liveMovements.length} RECENTS
            </span>
          </div>

          <div className="live-movements-scroll" id="live-movements-list">
            {liveMovements.length === 0 ? (
              <div className="empty-state" style={{ padding: '2.5rem 1rem' }}>
                <Clock className="empty-state-icon" />
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No movements recorded yet today.</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Use the quick simulator above or start the live camera to record movements.
                </p>
              </div>
            ) : (
              liveMovements.map((evt) => {
                const isCollege = evt.vehicle_category === 'COLLEGE_VEHICLE';
                const isEntry = evt.movement_type === 'ENTRY';
                const timeString = new Date(evt.recognized_at || evt.created_at || Date.now()).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit'
                });

                return (
                  <div
                    key={evt.id}
                    className={`live-movement-item ${isCollege ? 'college' : 'other'} ${isEntry ? 'entry' : 'exit'}`}
                  >
                    <div className="movement-item-time mono">{timeString}</div>

                    <div className="movement-item-main">
                      <div className="movement-item-title-row">
                        <span className="movement-item-name">
                          {isCollege ? (evt.vehicle_name || 'College Vehicle') : (evt.vehicle_name || 'Unknown Vehicle')}
                        </span>
                        <span className={`movement-pill-badge ${isEntry ? 'entry' : 'exit'}`}>
                          {isEntry ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
                          <span>{evt.movement_type}</span>
                        </span>
                      </div>

                      <div className="movement-item-sub-row">
                        <span className="movement-item-plate mono">{evt.plate_number}</span>
                        <span className={`movement-item-status ${evt.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                          {evt.current_status}
                        </span>
                      </div>
                    </div>

                    <div className="movement-item-meta mono">
                      <span>OCR {Math.round((evt.ocr_confidence || 0.95) * 100)}%</span>
                      {evt.plate_image_path && (
                        <button
                          className="icon-btn-micro"
                          onClick={() => handleViewPhoto(evt)}
                          title="View capture photos"
                          type="button"
                        >
                          <Eye size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>

      {/* ========================================================
          TWO SEPARATED MONITORING CATEGORIES (PHASE 2 INTACT)
         ======================================================== */}
      <div className="monitoring-dual-grid">
        {/* CATEGORY A: REGISTERED COLLEGE VEHICLES */}
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

          <div className="stream-content-title">
            <span>Recent College Vehicle Movements</span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {collegeList.length} recorded
            </span>
          </div>

          <div className="activity-list" id="college-vehicle-activity-list">
            {collegeList.length === 0 ? (
              <div className="empty-state">
                <Bus className="empty-state-icon" />
                <p>No recent college vehicle movements recorded yet.</p>
                <p style={{ fontSize: '0.78rem' }}>Use the simulator above to test Bus 01 or Bus 02 detection.</p>
              </div>
            ) : (
              collegeList.map((item) => (
                <div key={item.id} className="activity-card" id={`college-card-${item.id}`}>
                  <div className="activity-left">
                    <div
                      className="plate-thumb-container"
                      onClick={() => handleViewPhoto(item)}
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

        {/* CATEGORY B: OTHER / UNREGISTERED VEHICLES */}
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

          <div className="stream-content-title">
            <span>Recent Other Vehicle Movements</span>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              {otherList.length} recorded
            </span>
          </div>

          <div className="activity-list" id="other-vehicle-activity-list">
            {otherList.length === 0 ? (
              <div className="empty-state">
                <Car className="empty-state-icon" />
                <p>No recent other vehicle movements recorded yet.</p>
                <p style={{ fontSize: '0.78rem' }}>Visitor plates will automatically appear here.</p>
              </div>
            ) : (
              otherList.map((item) => (
                <div key={item.id} className="activity-card" id={`other-card-${item.id}`}>
                  <div className="activity-left">
                    <div
                      className="plate-thumb-container"
                      onClick={() => handleViewPhoto(item)}
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

      {/* ========================================================
          PHASE 4: RECENT MOVEMENTS TABLE (ADMIN AUDIT LOG)
         ======================================================== */}
      <section className="stream-panel" style={{ padding: '1.25rem' }} id="admin-recent-movements-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <Activity size={20} color="#06b6d4" />
              <span>Recent Movements Table</span>
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', margin: '0.2rem 0 0' }}>
              Real-time campus transit log with plate crop and vehicle evidence preview
            </p>
          </div>
          <span className="hud-pill mono" style={{ fontSize: '0.75rem' }}>
            {(liveMovements.length > 0 ? liveMovements : (summary?.recent_movements || [])).length} RECENT MOVEMENTS
          </span>
        </div>

        <div className="table-wrapper">
          <table className="custom-table" id="dashboard-recent-movements-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Plate Number</th>
                <th>Vehicle Name</th>
                <th>Category</th>
                <th>Movement Type</th>
                <th>Current Status</th>
                <th>Camera ID</th>
                <th>Confidence</th>
                <th style={{ textAlign: 'center' }}>Image Preview</th>
              </tr>
            </thead>
            <tbody>
              {(() => {
                const list = liveMovements.length > 0 ? liveMovements : (summary?.recent_movements || []);
                if (list.length === 0) {
                  return (
                    <tr>
                      <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
                        No recent movements recorded today.
                      </td>
                    </tr>
                  );
                }
                return list.slice(0, 15).map((evt) => {
                  const isCollege = evt.vehicle_category === 'COLLEGE_VEHICLE';
                  const isEntry = evt.movement_type === 'ENTRY';
                  const dateObj = new Date(evt.recognized_at || evt.created_at || Date.now());
                  const timeFormatted = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                  const dateFormatted = dateObj.toLocaleDateString();

                  return (
                    <tr key={evt.id || `${evt.plate_number}-${evt.created_at}`} id={`recent-movement-row-${evt.id}`}>
                      {/* 1. Timestamp */}
                      <td className="mono" style={{ fontSize: '0.8rem' }}>
                        <div style={{ color: '#38bdf8' }}>{timeFormatted}</div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{dateFormatted}</div>
                      </td>

                      {/* 2. Plate Number */}
                      <td>
                        <span className="mono" style={{ fontWeight: 700, color: '#ffffff', letterSpacing: '0.04em' }}>
                          {evt.plate_number}
                        </span>
                      </td>

                      {/* 3. Vehicle Name */}
                      <td style={{ fontSize: '0.85rem', color: isCollege ? '#f8fafc' : 'var(--text-muted)' }}>
                        {isCollege ? (evt.vehicle_name || 'College Fleet') : (evt.vehicle_name || 'Guest / Visitor')}
                      </td>

                      {/* 4. Vehicle Category */}
                      <td>
                        <span className={`detection-badge-tag ${isCollege ? 'college' : 'other'}`}>
                          {isCollege ? 'COLLEGE VEHICLE' : 'OTHER VEHICLE'}
                        </span>
                      </td>

                      {/* 5. Movement Type */}
                      <td>
                        <span className={`detection-movement-pill ${isEntry ? 'entry' : 'exit'}`} style={{ padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}>
                          {isEntry ? <ArrowDownRight size={13} /> : <ArrowUpRight size={13} />}
                          <span>{evt.movement_type}</span>
                        </span>
                      </td>

                      {/* 6. Current Status */}
                      <td>
                        <span className={`badge-status ${evt.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                          {evt.current_status || 'UNKNOWN'}
                        </span>
                      </td>

                      {/* 7. Camera ID */}
                      <td className="mono" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                        {evt.camera_id || cameraConfig.camera_id || 'GATE_CAMERA_01'}
                      </td>

                      {/* 8. Confidence */}
                      <td className="mono" style={{ fontSize: '0.78rem', color: '#10b981' }}>
                        {Math.round((evt.ocr_confidence || evt.confidence || 0.95) * 100)}%
                      </td>

                      {/* 9. Image Preview */}
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                          {evt.plate_image_path ? (
                            <img
                              src={getImageUrl(evt.plate_image_path)}
                              alt="Crop"
                              style={{ width: '42px', height: '24px', objectFit: 'cover', borderRadius: '3px', border: '1px solid var(--border-subtle)', cursor: 'pointer' }}
                              onClick={() => handleViewPhoto(evt)}
                              title="Click to zoom image"
                            />
                          ) : null}
                          <button
                            className="icon-btn-micro"
                            onClick={() => handleViewPhoto(evt)}
                            title="Inspect capture evidence"
                            type="button"
                          >
                            <Eye size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                });
              })()}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
