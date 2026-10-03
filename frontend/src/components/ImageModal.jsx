import React from 'react';
import { X, ExternalLink } from 'lucide-react';
import { getImageUrl } from '../services/api';

export default function ImageModal({ imageInfo, onClose }) {
  if (!imageInfo) return null;

  const fullImgUrl = getImageUrl(imageInfo.full_image_path);
  const plateImgUrl = getImageUrl(imageInfo.plate_image_path);

  return (
    <div className="modal-overlay" onClick={onClose} id="image-preview-modal">
      <div className="modal-card" style={{ maxWidth: '800px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 className="modal-title">
              {imageInfo.vehicle_name ? `${imageInfo.vehicle_name} — ` : ''}
              <span className="mono">{imageInfo.plate_number}</span>
            </h3>
            <p className="nav-subtitle">
              {imageInfo.vehicle_category === 'COLLEGE_VEHICLE' ? '🚌 College Vehicle' : '🚗 Other Vehicle'} • {imageInfo.movement_type} at {new Date(imageInfo.recognized_at || imageInfo.created_at).toLocaleTimeString()}
            </p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body" style={{ gap: '1rem' }}>
          {plateImgUrl && (
            <div>
              <span className="form-label" style={{ marginBottom: '0.4rem', display: 'block' }}>
                Cropped Number Plate
              </span>
              <div style={{ background: '#000', borderRadius: '8px', padding: '0.5rem', textAlign: 'center', border: '1px solid var(--border-subtle)' }}>
                <img
                  src={plateImgUrl}
                  alt="Plate crop"
                  style={{ maxHeight: '90px', maxWidth: '100%', objectFit: 'contain' }}
                />
              </div>
            </div>
          )}

          {fullImgUrl ? (
            <div>
              <span className="form-label" style={{ marginBottom: '0.4rem', display: 'block' }}>
                Full Vehicle Camera Frame
              </span>
              <div style={{ background: '#000', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-subtle)' }}>
                <img
                  src={fullImgUrl}
                  alt="Full frame"
                  style={{ width: '100%', maxHeight: '420px', objectFit: 'contain', display: 'block' }}
                />
              </div>
            </div>
          ) : (
            <p className="empty-state" style={{ padding: '1.5rem' }}>No full vehicle capture file stored.</p>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <span>YOLO Confidence: <strong>{Math.round((imageInfo.yolo_confidence || 0) * 100)}%</strong></span>
            <span>OCR Confidence: <strong>{Math.round((imageInfo.ocr_confidence || 0) * 100)}%</strong></span>
            <span>Current Status: <strong style={{ color: imageInfo.current_status === 'INSIDE' ? '#10b981' : '#94a3b8' }}>{imageInfo.current_status}</strong></span>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
