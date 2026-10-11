import React, { useState, useEffect, useCallback, useRef } from 'react'
import Navbar from './components/Navbar'
import LiveMonitor from './components/LiveMonitor'
import CollegeVehicles from './components/CollegeVehicles'
import MovementLogs from './components/MovementLogs'
import DetectionSimulator from './components/DetectionSimulator'
import ImageModal from './components/ImageModal'
import { fetchDashboardSummary, fetchRecognitions, getWsUrl } from './services/api'

export default function App() {
  const [activeTab, setActiveTab] = useState('live')
  const [wsConnected, setWsConnected] = useState(false)
  const [summary, setSummary] = useState({
    college_vehicles: { total: 0, inside: 0, outside: 0, total_events: 0 },
    other_vehicles: { total: 0, inside: 0, outside: 0, total_events: 0 }
  })
  const [recentCollege, setRecentCollege] = useState([])
  const [recentOther, setRecentOther] = useState([])
  const [latestDetection, setLatestDetection] = useState(null)
  const [liveMovements, setLiveMovements] = useState([])
  const [selectedImage, setSelectedImage] = useState(null)
  const [toast, setToast] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => {
      setToast(null)
    }, 4500)
  }

  const loadData = useCallback(async () => {
    try {
      const summaryRes = await fetchDashboardSummary()
      if (summaryRes) {
        setSummary(summaryRes.data || summaryRes)
      }
    } catch (err) {
      console.error('Error fetching dashboard summary:', err)
    }

    try {
      const collegeRes = await fetchRecognitions({ limit: 15, category: 'COLLEGE_VEHICLE' })
      const items = Array.isArray(collegeRes) ? collegeRes : (collegeRes?.data?.items || collegeRes?.items || [])
      setRecentCollege(items)
    } catch (err) {
      console.error('Error fetching college recognitions:', err)
    }

    try {
      const otherRes = await fetchRecognitions({ limit: 15, category: 'OTHER_VEHICLE' })
      const items = Array.isArray(otherRes) ? otherRes : (otherRes?.data?.items || otherRes?.items || [])
      setRecentOther(items)
    } catch (err) {
      console.error('Error fetching other recognitions:', err)
    }

    try {
      const allRes = await fetchRecognitions({ limit: 25 })
      const items = Array.isArray(allRes) ? allRes : (allRes?.data?.items || allRes?.items || [])
      setLiveMovements(items)
    } catch (err) {
      console.error('Error fetching all live movements:', err)
    }
  }, [])

  // Initial load
  useEffect(() => {
    loadData()
  }, [loadData])

  // WebSocket connection & live streaming
  useEffect(() => {
    let isSubscribed = true

    const connectWebSocket = () => {
      const wsUrl = getWsUrl()
      console.log('Connecting to WebSocket:', wsUrl)

      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          if (!isSubscribed) return
          console.log('WebSocket connected successfully')
          setWsConnected(true)
        }

        ws.onmessage = (event) => {
          if (!isSubscribed) return
          try {
            const data = JSON.parse(event.data)

            if (data.type === 'VEHICLE_MOVEMENT' || data.type === 'recognition') {
              const rec = data.data || data
              const normalized = {
                id: rec.id || `${rec.plate_number || rec.vehicle_number}-${Date.now()}`,
                plate_number: rec.plate_number || rec.vehicle_number,
                vehicle_number: rec.plate_number || rec.vehicle_number,
                vehicle_category: rec.vehicle_category || 'OTHER_VEHICLE',
                vehicle_name: rec.vehicle_name || (rec.vehicle_category === 'COLLEGE_VEHICLE' ? 'College Fleet' : null),
                movement_type: rec.movement_type || 'ENTRY',
                current_status: rec.current_status || (rec.movement_type === 'EXIT' ? 'OUTSIDE' : 'INSIDE'),
                camera_id: rec.camera_id || 'GATE_CAMERA_01',
                yolo_confidence: rec.yolo_confidence ?? 0.85,
                ocr_confidence: rec.ocr_confidence ?? 0.95,
                recognized_at: rec.timestamp || rec.recognized_at || rec.created_at || new Date().toISOString(),
                created_at: rec.timestamp || rec.recognized_at || rec.created_at || new Date().toISOString(),
                plate_image_path: rec.plate_image_path || rec.cropped_plate_image,
                vehicle_image_path: rec.vehicle_image_path || rec.full_vehicle_image
              }

              setLatestDetection(normalized)
              setLiveMovements((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 30))

              if (normalized.vehicle_category === 'COLLEGE_VEHICLE') {
                setRecentCollege((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 20))
                showToast(
                  `🚌 ${normalized.vehicle_name || 'College Vehicle'} (${normalized.plate_number}) ${normalized.movement_type} detected! Status: ${normalized.current_status}`,
                  'success'
                )
              } else {
                setRecentOther((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 20))
                showToast(
                  `🚗 Other Vehicle (${normalized.plate_number}) ${normalized.movement_type} detected! Status: ${normalized.current_status}`,
                  'warning'
                )
              }

              // Refresh summary counters
              fetchDashboardSummary()
                .then((res) => {
                  if (res?.data) setSummary(res.data)
                  else if (res) setSummary(res)
                })
                .catch(() => {})
            }
          } catch (e) {
            console.error('Error parsing WS message:', e)
          }
        }

        ws.onclose = () => {
          if (!isSubscribed) return
          setWsConnected(false)
          console.log('WebSocket disconnected. Reconnecting in 3s...')
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000)
        }

        ws.onerror = (err) => {
          console.error('WebSocket error:', err)
          ws.close()
        }
      } catch (err) {
        console.error('WebSocket connection failed:', err)
        if (isSubscribed) {
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000)
        }
      }
    }

    connectWebSocket()

    return () => {
      isSubscribed = false
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  const handleDetectionTriggered = (newRecord) => {
    const normalized = {
      id: newRecord.id || `${newRecord.plate_number || newRecord.vehicle_number}-${Date.now()}`,
      plate_number: newRecord.plate_number || newRecord.vehicle_number,
      vehicle_number: newRecord.plate_number || newRecord.vehicle_number,
      vehicle_category: newRecord.vehicle_category || 'OTHER_VEHICLE',
      vehicle_name: newRecord.vehicle_name,
      movement_type: newRecord.movement_type || 'ENTRY',
      current_status: newRecord.current_status || (newRecord.movement_type === 'EXIT' ? 'OUTSIDE' : 'INSIDE'),
      camera_id: newRecord.camera_id || 'GATE_CAMERA_01',
      yolo_confidence: newRecord.yolo_confidence ?? 0.88,
      ocr_confidence: newRecord.ocr_confidence ?? 0.96,
      recognized_at: newRecord.recognized_at || newRecord.created_at || new Date().toISOString(),
      created_at: newRecord.recognized_at || newRecord.created_at || new Date().toISOString(),
      plate_image_path: newRecord.plate_image_path,
      vehicle_image_path: newRecord.vehicle_image_path
    }

    setLatestDetection(normalized)
    setLiveMovements((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 30))

    if (normalized.vehicle_category === 'COLLEGE_VEHICLE') {
      setRecentCollege((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 20))
      showToast(
        `🚌 ${normalized.vehicle_name || 'College Vehicle'} (${normalized.plate_number}) ${normalized.movement_type} logged`,
        'success'
      )
    } else {
      setRecentOther((prev) => [normalized, ...prev.filter((p) => p.id !== normalized.id)].slice(0, 20))
      showToast(
        `🚗 Other Vehicle (${normalized.plate_number}) ${normalized.movement_type} logged`,
        'warning'
      )
    }

    // Refresh summary
    fetchDashboardSummary().then((res) => {
      if (res?.data) setSummary(res.data)
      else if (res) setSummary(res)
    })
  }

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        wsConnected={wsConnected}
        summary={summary}
      />

      <main className="content-container">
        {activeTab === 'live' && (
          <>
            <DetectionSimulator onDetectionCreated={handleDetectionTriggered} />
            <LiveMonitor
              summary={summary}
              collegeEvents={recentCollege}
              otherEvents={recentOther}
              liveMovements={liveMovements}
              latestDetection={latestDetection}
              onSelectImage={(item) => setSelectedImage({
                url: item.plate_image_path ? `/${item.plate_image_path}` : (item.vehicle_image_path ? `/${item.vehicle_image_path}` : ''),
                title: `${item.vehicle_name || item.plate_number} (${item.movement_type || 'MOVEMENT'})`
              })}
              onViewImage={(url, title) => setSelectedImage({ url, title })}
            />
          </>
        )}

        {activeTab === 'college-vehicles' && (
          <CollegeVehicles
            showToast={showToast}
            onViewImage={(url, title) => setSelectedImage({ url, title })}
            refreshSummary={() => {
              fetchDashboardSummary()
                .then((res) => {
                  if (res?.data) setSummary(res.data)
                  else if (res) setSummary(res)
                })
                .catch(() => {})
            }}
          />
        )}

        {activeTab === 'logs' && (
          <MovementLogs
            onSelectImage={(item) => setSelectedImage({
              url: item.plate_image_path ? `/${item.plate_image_path}` : (item.vehicle_image_path ? `/${item.vehicle_image_path}` : ''),
              title: `${item.vehicle_name || item.plate_number} (${item.movement_type || 'MOVEMENT'})`
            })}
            onViewImage={(url, title) => setSelectedImage({ url, title })}
          />
        )}
      </main>

      {/* Image inspection modal */}
      {selectedImage && (
        <ImageModal
          imageUrl={selectedImage.url}
          title={selectedImage.title}
          onClose={() => setSelectedImage(null)}
        />
      )}

      {/* Floating toast notification */}
      {toast && (
        <div
          style={{
            position: 'fixed',
            bottom: '1.5rem',
            right: '1.5rem',
            backgroundColor: toast.type === 'success' ? '#065f46' : toast.type === 'warning' ? '#78350f' : '#1e293b',
            border: `1px solid ${toast.type === 'success' ? '#10b981' : toast.type === 'warning' ? '#f59e0b' : '#38bdf8'}`,
            color: '#f8fafc',
            padding: '1rem 1.25rem',
            borderRadius: '10px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.925rem',
            fontWeight: 500,
            animation: 'slideUp 0.3s ease-out'
          }}
        >
          <span>{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              marginLeft: '0.5rem',
              fontSize: '1.1rem'
            }}
          >
            &times;
          </button>
        </div>
      )}
    </div>
  )
}
