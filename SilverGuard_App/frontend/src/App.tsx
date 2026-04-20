import { useState, useEffect } from 'react';
import MapboxViewer from './components/MapboxViewer';
import { Activity, Clock, AlertTriangle } from 'lucide-react';

interface WaitTimeData {
    hospNameE: string;
    topWait: string;
    severity_color?: string;
    lat?: number;
    lon?: number;
}

function App() {
  const [waitTimes, setWaitTimes] = useState<WaitTimeData[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>('Loading...');
  const [districtGeojson, setDistrictGeojson] = useState<any>(null);
  const [facilitiesGeojson, setFacilitiesGeojson] = useState<any>(null);

  useEffect(() => {
    // Fetch District Heatmap GeoJSON
    fetch('/api/spatial/geojson')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setDistrictGeojson(data.data);
        }
      })
      .catch(err => console.error(err));

    // Fetch Static Medical Facilities GeoJSON
    fetch('/api/spatial/facilities')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setFacilitiesGeojson(data.data);
        }
      })
      .catch(err => console.error(err));

    // Function to fetch active Live AED wait times
    const fetchWaitTimes = () => {
      fetch('/api/live/aed_wait_times')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setWaitTimes(data.data || []);
            setLastUpdated(data.updateTime || new Date().toLocaleString());
          }
        })
        .catch(err => console.error(err));
    };

    fetchWaitTimes();
    const interval = setInterval(fetchWaitTimes, 60000); // Poll every 1 minute
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container" style={{ display: 'flex', height: '100vh', width: '100vw', margin: 0, padding: 0 }}>
      <div className="ui-layer">
        <div className="sidebar glass-panel" style={{ width: '380px', flexShrink: 0 }}>
          <div className="header">
            <h1 className="sidebar-title" style={{ fontWeight: 700, letterSpacing: '-0.5px' }}>SilverGuard</h1>
            <p className="sidebar-subtitle" style={{ fontWeight: 400, color: 'var(--text-secondary)' }}>Live Healthcare Capacity Dashboard</p>
          </div>

          <div className="divider" style={{ margin: '16px 0' }} />

          <div className="metrics-container" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div className="metric-card">
            <div className="metric-header text-gray-400 font-medium">
              <Activity size={16} /> TRACKED HOSPITALS
            </div>
            <div className="metric-value font-bold text-gray-100">{waitTimes.length}</div>
          </div>
          
          <div className="metric-card critical-card">
            <div className="metric-header font-medium">
              <AlertTriangle size={16} /> CRITICAL A&E WAIT (RED)
            </div>
            <div className="metric-value font-bold">
              {waitTimes.filter((w: any) => w.severity_color === 'red').length}
            </div>
          </div>

          <div className="metric-card update-card">
            <div className="metric-header text-gray-400 font-medium">
              <Clock size={16} /> LAST UPDATED
            </div>
            <div className="metric-value font-bold text-gray-100" style={{ fontSize: '18px' }}>
              {lastUpdated}
            </div>
          </div>
          </div>

          <div className="divider" style={{ margin: '16px 0' }} />

          <div className="legend-section">
            <h3 style={{ color: 'var(--text-tertiary)', fontWeight: 600, fontSize: '13px', textTransform: 'uppercase', marginBottom: '16px' }}>Map Legend</h3>
            <div className="legend-content">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                <div className="legend-item" style={{ margin: 0 }}>
                  <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: 'var(--accent-green)' }}></span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>A&E: Fast ( &lt; 3 hrs )</span>
                </div>
                <div className="legend-item" style={{ margin: 0 }}>
                  <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#FFD60A' }}></span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>A&E: Busy ( 3 - 5 hrs )</span>
                </div>
                <div className="legend-item" style={{ margin: 0, borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                  <span className="pulse-dot" style={{ backgroundColor: 'var(--accent-red)' }}></span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>A&E: Critical ( &gt; 5 hrs )</span>
                </div>
              </div>
              
              <div className="legend-item" style={{ marginBottom: '16px' }}>
                  <span style={{ display: 'inline-block', width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#4da6ff', border: '1px solid white' }}></span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>Registered Healthcare Facility</span>
              </div>

              <div className="legend-item" style={{ marginBottom: '8px' }}>
                  <span className="color-box" style={{ background: 'linear-gradient(90deg, #32D74B, #FF9F0A, #FF453A)' }}></span>
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>Elderly per Integrated Facility (Severity)</span>
              </div>
              <p style={{ color: 'var(--text-tertiary)', fontSize: '12px', marginTop: '8px' }}>Green: Good | Red: Severe Shortage</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="map-container" style={{ flexGrow: 1, position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 1 }}>
         <MapboxViewer geojson={districtGeojson} facilitiesGeojson={facilitiesGeojson} waitTimes={waitTimes} />
      </div>
      
      <div className="home-indicator"></div>
    </div>
  );
}

export default App;
