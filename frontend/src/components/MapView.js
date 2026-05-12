import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

const MapView = ({ sites, selectedSite, onSiteClick }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    if (!mapRef.current) return;

    // Initialize map
    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([19.0, 103.4], 9);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
      }).addTo(mapInstanceRef.current);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current || !sites || sites.length === 0) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    // Add new markers
    sites.forEach(site => {
      const isSelected = selectedSite?.id === site.id;
      
      const marker = L.circleMarker([site.lat, site.lon], {
        radius: isSelected ? 10 : 8,
        fillColor: getColorByVolume(site.volume),
        color: isSelected ? '#ff0000' : '#fff',
        weight: isSelected ? 3 : 2,
        opacity: 1,
        fillOpacity: isSelected ? 1 : 0.8
      });

      marker.bindPopup(`
        <div style="font-size: 13px; min-width: 200px;">
          <div style="font-weight: bold; font-size: 16px; color: #667eea; margin-bottom: 8px;">
            ${site.id}
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 12px;">
            <div>Volume:</div><div><b>${site.volume.toFixed(0)} Mm³</b></div>
            <div>Height:</div><div>${site.height} m</div>
            <div>Dam Length:</div><div>${site.damLength} m</div>
            <div>Bed Elev:</div><div>${site.bed} m</div>
            <div>Stream Order:</div><div>${site.order}</div>
            <div>Coordinates:</div><div>${site.lat.toFixed(4)}, ${site.lon.toFixed(4)}</div>
          </div>
        </div>
      `);

      marker.on('click', () => {
        if (onSiteClick) onSiteClick(site);
      });

      marker.addTo(mapInstanceRef.current);
      markersRef.current.push(marker);
    });

    // Fit bounds
    const bounds = L.latLngBounds(sites.map(s => [s.lat, s.lon]));
    mapInstanceRef.current.fitBounds(bounds.pad(0.1));
  }, [sites, selectedSite, onSiteClick]);

  // Center on selected site
  useEffect(() => {
    if (selectedSite && mapInstanceRef.current) {
      mapInstanceRef.current.setView([selectedSite.lat, selectedSite.lon], 13);
    }
  }, [selectedSite]);

  const getColorByVolume = (volume) => {
    if (volume > 2000) return '#e74c3c';
    if (volume > 1500) return '#e67e22';
    if (volume > 1000) return '#f39c12';
    if (volume > 500) return '#3498db';
    return '#9b59b6';
  };

  return (
    <div ref={mapRef} className="map-view" />
  );
};

export default MapView;
