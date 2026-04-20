import React, { useRef, useState } from 'react';
import Map, { Source, Layer, Marker, Popup } from 'react-map-gl/mapbox';
import type { MapRef } from 'react-map-gl/mapbox';
import type { FillLayer, LineLayer, CircleLayer } from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

// User provided Token
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN;

interface WaitTimeData {
    hospNameE: string;
    topWait: string;
    severity_color?: string;
    lat?: number;
    lon?: number;
}

interface MapboxViewerProps {
    geojson: any;
    facilitiesGeojson?: any;
    waitTimes: WaitTimeData[];
}

const MapboxViewer: React.FC<MapboxViewerProps> = ({ geojson, facilitiesGeojson, waitTimes }) => {
    const mapRef = useRef<MapRef>(null);
    const [popupInfo, setPopupInfo] = useState<WaitTimeData | null>(null);
    const [facilityPopupInfo, setFacilityPopupInfo] = useState<any | null>(null);

    // Initial camera position (Hong Kong)
    const [viewState, setViewState] = useState({
        longitude: 114.1694,
        latitude: 22.36,
        zoom: 10.5,
        pitch: 45,
        bearing: -17.6
    });

    // Define the heatmap layer styling based on Gap_Index (Gap values range from roughly 250 to 2100)
    const districtFillLayer: FillLayer = {
        id: 'district-fill',
        type: 'fill',
        source: 'districts',
        paint: {
            'fill-color': [
                'interpolate',
                ['linear'],
                ['get', 'Gap_Index'],
                250,  '#32D74B',   // Green: Good Coverage (Yau Tsim Mong, Central & Western)
                800,  '#A8E000',   // Light Yellow-Green
                1200, '#FFD60A',   // Yellow: Moderate Coverage
                1600, '#FF9F0A',   // Orange: Severe Shortage
                2100, '#FF453A'    // Red: Extreme Shortage (Sai Kung, Sha Tin)
            ],
            'fill-opacity': [
                'interpolate',
                ['linear'],
                ['get', 'Gap_Index'],
                250, 0.25,         // Good coverage is more transparent
                2100, 0.65         // Severe shortage is highly opaque
            ]
        }
    };

    const districtLineLayer: LineLayer = {
        id: 'district-line',
        type: 'line',
        source: 'districts',
        paint: {
            'line-color': 'rgba(255,255,255,0.2)',
            'line-width': 1
        }
    };

    const facilitiesCircleLayer: CircleLayer = {
        id: 'facilities',
        type: 'circle',
        source: 'facilities',
        paint: {
            'circle-radius': 4,
            'circle-color': '#4da6ff',
            'circle-stroke-color': '#fff',
            'circle-stroke-width': 1
        }
    };

    const handleMapClick = (evt: any) => {
        const feature = evt.features && evt.features[0];
        if (feature && feature.layer.id === 'facilities') {
            setFacilityPopupInfo({
                lon: evt.lngLat.lng,
                lat: evt.lngLat.lat,
                props: feature.properties
            });
        }
    };

    return (
        <Map
            ref={mapRef}
            {...viewState}
            onMove={evt => setViewState(evt.viewState)}
            onClick={handleMapClick}
            mapStyle="mapbox://styles/mapbox/dark-v11"
            mapboxAccessToken={MAPBOX_TOKEN}
            interactiveLayerIds={['facilities']}
            cursor={facilityPopupInfo ? 'pointer' : 'grab'}
        >
            {geojson && (
                <Source id="districts" type="geojson" data={geojson}>
                    <Layer {...districtFillLayer} />
                    <Layer {...districtLineLayer} />
                </Source>
            )}

            {facilitiesGeojson && (
                <Source id="facilities" type="geojson" data={facilitiesGeojson}>
                    <Layer {...facilitiesCircleLayer} />
                </Source>
            )}

            {/* Render HA Live Points */}
            {waitTimes.map((hosp, index) => {
                const isCritical = hosp.severity_color === 'red';
                let markerBg = 'var(--accent-green)';
                if (hosp.severity_color === 'yellow') markerBg = '#FFD60A';
                if (hosp.severity_color === 'red') markerBg = 'var(--accent-red)';
                
                if (hosp.lat && hosp.lon) {
                    return (
                        <Marker 
                            key={`marker-${index}`} 
                            longitude={hosp.lon} 
                            latitude={hosp.lat} 
                            anchor="center"
                            onClick={e => {
                                e.originalEvent.stopPropagation();
                                setFacilityPopupInfo(null);
                                setPopupInfo(hosp);
                            }}
                        >
                            <div className={isCritical ? "pulse-dot" : ""} style={{
                                width: isCritical ? 16 : 10,
                                height: isCritical ? 16 : 10,
                                borderRadius: '50%',
                                backgroundColor: markerBg,
                                border: '2px solid white',
                                cursor: 'pointer',
                                boxShadow: '0 0 10px rgba(0,0,0,0.5)'
                            }} />
                        </Marker>
                    );
                }
                return null;
            })}

            {popupInfo && (
                <Popup
                    anchor="top"
                    longitude={popupInfo.lon!}
                    latitude={popupInfo.lat!}
                    onClose={() => setPopupInfo(null)}
                    closeButton={true}
                >
                    <div style={{ padding: 4, minWidth: '150px' }}>
                        <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', fontWeight: 600 }}>{popupInfo.hospNameE}</h3>
                        <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>Current Wait Time:</p>
                        <p style={{ margin: '4px 0 0 0', fontSize: '16px', fontWeight: 700, color: popupInfo.severity_color === 'red' ? 'var(--accent-red)' : popupInfo.severity_color === 'yellow' ? '#FFD60A' : 'var(--accent-green)' }}>
                            {popupInfo.topWait || 'Unknown'}
                        </p>
                    </div>
                </Popup>
            )}

            {facilityPopupInfo && (
                <Popup
                    anchor="top"
                    longitude={facilityPopupInfo.lon}
                    latitude={facilityPopupInfo.lat}
                    onClose={() => setFacilityPopupInfo(null)}
                    closeButton={true}
                >
                    <div style={{ padding: 4, maxWidth: '280px' }}>
                        <h3 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 600 }}>{facilityPopupInfo.props.name}</h3>
                        <span style={{ display: 'inline-block', backgroundColor: 'rgba(77,166,255,0.1)', color: '#4da6ff', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', marginBottom: '8px' }}>
                            {facilityPopupInfo.props.type}
                        </span>
                        <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                            {facilityPopupInfo.props.address}
                        </p>
                    </div>
                </Popup>
            )}
        </Map>
    );
}

export default MapboxViewer;
