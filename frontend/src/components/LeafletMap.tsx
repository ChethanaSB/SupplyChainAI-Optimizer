"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Anchor, Truck } from "lucide-react";

// Fix for default marker icons in Leaflet 
const fixLeafletIcons = () => {
  // @ts-ignore
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  });
};

interface AnimatedMarkerProps {
  start: [number, number];
  end: [number, number];
  mode: string;
  speed?: number;
}

const AnimatedMarker = ({ start, end, mode, speed = 0.005 }: AnimatedMarkerProps) => {
  const [pos, setPos] = React.useState<[number, number]>(start);
  const [progress, setProgress] = React.useState(Math.random());

  useEffect(() => {
    let frame: number;
    const animate = () => {
      setProgress(prev => (prev + speed) % 1);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [speed]);

  useEffect(() => {
    const lat = start[0] + (end[0] - start[0]) * progress;
    const lng = start[1] + (end[1] - start[1]) * progress;
    setPos([lat, lng]);
  }, [progress, start, end]);

  return (
    <CircleMarker
      center={pos}
      radius={mode === "sea" ? 5 : 3}
      pathOptions={{
        color: mode === "sea" ? "#0ea5e9" : "#3b82f6",
        fillOpacity: 1,
        fillColor: mode === "sea" ? "#0ea5e9" : "#fff",
        weight: 1
      }}
    >
      <Tooltip direction="top" offset={[0, -5]} opacity={1}>
        <div className="flex items-center gap-2 px-1 py-0.5 font-bold text-[10px] bg-background text-foreground border border-border rounded shadow-sm">
          {mode === "sea" ? <Anchor size={10} /> : <Truck size={10} />}
          {mode === "sea" ? "ZF CARRIER-S4" : "ZF TRUCK-L12"}
        </div>
      </Tooltip>
    </CircleMarker>
  );
};

interface LeafletMapProps {
  data: any;
  vessels: any[];
  selectedRoute: string | null;
  simulatedMovement: boolean;
}

export default function LeafletMap({ data, vessels, selectedRoute, simulatedMovement }: LeafletMapProps) {
  useEffect(() => {
    fixLeafletIcons();
    
    // Fix for Next.js Fast Refresh throwing "Map container is already initialized"
    return () => {
         const container = L.DomUtil.get('route-map-container');
         if(container != null) {
            // @ts-ignore
            container._leaflet_id = null;
         }
    };
  }, []);

  const customIcon = new L.Icon({
    iconUrl: 'https://cdn0.iconfinder.com/data/icons/small-n-flat/24/678111-map-marker-512.png',
    iconSize: [25, 25],
    iconAnchor: [12, 25],
  });

  return (
    <MapContainer
      id="route-map-container"
      center={[20.5937, 78.9629]}
      zoom={5}
      className="h-full w-full z-0 grayscale-[0.05] contrast-[1.05]"
      zoomControl={false}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
      />

      {data.routes.map((route: any, idx: number) => {
        const start: [number, number] = [route.origin_lat, route.origin_lon];
        const end: [number, number] = [route.dest_lat, route.dest_lon];
        const isActive = selectedRoute === `${route.supplier_id}-${route.plant_id}`;

        return (
          <React.Fragment key={idx}>
            <Polyline
              positions={[start, end]}
              pathOptions={{
                color: isActive ? "#002366" : "rgba(100,116,139,0.3)",
                weight: isActive ? 4 : 2,
                dashArray: route.mode === "air" ? "5, 10" : undefined,
                opacity: isActive ? 1 : 0.4,
              }}
            >
              <Tooltip sticky>
                <div className="p-2 space-y-1">
                  <p className="text-[10px] font-black uppercase text-primary border-b border-border pb-1 mb-1">{route.supplier_id} → {route.plant_id}</p>
                  <p className="text-xs font-bold">Distance: {route.distance_km} km</p>
                  <p className="text-[10px] text-muted-foreground uppercase font-bold">Mode: {route.mode.toUpperCase()}</p>
                  <p className="text-[10px] text-emerald-500 font-bold">Cost: ₹{route.cost_inr?.toLocaleString()}</p>
                </div>
              </Tooltip>
            </Polyline>

            {simulatedMovement && (
              <AnimatedMarker
                start={start}
                end={end}
                mode={route.mode}
                speed={0.002 + Math.random() * 0.004}
              />
            )}

            {isActive && (
              <Marker position={end} icon={customIcon}>
                <Tooltip permanent direction="top">{route.plant_id}</Tooltip>
              </Marker>
            )}
          </React.Fragment>
        );
      })}

      {vessels.length === 0 && [
        { s: [15, 70], e: [19, 72] },
        { s: [10, 80], e: [13, 85] },
        { s: [5, 75], e: [8, 82] }
      ].map((v, i) => (
        <AnimatedMarker key={`v-${i}`} start={v.s as [number, number]} end={v.e as [number, number]} mode="sea" speed={0.0005} />
      ))}
    </MapContainer>
  );
}
