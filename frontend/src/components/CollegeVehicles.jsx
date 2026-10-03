import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Bus, Search, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import {
  fetchCollegeVehicles,
  createCollegeVehicle,
  updateCollegeVehicle,
  deleteCollegeVehicle,
} from '../services/api';

export default function CollegeVehicles({ showToast }) {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [formData, setFormData] = useState({
    vehicle_number: '',
    vehicle_name: '',
    vehicle_type: 'BUS',
    status: 'ACTIVE',
  });
  const [saving, setSaving] = useState(false);

  const loadVehicles = async () => {
    try {
      setLoading(true);
      const data = await fetchCollegeVehicles(statusFilter || null, searchTerm || '');
      setVehicles(data);
    } catch (err) {
      console.error(err);
      if (showToast) showToast(`Failed to load vehicles: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVehicles();
  }, [statusFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadVehicles();
  };

  const openAddModal = () => {
    setEditingVehicle(null);
    setFormData({
      vehicle_number: '',
      vehicle_name: '',
      vehicle_type: 'BUS',
      status: 'ACTIVE',
    });
    setIsModalOpen(true);
  };

  const openEditModal = (veh) => {
    setEditingVehicle(veh);
    setFormData({
      vehicle_number: veh.vehicle_number,
      vehicle_name: veh.vehicle_name,
      vehicle_type: veh.vehicle_type,
      status: veh.status,
    });
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingVehicle(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formData.vehicle_number.trim() || !formData.vehicle_name.trim()) {
      alert('Please provide both Vehicle Number and Name');
      return;
    }

    try {
      setSaving(true);
      if (editingVehicle) {
        await updateCollegeVehicle(editingVehicle.id, {
          vehicle_name: formData.vehicle_name.trim(),
          vehicle_type: formData.vehicle_type,
          status: formData.status,
        });
        if (showToast) showToast('College vehicle updated successfully!', 'success');
      } else {
        await createCollegeVehicle({
          vehicle_number: formData.vehicle_number.trim().toUpperCase(),
          vehicle_name: formData.vehicle_name.trim(),
          vehicle_type: formData.vehicle_type,
          status: formData.status,
        });
        if (showToast) showToast('New college vehicle added to registry!', 'success');
      }
      closeModal();
      loadVehicles();
    } catch (err) {
      console.error(err);
      alert(`Save failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id, name, plate) => {
    if (!window.confirm(`Are you sure you want to remove "${name}" (${plate}) from College Registry?`)) {
      return;
    }
    try {
      await deleteCollegeVehicle(id);
      if (showToast) showToast(`Vehicle ${plate} removed from college list`, 'success');
      loadVehicles();
    } catch (err) {
      console.error(err);
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handleToggleStatus = async (veh) => {
    const nextStatus = veh.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCollegeVehicle(veh.id, { status: nextStatus });
      if (showToast) showToast(`Vehicle set to ${nextStatus}`, 'success');
      loadVehicles();
    } catch (err) {
      console.error(err);
      alert(`Status update failed: ${err.message}`);
    }
  };

  return (
    <div className="master-page-container" id="college-fleet-master-page">
      <div className="master-header-row">
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bus size={24} color="#f59e0b" />
            <span>College Vehicle Registry</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Predefined list of recognized college buses, ambulances, staff vans, and institutional vehicles
          </p>
        </div>

        <button className="btn-primary" id="btn-add-college-vehicle" onClick={openAddModal} type="button">
          <Plus size={16} />
          <span>Add College Vehicle</span>
        </button>
      </div>

      <div className="master-controls">
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', flex: 1, maxWidth: '420px' }}>
          <input
            type="text"
            className="search-input"
            id="search-vehicle-input"
            placeholder="Search by plate or name (e.g. TN45BD7321)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="sim-btn" type="submit" id="btn-search-vehicles">
            <Search size={15} />
            <span>Search</span>
          </button>
        </form>

        <select
          className="form-select"
          id="filter-status-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ width: '160px' }}
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active Only</option>
          <option value="INACTIVE">Inactive Only</option>
        </select>

        <button className="icon-btn" onClick={loadVehicles} title="Refresh Table" type="button">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
        </button>
      </div>

      <div className="table-wrapper">
        <table className="custom-table" id="college-vehicles-table">
          <thead>
            <tr>
              <th>Vehicle Name</th>
              <th>Number Plate</th>
              <th>Type</th>
              <th>Campus State</th>
              <th>Registry Status</th>
              <th>Last Movement</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {vehicles.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  {loading ? 'Loading registered vehicles...' : 'No college vehicles found matching criteria.'}
                </td>
              </tr>
            ) : (
              vehicles.map((v) => (
                <tr key={v.id} id={`row-vehicle-${v.id}`}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span style={{ fontSize: '1.2rem' }}>
                        {v.vehicle_type === 'BUS' ? '🚌' : v.vehicle_type === 'VAN' ? '🚐' : '🚗'}
                      </span>
                      <strong style={{ color: '#ffffff' }}>{v.vehicle_name}</strong>
                    </div>
                  </td>
                  <td>
                    <span className="mono" style={{ fontWeight: 700, color: '#fbbf24', letterSpacing: '0.04em' }}>
                      {v.vehicle_number}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {v.vehicle_type}
                    </span>
                  </td>
                  <td>
                    <span className={`badge-status ${v.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                      {v.current_status || 'OUTSIDE'}
                    </span>
                  </td>
                  <td>
                    <button
                      onClick={() => handleToggleStatus(v)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        color: v.status === 'ACTIVE' ? '#10b981' : '#64748b',
                      }}
                      title="Click to toggle Active/Inactive"
                    >
                      {v.status === 'ACTIVE' ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
                      <span>{v.status}</span>
                    </button>
                  </td>
                  <td className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {v.last_movement_at ? new Date(v.last_movement_at).toLocaleString() : 'Never'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div className="action-btn-group" style={{ justifyContent: 'flex-end' }}>
                      <button
                        className="icon-btn"
                        id={`btn-edit-${v.id}`}
                        onClick={() => openEditModal(v)}
                        title="Edit Vehicle"
                        type="button"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        className="icon-btn delete"
                        id={`btn-delete-${v.id}`}
                        onClick={() => handleDelete(v.id, v.vehicle_name, v.vehicle_number)}
                        title="Delete Vehicle"
                        type="button"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ADD / EDIT MODAL DIALOG */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={closeModal} id="college-vehicle-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSave}>
              <div className="modal-header">
                <h3 className="modal-title">
                  {editingVehicle ? 'Edit College Vehicle' : 'Register New College Vehicle'}
                </h3>
              </div>

              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label" htmlFor="input-vehicle-number">
                    Vehicle Number Plate (Indian Format)
                  </label>
                  <input
                    id="input-vehicle-number"
                    type="text"
                    className="form-input mono"
                    placeholder="e.g. TN45BD7321"
                    disabled={!!editingVehicle}
                    value={formData.vehicle_number}
                    onChange={(e) => setFormData({ ...formData, vehicle_number: e.target.value.toUpperCase() })}
                    required
                  />
                  {!editingVehicle && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Standard state code + district + series + digits (e.g. TN45BD7321)
                    </span>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="input-vehicle-name">
                    Vehicle Display Name / Label
                  </label>
                  <input
                    id="input-vehicle-name"
                    type="text"
                    className="form-input"
                    placeholder="e.g. College Bus 01, Staff Van, Ambulance"
                    value={formData.vehicle_name}
                    onChange={(e) => setFormData({ ...formData, vehicle_name: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="select-vehicle-type">
                    Vehicle Type
                  </label>
                  <select
                    id="select-vehicle-type"
                    className="form-select"
                    value={formData.vehicle_type}
                    onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                  >
                    <option value="BUS">🚌 Bus</option>
                    <option value="VAN">🚐 Van / Minibus</option>
                    <option value="CAR">🚗 Staff Car / Official</option>
                    <option value="AMBULANCE">🚑 Ambulance / Emergency</option>
                    <option value="TRUCK">🚛 Campus Truck</option>
                    <option value="OTHER">Other Institutional</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="select-vehicle-status">
                    Registry Status
                  </label>
                  <select
                    id="select-vehicle-status"
                    className="form-select"
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  >
                    <option value="ACTIVE">ACTIVE (Monitored)</option>
                    <option value="INACTIVE">INACTIVE (Decommissioned)</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeModal} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" id="btn-save-vehicle" disabled={saving}>
                  {saving ? 'Saving...' : editingVehicle ? 'Update Vehicle' : 'Register Vehicle'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
