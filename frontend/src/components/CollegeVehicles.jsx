import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Edit2,
  Trash2,
  Bus,
  Search,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Eye,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Clock,
  ArrowDownRight,
  ArrowUpRight,
  FileText,
  X,
  ShieldCheck,
  ShieldAlert,
  Car
} from 'lucide-react';
import {
  fetchCollegeVehicles,
  fetchCollegeVehicleHistory,
  createCollegeVehicle,
  updateCollegeVehicle,
  deleteCollegeVehicle,
  getImageUrl
} from '../services/api';

const VEHICLE_TYPES = [
  { value: 'ALL', label: 'All Types' },
  { value: 'BUS', label: 'Bus' },
  { value: 'VAN', label: 'Van / Minibus' },
  { value: 'CAR', label: 'Car' },
  { value: 'STAFF_VEHICLE', label: 'Staff Vehicle' },
  { value: 'OTHER', label: 'Other' },
];

export default function CollegeVehicles({ showToast, onViewImage, refreshSummary }) {
  // Vehicle list & pagination state
  const [vehicles, setVehicles] = useState([]);
  const [totalVehicles, setTotalVehicles] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [locationFilter, setLocationFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('last_movement_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Add / Edit Modal state
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [formData, setFormData] = useState({
    vehicle_number: '',
    vehicle_name: '',
    vehicle_type: 'BUS',
    description: '',
    status: 'ACTIVE',
    current_status: 'OUTSIDE',
  });
  const [formError, setFormError] = useState(null);
  const [saving, setSaving] = useState(false);

  // Details Modal state
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [vehicleHistory, setVehicleHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Safe Delete Modal state
  const [deleteModalVehicle, setDeleteModalVehicle] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  // Normalize plate number helper
  const normalizePlate = (input) => {
    return (input || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  };

  const loadVehicles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (searchTerm.trim()) params.search = searchTerm.trim();
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (typeFilter !== 'ALL') params.vehicle_type = typeFilter;
      if (locationFilter !== 'ALL') params.current_status = locationFilter;

      const res = await fetchCollegeVehicles(params);

      if (Array.isArray(res)) {
        setVehicles(res);
        setTotalVehicles(res.length);
      } else if (res && res.items) {
        setVehicles(res.items);
        setTotalVehicles(res.total ?? res.items.length);
      } else {
        setVehicles([]);
        setTotalVehicles(0);
      }
    } catch (err) {
      console.error('Failed to load college vehicles:', err);
      const msg = err.response?.data?.detail || err.message || 'Error loading vehicles';
      setError(msg);
      if (showToast) showToast(`Failed to load vehicles: ${msg}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchTerm, statusFilter, typeFilter, locationFilter, sortBy, sortOrder, showToast]);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadVehicles();
  };

  // Open Add modal
  const openAddModal = () => {
    setEditingVehicle(null);
    setFormData({
      vehicle_number: '',
      vehicle_name: '',
      vehicle_type: 'BUS',
      description: '',
      status: 'ACTIVE',
      current_status: 'OUTSIDE',
    });
    setFormError(null);
    setIsFormModalOpen(true);
  };

  // Open Edit modal
  const openEditModal = (veh) => {
    setEditingVehicle(veh);
    setFormData({
      vehicle_number: veh.vehicle_number,
      vehicle_name: veh.vehicle_name,
      vehicle_type: veh.vehicle_type || 'BUS',
      description: veh.description || '',
      status: veh.status || 'ACTIVE',
      current_status: veh.current_status || 'OUTSIDE',
    });
    setFormError(null);
    setIsFormModalOpen(true);
  };

  const closeFormModal = () => {
    setIsFormModalOpen(false);
    setEditingVehicle(null);
    setFormError(null);
  };

  // Save (Create or Update)
  const handleSave = async (e) => {
    e.preventDefault();
    const cleanPlate = normalizePlate(formData.vehicle_number);
    const cleanName = formData.vehicle_name.trim();

    if (!cleanPlate || cleanPlate.length < 4) {
      setFormError('Please enter a valid registration number (at least 4 characters).');
      return;
    }
    if (!cleanName) {
      setFormError('Please enter a vehicle name or label.');
      return;
    }

    try {
      setSaving(true);
      setFormError(null);

      if (editingVehicle) {
        await updateCollegeVehicle(editingVehicle.id, {
          vehicle_number: cleanPlate,
          vehicle_name: cleanName,
          vehicle_type: formData.vehicle_type,
          description: formData.description.trim() || null,
          status: formData.status,
          current_status: formData.current_status,
        });
        if (showToast) showToast(`Vehicle ${cleanPlate} updated successfully!`, 'success');
      } else {
        await createCollegeVehicle({
          vehicle_number: cleanPlate,
          vehicle_name: cleanName,
          vehicle_type: formData.vehicle_type,
          description: formData.description.trim() || null,
          status: formData.status,
          current_status: formData.current_status,
        });
        if (showToast) showToast(`Vehicle ${cleanPlate} registered successfully!`, 'success');
      }

      closeFormModal();
      loadVehicles();
      if (refreshSummary) refreshSummary();
    } catch (err) {
      console.error('Failed to save vehicle:', err);
      const detail = err.response?.data?.detail || err.message || 'Error saving vehicle';
      setFormError(detail);
    } finally {
      setSaving(false);
    }
  };

  // Toggle active/inactive directly from row
  const handleToggleStatus = async (veh) => {
    const nextStatus = veh.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
    try {
      await updateCollegeVehicle(veh.id, { status: nextStatus });
      if (showToast) showToast(`Vehicle ${veh.vehicle_number} set to ${nextStatus}`, 'info');
      loadVehicles();
      if (refreshSummary) refreshSummary();
    } catch (err) {
      console.error('Failed to toggle status:', err);
      const msg = err.response?.data?.detail || err.message || 'Status update failed';
      alert(`Status update failed: ${msg}`);
    }
  };

  // Open Details Modal
  const openDetailsModal = async (veh) => {
    setSelectedVehicle(veh);
    setHistoryLoading(true);
    setVehicleHistory(null);
    try {
      const historyData = await fetchCollegeVehicleHistory(veh.id, 25);
      setVehicleHistory(historyData);
    } catch (err) {
      console.error('Error fetching vehicle history:', err);
      // Fallback: minimal details
      setVehicleHistory({
        vehicle: veh,
        total_entries: 0,
        total_exits: 0,
        history: []
      });
    } finally {
      setHistoryLoading(false);
    }
  };

  const closeDetailsModal = () => {
    setSelectedVehicle(null);
    setVehicleHistory(null);
  };

  // Open Safe Delete Dialog
  const openDeleteModal = (veh) => {
    setDeleteModalVehicle(veh);
    setDeleteError(null);
  };

  const closeDeleteModal = () => {
    setDeleteModalVehicle(null);
    setDeleteError(null);
  };

  // Safe Deactivate
  const handleSafeDeactivate = async () => {
    if (!deleteModalVehicle) return;
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      await deleteCollegeVehicle(deleteModalVehicle.id, false);
      if (showToast) {
        showToast(`Vehicle ${deleteModalVehicle.vehicle_number} safely deactivated. Historical logs preserved.`, 'success');
      }
      closeDeleteModal();
      loadVehicles();
      if (refreshSummary) refreshSummary();
    } catch (err) {
      console.error('Safe deactivate error:', err);
      const msg = err.response?.data?.detail || err.message;
      setDeleteError(msg);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Hard Delete (allowed only if no history)
  const handlePermanentDelete = async () => {
    if (!deleteModalVehicle) return;
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      await deleteCollegeVehicle(deleteModalVehicle.id, true);
      if (showToast) {
        showToast(`Vehicle ${deleteModalVehicle.vehicle_number} permanently removed.`, 'success');
      }
      closeDeleteModal();
      loadVehicles();
      if (refreshSummary) refreshSummary();
    } catch (err) {
      console.error('Permanent delete error:', err);
      const msg = err.response?.data?.detail || err.message;
      setDeleteError(msg);
    } finally {
      setDeleteLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(totalVehicles / pageSize));

  return (
    <div className="master-page-container" id="college-fleet-master-page">
      {/* Header */}
      <div className="master-header-row">
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bus size={24} color="#f59e0b" />
            <span>College Vehicle Master</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Registered institutional fleet: Buses, Vans, Official Cars, and Staff Vehicles.
          </p>
        </div>

        <button
          className="btn-primary"
          id="btn-add-college-vehicle"
          onClick={openAddModal}
          type="button"
        >
          <Plus size={16} />
          <span>Add College Vehicle</span>
        </button>
      </div>

      {/* Controls: Search, Filters, Sorting */}
      <div className="master-controls" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        {/* Search */}
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '0.5rem', flex: '1 1 280px', minWidth: '240px' }}>
          <input
            type="text"
            className="search-input"
            id="search-vehicle-input"
            placeholder="Search by plate or name (e.g. TN45BD7321, Bus 01)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button className="sim-btn" type="submit" id="btn-search-vehicles">
            <Search size={15} />
            <span>Search</span>
          </button>
        </form>

        {/* Filter: Vehicle Type */}
        <select
          className="form-select"
          id="filter-type-select"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          style={{ width: '150px' }}
        >
          {VEHICLE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>

        {/* Filter: Registry Status */}
        <select
          className="form-select"
          id="filter-status-select"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          style={{ width: '140px' }}
        >
          <option value="ALL">All Status</option>
          <option value="ACTIVE">Active Only</option>
          <option value="INACTIVE">Inactive Only</option>
        </select>

        {/* Filter: Campus Location */}
        <select
          className="form-select"
          id="filter-location-select"
          value={locationFilter}
          onChange={(e) => {
            setLocationFilter(e.target.value);
            setPage(1);
          }}
          style={{ width: '140px' }}
        >
          <option value="ALL">All Location</option>
          <option value="INSIDE">Inside Campus</option>
          <option value="OUTSIDE">Outside Campus</option>
        </select>

        {/* Sort Order */}
        <select
          className="form-select"
          id="sort-vehicles-select"
          value={`${sortBy}-${sortOrder}`}
          onChange={(e) => {
            const [sb, so] = e.target.value.split('-');
            setSortBy(sb);
            setSortOrder(so);
            setPage(1);
          }}
          style={{ width: '170px' }}
        >
          <option value="last_movement_at-desc">Latest Movement ↓</option>
          <option value="last_movement_at-asc">Oldest Movement ↑</option>
          <option value="created_at-desc">Newly Registered ↓</option>
          <option value="vehicle_number-asc">Plate Number (A-Z)</option>
        </select>

        {/* Refresh */}
        <button className="icon-btn" onClick={loadVehicles} title="Refresh Table" type="button">
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
        </button>
      </div>

      {/* Error state alert */}
      {error && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '8px',
          padding: '0.85rem 1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: '#f43f5e',
          fontSize: '0.85rem'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button
            onClick={loadVehicles}
            style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: '#f43f5e', textDecoration: 'underline', cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Table */}
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
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  <RefreshCw size={20} className="spin" style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Loading registered college vehicles...
                </td>
              </tr>
            ) : vehicles.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No college vehicles match the search or filter criteria.
                </td>
              </tr>
            ) : (
              vehicles.map((v) => (
                <tr key={v.id} id={`row-vehicle-${v.id}`}>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <span style={{ fontSize: '1.2rem' }}>
                          {v.vehicle_type === 'BUS' ? '🚌' : v.vehicle_type === 'VAN' ? '🚐' : v.vehicle_type === 'CAR' ? '🚗' : v.vehicle_type === 'STAFF_VEHICLE' ? '🚙' : '🚘'}
                        </span>
                        <strong style={{ color: '#ffffff' }}>{v.vehicle_name}</strong>
                      </div>
                      {v.description && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', paddingLeft: '1.8rem' }}>
                          {v.description}
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className="mono" style={{ fontWeight: 700, color: '#fbbf24', letterSpacing: '0.04em' }}>
                      {v.vehicle_number}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {v.vehicle_type || 'OTHER'}
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
                    <div className="action-btn-group" style={{ justifyContent: 'flex-end', gap: '0.35rem' }}>
                      {/* View Details */}
                      <button
                        className="icon-btn"
                        id={`btn-details-${v.id}`}
                        onClick={() => openDetailsModal(v)}
                        title="View Vehicle Details & History"
                        type="button"
                      >
                        <Eye size={14} />
                      </button>
                      {/* Edit */}
                      <button
                        className="icon-btn"
                        id={`btn-edit-${v.id}`}
                        onClick={() => openEditModal(v)}
                        title="Edit Vehicle"
                        type="button"
                      >
                        <Edit2 size={14} />
                      </button>
                      {/* Safe Delete */}
                      <button
                        className="icon-btn delete"
                        id={`btn-delete-${v.id}`}
                        onClick={() => openDeleteModal(v)}
                        title="Delete / Deactivate Vehicle"
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

      {/* Pagination Controls */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0.75rem 0',
        fontSize: '0.85rem',
        color: 'var(--text-secondary)'
      }}>
        <span>
          Showing {vehicles.length > 0 ? (page - 1) * pageSize + 1 : 0} to {Math.min(page * pageSize, totalVehicles)} of {totalVehicles} registered vehicles
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            className="sim-btn"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            style={{ padding: '0.35rem 0.65rem' }}
          >
            <ChevronLeft size={14} />
            <span>Previous</span>
          </button>
          <span className="mono" style={{ padding: '0 0.5rem', color: '#ffffff' }}>
            Page {page} of {totalPages}
          </span>
          <button
            className="sim-btn"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            style={{ padding: '0.35rem 0.65rem' }}
          >
            <span>Next</span>
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* ========================================================
          1. ADD / EDIT MODAL DIALOG
         ======================================================== */}
      {isFormModalOpen && (
        <div className="modal-overlay" onClick={closeFormModal} id="college-vehicle-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handleSave}>
              <div className="modal-header">
                <h3 className="modal-title">
                  {editingVehicle ? 'Edit College Vehicle' : 'Register New College Vehicle'}
                </h3>
                <button
                  type="button"
                  onClick={closeFormModal}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                  <X size={18} />
                </button>
              </div>

              <div className="modal-body">
                {formError && (
                  <div style={{
                    background: 'rgba(244, 63, 94, 0.1)',
                    border: '1px solid rgba(244, 63, 94, 0.3)',
                    borderRadius: '6px',
                    padding: '0.65rem 0.85rem',
                    marginBottom: '1rem',
                    color: '#f43f5e',
                    fontSize: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}>
                    <AlertTriangle size={15} />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label" htmlFor="input-vehicle-number">
                    Registration Number (Plate) *
                  </label>
                  <input
                    id="input-vehicle-number"
                    type="text"
                    className="form-input mono"
                    placeholder="e.g. TN45BD7321"
                    value={formData.vehicle_number}
                    onChange={(e) => setFormData({ ...formData, vehicle_number: normalizePlate(e.target.value) })}
                    required
                  />
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Uppercase alphanumeric Indian registration format (auto-normalized).
                  </span>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="input-vehicle-name">
                    Vehicle Display Name / Identifier *
                  </label>
                  <input
                    id="input-vehicle-name"
                    type="text"
                    className="form-input"
                    placeholder="e.g. College Bus 01, Staff Van, Campus Patrol"
                    value={formData.vehicle_name}
                    onChange={(e) => setFormData({ ...formData, vehicle_name: e.target.value })}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="select-vehicle-type">
                    Vehicle Type *
                  </label>
                  <select
                    id="select-vehicle-type"
                    className="form-select"
                    value={formData.vehicle_type}
                    onChange={(e) => setFormData({ ...formData, vehicle_type: e.target.value })}
                  >
                    <option value="BUS">🚌 Bus</option>
                    <option value="VAN">🚐 Van / Minibus</option>
                    <option value="CAR">🚗 Official Car</option>
                    <option value="STAFF_VEHICLE">🚙 Staff Vehicle</option>
                    <option value="OTHER">🚘 Other Institutional</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="input-vehicle-desc">
                    Description / Route Details (Optional)
                  </label>
                  <textarea
                    id="input-vehicle-desc"
                    className="form-input"
                    rows={2}
                    placeholder="e.g. Route 12 - Airport via Main Bypass. Assigned driver: R. Kumar."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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

                  <div className="form-group">
                    <label className="form-label" htmlFor="select-current-status">
                      Campus Location
                    </label>
                    <select
                      id="select-current-status"
                      className="form-select"
                      value={formData.current_status}
                      onChange={(e) => setFormData({ ...formData, current_status: e.target.value })}
                    >
                      <option value="OUTSIDE">OUTSIDE (Off Campus)</option>
                      <option value="INSIDE">INSIDE (On Campus)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={closeFormModal} disabled={saving}>
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

      {/* ========================================================
          2. VEHICLE DETAILS MODAL (REQUIREMENT 5)
         ======================================================== */}
      {selectedVehicle && (
        <div className="modal-overlay" onClick={closeDetailsModal} id="vehicle-details-modal">
          <div
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '780px', width: '92%' }}
          >
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <span style={{ fontSize: '1.4rem' }}>
                  {selectedVehicle.vehicle_type === 'BUS' ? '🚌' : selectedVehicle.vehicle_type === 'VAN' ? '🚐' : '🚗'}
                </span>
                <div>
                  <h3 className="modal-title" style={{ margin: 0 }}>
                    {selectedVehicle.vehicle_name}
                  </h3>
                  <span className="mono" style={{ fontSize: '0.85rem', color: '#fbbf24', fontWeight: 700 }}>
                    {selectedVehicle.vehicle_number}
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={closeDetailsModal}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <div className="modal-body" style={{ maxHeight: '72vh', overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
              {/* Top Summary Stat Grid */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: '0.75rem',
                marginBottom: '1.25rem'
              }}>
                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>Type</span>
                  <strong style={{ color: '#ffffff', fontSize: '0.9rem' }}>{selectedVehicle.vehicle_type || 'OTHER'}</strong>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>Location Status</span>
                  <span className={`badge-status ${selectedVehicle.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                    {selectedVehicle.current_status || 'OUTSIDE'}
                  </span>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>Registry Status</span>
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: selectedVehicle.status === 'ACTIVE' ? '#10b981' : '#64748b' }}>
                    {selectedVehicle.status}
                  </span>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>Total Entries</span>
                  <strong className="mono" style={{ color: '#10b981', fontSize: '1.1rem' }}>
                    {vehicleHistory?.total_entries ?? 0}
                  </strong>
                </div>

                <div style={{ background: 'var(--bg-surface)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block' }}>Total Exits</span>
                  <strong className="mono" style={{ color: '#f43f5e', fontSize: '1.1rem' }}>
                    {vehicleHistory?.total_exits ?? 0}
                  </strong>
                </div>
              </div>

              {/* Description & Metadata */}
              <div style={{
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                marginBottom: '1.25rem',
                fontSize: '0.82rem',
                color: 'var(--text-secondary)'
              }}>
                <div style={{ marginBottom: '0.4rem' }}>
                  <strong style={{ color: '#ffffff' }}>Description: </strong>
                  <span>{selectedVehicle.description || 'No description provided.'}</span>
                </div>
                <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.78rem' }}>
                  <span>Created: {new Date(selectedVehicle.created_at || Date.now()).toLocaleDateString()}</span>
                  <span>Last Moved: {selectedVehicle.last_movement_at ? new Date(selectedVehicle.last_movement_at).toLocaleString() : 'Never'}</span>
                </div>
              </div>

              {/* Movement History & Image Evidence Table */}
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Clock size={16} color="#06b6d4" />
                <span>Recent Movement History & Photographic Evidence</span>
              </h4>

              {historyLoading ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  <RefreshCw size={18} className="spin" style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Loading vehicle movement history...
                </div>
              ) : !vehicleHistory || !vehicleHistory.history || vehicleHistory.history.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', background: 'var(--bg-surface)', borderRadius: '8px' }}>
                  No movement history recorded yet for this vehicle.
                </div>
              ) : (
                <div className="table-wrapper" style={{ maxHeight: '320px', overflowY: 'auto' }}>
                  <table className="custom-table" style={{ fontSize: '0.82rem' }}>
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>Movement</th>
                        <th>State</th>
                        <th>Camera</th>
                        <th>Conf (Y/OCR)</th>
                        <th>Plate Crop</th>
                        <th>Full Vehicle Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {vehicleHistory.history.map((h) => (
                        <tr key={h.id}>
                          <td className="mono" style={{ whiteSpace: 'nowrap' }}>
                            {new Date(h.recognized_at || h.created_at).toLocaleString()}
                          </td>
                          <td>
                            <span className={`badge-movement ${h.movement_type === 'ENTRY' ? 'entry' : 'exit'}`}>
                              {h.movement_type}
                            </span>
                          </td>
                          <td>
                            <span className={`badge-status ${h.current_status === 'INSIDE' ? 'inside' : 'outside'}`}>
                              {h.current_status}
                            </span>
                          </td>
                          <td className="mono">{h.camera_id || 'GATE_01'}</td>
                          <td className="mono">
                            {Math.round((h.yolo_confidence || 0) * 100)}% / {Math.round((h.ocr_confidence || 0) * 100)}%
                          </td>
                          <td>
                            {h.plate_image_path ? (
                              <button
                                type="button"
                                onClick={() => onViewImage && onViewImage(`/${h.plate_image_path}`, `Cropped Plate: ${selectedVehicle.vehicle_number}`)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  padding: 0
                                }}
                                title="Click to view crop image"
                              >
                                <img
                                  src={getImageUrl(h.plate_image_path)}
                                  alt="Crop"
                                  style={{ height: '24px', width: '56px', objectFit: 'contain', borderRadius: '3px', background: '#000' }}
                                />
                              </button>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>-</span>
                            )}
                          </td>
                          <td>
                            {h.vehicle_image_path ? (
                              <button
                                type="button"
                                onClick={() => onViewImage && onViewImage(`/${h.vehicle_image_path}`, `Vehicle Evidence: ${selectedVehicle.vehicle_number} (${h.movement_type})`)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  cursor: 'pointer',
                                  padding: 0
                                }}
                                title="Click to view full image"
                              >
                                <img
                                  src={getImageUrl(h.vehicle_image_path)}
                                  alt="Full Vehicle"
                                  style={{ height: '28px', width: '48px', objectFit: 'cover', borderRadius: '3px' }}
                                />
                              </button>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-primary" onClick={closeDetailsModal}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          3. SAFE DELETE CONFIRMATION MODAL (REQUIREMENT 3)
         ======================================================== */}
      {deleteModalVehicle && (
        <div className="modal-overlay" onClick={closeDeleteModal} id="safe-delete-modal">
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="modal-header" style={{ borderBottomColor: 'rgba(244, 63, 94, 0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <ShieldAlert size={20} color="#f43f5e" />
                <h3 className="modal-title" style={{ color: '#f43f5e' }}>
                  Confirm Vehicle Removal
                </h3>
              </div>
              <button
                type="button"
                onClick={closeDeleteModal}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              {deleteError && (
                <div style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  marginBottom: '1rem',
                  color: '#f43f5e',
                  fontSize: '0.82rem'
                }}>
                  {deleteError}
                </div>
              )}

              <p style={{ color: '#ffffff', fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                Are you sure you want to remove <strong>{deleteModalVehicle.vehicle_name}</strong> (
                <span className="mono" style={{ color: '#fbbf24' }}>{deleteModalVehicle.vehicle_number}</span>)?
              </p>

              <div style={{
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '0.85rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                marginBottom: '1rem'
              }}>
                <strong style={{ color: '#f59e0b', display: 'block', marginBottom: '0.3rem' }}>
                  Safety Guard Active:
                </strong>
                To protect historical audit logs and entry/exit movement records:
                <ul style={{ margin: '0.3rem 0 0 1.2rem', padding: 0 }}>
                  <li><strong>Deactivate (Recommended):</strong> Sets vehicle to INACTIVE. No historical recognition events are destroyed.</li>
                  <li><strong>Permanent Delete:</strong> Allowed only if the vehicle has ZERO recognition events.</li>
                </ul>
              </div>
            </div>

            <div className="modal-footer" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={closeDeleteModal}
                disabled={deleteLoading}
              >
                Cancel
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={handleSafeDeactivate}
                disabled={deleteLoading}
                style={{ background: '#334155', color: '#ffffff' }}
              >
                {deleteLoading ? 'Processing...' : 'Deactivate Vehicle (Safe)'}
              </button>

              <button
                type="button"
                className="icon-btn delete"
                onClick={handlePermanentDelete}
                disabled={deleteLoading}
                style={{
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.4)',
                  color: '#f43f5e',
                  padding: '0.5rem 0.85rem',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem'
                }}
              >
                <Trash2 size={14} />
                <span>Permanent Delete</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
