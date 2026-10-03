import React, { useState } from 'react';
import { PlayCircle, Bus, Car, Zap, Check } from 'lucide-react';
import { createManualRecognition } from '../services/api';

export default function DetectionSimulator({ onTriggerSuccess }) {
  const [loadingPlate, setLoadingPlate] = useState(null);
  const [customPlate, setCustomPlate] = useState('');

  const handleSimulate = async (plateNumber, customName = '') => {
    try {
      setLoadingPlate(plateNumber);
      const res = await createManualRecognition({
        plate_number: plateNumber,
        yolo_confidence: 0.88 + Math.random() * 0.08,
        ocr_confidence: 0.94 + Math.random() * 0.05,
        full_image_path: 'static/captures/demo_vehicle.jpg',
        plate_image_path: 'static/crops/demo_plate.jpg',
      });
      if (onTriggerSuccess) {
        onTriggerSuccess(res);
      }
    } catch (err) {
      console.error('Simulation error:', err);
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setLoadingPlate(null);
    }
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (!customPlate.trim()) return;
    handleSimulate(customPlate.trim().toUpperCase());
    setCustomPlate('');
  };

  return (
    <div className="simulator-strip" id="quick-simulation-strip">
      <div className="simulator-title">
        <Zap size={16} color="#f59e0b" />
        <span>Camera Trigger Simulator (Test In/Out Toggling & Classification):</span>
      </div>

      <div className="simulator-actions">
        <button
          className="sim-btn bus"
          id="sim-bus-1-btn"
          disabled={loadingPlate !== null}
          onClick={() => handleSimulate('TN45BD7321')}
          type="button"
        >
          <Bus size={14} />
          <span>{loadingPlate === 'TN45BD7321' ? 'Processing...' : 'Simulate College Bus 01 (TN45BD7321)'}</span>
        </button>

        <button
          className="sim-btn bus"
          id="sim-bus-2-btn"
          disabled={loadingPlate !== null}
          onClick={() => handleSimulate('TN45BD8456')}
          type="button"
        >
          <Bus size={14} />
          <span>{loadingPlate === 'TN45BD8456' ? 'Processing...' : 'Simulate College Bus 02 (TN45BD8456)'}</span>
        </button>

        <button
          className="sim-btn other"
          id="sim-other-1-btn"
          disabled={loadingPlate !== null}
          onClick={() => handleSimulate('TN47AB1234')}
          type="button"
        >
          <Car size={14} />
          <span>{loadingPlate === 'TN47AB1234' ? 'Processing...' : 'Simulate Other Vehicle (TN47AB1234)'}</span>
        </button>

        <form onSubmit={handleCustomSubmit} style={{ display: 'flex', gap: '0.35rem' }}>
          <input
            type="text"
            className="form-input mono"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem', width: '130px' }}
            placeholder="ANY PLATE"
            value={customPlate}
            onChange={(e) => setCustomPlate(e.target.value.toUpperCase())}
          />
          <button className="sim-btn" type="submit" disabled={!customPlate.trim() || loadingPlate !== null}>
            <PlayCircle size={14} />
            <span>Test</span>
          </button>
        </form>
      </div>
    </div>
  );
}
