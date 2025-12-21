// RotMG Realm Map Editor - Main JavaScript

// Configuration
const CONFIG = {
    // Game coordinate bounds
    gameBounds: {
        minX: 283,
        maxX: 2048,
        minY: 130,
        maxY: 1871
    },
    // Image dimensions
    imageDimensions: {
        width: 1801,
        height: 1872
    },
    // Map image path (relative to server)
    mapImagePath: 'realm_map.png',
    offsetX: 14, // global X offset to align map image with game coords
    // API endpoints
    api: {
        biomes: '/api/biomes',
        export: '/api/export'
    }
};

// State
const state = {
    patrolPoints: [],
    biomeData: null,
    beaconData: [],
    map: null,
    markers: [],
    biomePolygons: [],
    beaconMarkers: [],
    gridLayer: null,
    selectedBiome: 'all'
};

// Initialize map
function initMap() {
    // Calculate bounds for coordinate transformation
    const bounds = [
        [0, 0],
        [CONFIG.imageDimensions.height, CONFIG.imageDimensions.width]
    ];

    // Create map with CRS.Simple (pixel coordinates)
    state.map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: -2,
        maxZoom: 2,
        zoomSnap: 0.1,
        zoomDelta: 0.5
    });

    // Add map image overlay
    L.imageOverlay(CONFIG.mapImagePath, bounds).addTo(state.map);

    // Fit map to bounds
    state.map.fitBounds(bounds);

    // Add click event for adding patrol points
    state.map.on('click', onMapClick);

    // Add mouse move event for coordinate display
    state.map.on('mousemove', onMouseMove);

    // Prevent context menu on map
    state.map.getContainer().addEventListener('contextmenu', (e) => {
        e.preventDefault();
    });
}

// Coordinate transformation: Game coords to pixel coords
function gameToPixel(gameX, gameY) {
    const { minX, maxX, minY, maxY } = CONFIG.gameBounds;
    const { width, height } = CONFIG.imageDimensions;

    const pixelX = (((gameX + CONFIG.offsetX) - minX) / (maxX - minX)) * width;
    // Invert Y to match realm_map.html calibration (game Y increases upward)
    const pixelY = height - ((gameY - minY) / (maxY - minY)) * height;

    return [pixelY, pixelX]; // Leaflet uses [lat, lng] which is [y, x]
}

// Coordinate transformation: Pixel coords to game coords
function pixelToGame(pixelY, pixelX) {
    const { minX, maxX, minY, maxY } = CONFIG.gameBounds;
    const { width, height } = CONFIG.imageDimensions;

    const gameX = Math.round((pixelX / width) * (maxX - minX) + minX - CONFIG.offsetX);
    const gameY = Math.round(((height - pixelY) / height) * (maxY - minY) + minY);

    return { x: gameX, y: gameY };
}

// Handle map click - add patrol point
function onMapClick(e) {
    const pixelCoords = [e.latlng.lat, e.latlng.lng];
    const gameCoords = pixelToGame(pixelCoords[0], pixelCoords[1]);

    addPatrolPoint(gameCoords.x, gameCoords.y);
    updateStatus(`Added patrol point at (${gameCoords.x}, ${gameCoords.y})`);
}

// Handle mouse move - update coordinate display
function onMouseMove(e) {
    const pixelCoords = [e.latlng.lat, e.latlng.lng];
    const gameCoords = pixelToGame(pixelCoords[0], pixelCoords[1]);

    document.getElementById('mouse-coords').textContent =
        `Game Coords: ${gameCoords.x}, ${gameCoords.y}`;
}

// Add patrol point
function addPatrolPoint(x, y) {
    const point = { x, y };
    state.patrolPoints.push(point);

    // Create marker
    const pixelCoords = gameToPixel(x, y);
    const marker = L.circleMarker(pixelCoords, {
        radius: 8,
        fillColor: '#3b82f6',
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
        draggable: true
    }).addTo(state.map);

    // Add tooltip
    marker.bindTooltip(`Point ${state.patrolPoints.length}<br>(${x}, ${y})`, {
        permanent: false,
        direction: 'top'
    });

    // Handle drag
    marker.on('dragend', function(e) {
        const newPixelCoords = [e.target.getLatLng().lat, e.target.getLatLng().lng];
        const newGameCoords = pixelToGame(newPixelCoords[0], newPixelCoords[1]);

        const index = state.markers.indexOf(marker);
        state.patrolPoints[index] = { x: newGameCoords.x, y: newGameCoords.y };

        marker.setTooltipContent(`Point ${index + 1}<br>(${newGameCoords.x}, ${newGameCoords.y})`);
        updatePointList();
        updateStatus(`Moved point ${index + 1} to (${newGameCoords.x}, ${newGameCoords.y})`);
    });

    // Handle right-click for deletion
    marker.on('contextmenu', function(e) {
        L.DomEvent.stopPropagation(e);
        const index = state.markers.indexOf(marker);
        deletePatrolPoint(index);
    });

    state.markers.push(marker);
    updatePointList();
    updatePointCount();
}

// Delete patrol point
function deletePatrolPoint(index) {
    if (index >= 0 && index < state.patrolPoints.length) {
        state.patrolPoints.splice(index, 1);
        state.map.removeLayer(state.markers[index]);
        state.markers.splice(index, 1);

        // Update all tooltips with new indices
        state.markers.forEach((marker, i) => {
            const point = state.patrolPoints[i];
            marker.setTooltipContent(`Point ${i + 1}<br>(${point.x}, ${point.y})`);
        });

        updatePointList();
        updatePointCount();
        updateStatus(`Deleted patrol point ${index + 1}`);
    }
}

// Clear all patrol points
function clearAllPoints() {
    if (state.patrolPoints.length === 0) {
        updateStatus('No points to clear');
        return;
    }

    if (!confirm(`Delete all ${state.patrolPoints.length} patrol points?`)) {
        return;
    }

    state.markers.forEach(marker => state.map.removeLayer(marker));
    state.markers = [];
    state.patrolPoints = [];

    updatePointList();
    updatePointCount();
    updateStatus('Cleared all patrol points');
}

// Update point list UI
function updatePointList() {
    const pointList = document.getElementById('point-list');

    if (state.patrolPoints.length === 0) {
        pointList.innerHTML = '<p class="empty-message">No points added. Click on map to add.</p>';
        return;
    }

    pointList.innerHTML = state.patrolPoints.map((point, index) => `
        <div class="point-item">
            <div class="point-info">
                <div class="point-index">Point ${index + 1}</div>
                <div class="point-coords">(${point.x}, ${point.y})</div>
            </div>
            <div class="point-actions">
                <button class="btn-small" onclick="deletePatrolPoint(${index})">Delete</button>
            </div>
        </div>
    `).join('');
}

// Update point count
function updatePointCount() {
    document.getElementById('point-count').textContent =
        `Points: ${state.patrolPoints.length}`;
}

// Update status message
function updateStatus(message) {
    document.getElementById('status-message').textContent = message;
}

// Export patrol points as JSON
async function exportPatrolPoints() {
    if (state.patrolPoints.length === 0) {
        updateStatus('No points to export');
        alert('No patrol points to export');
        return;
    }

    const exportData = {
        points: state.patrolPoints,
        count: state.patrolPoints.length,
        timestamp: new Date().toISOString(),
        bounds: CONFIG.gameBounds
    };

    try {
        const response = await fetch(CONFIG.api.export, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(exportData)
        });

        if (response.ok) {
            const result = await response.json();
            updateStatus(`Exported ${state.patrolPoints.length} points to ${result.filename}`);
            alert(`Successfully exported to ${result.filename}`);
        } else {
            throw new Error('Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        // Fallback: download as file
        downloadJSON(exportData, 'patrol_points.json');
        updateStatus('Exported patrol points (client-side download)');
    }
}

// Download JSON file (client-side fallback)
function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Import patrol points from JSON
function importPatrolPoints() {
    document.getElementById('file-input').click();
}

// Handle file selection
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);

            // Validate data
            if (!data.points || !Array.isArray(data.points)) {
                throw new Error('Invalid JSON format: missing points array');
            }

            // Clear existing points
            clearAllPoints();

            // Add imported points
            data.points.forEach(point => {
                if (point.x !== undefined && point.y !== undefined) {
                    addPatrolPoint(point.x, point.y);
                }
            });

            updateStatus(`Imported ${data.points.length} patrol points`);
            alert(`Successfully imported ${data.points.length} points`);
        } catch (error) {
            console.error('Import error:', error);
            alert('Failed to import JSON: ' + error.message);
            updateStatus('Import failed');
        }
    };
    reader.readAsText(file);

    // Reset input
    event.target.value = '';
}

// Load biome data from server
async function loadBiomeData() {
    try {
        const response = await fetch(CONFIG.api.biomes);
        if (!response.ok) {
            throw new Error('Failed to load biome data');
        }

        state.biomeData = await response.json();
        populateBiomeSelector();
        drawBiomeBounds();
        loadBeaconData();
        updateStatus('Loaded biome data');
    } catch (error) {
        console.error('Error loading biome data:', error);
        updateStatus('Failed to load biome data (optional)');
    }
}

// Populate biome selector dropdown
function populateBiomeSelector() {
    if (!state.biomeData || !state.biomeData.biomes) return;

    const selector = document.getElementById('biome-selector');
    const biomes = Object.keys(state.biomeData.biomes);

    biomes.forEach(biomeName => {
        const option = document.createElement('option');
        option.value = biomeName;
        option.textContent = biomeName;
        selector.appendChild(option);
    });
}

// Draw biome bounds as polygons
function drawBiomeBounds() {
    if (!state.biomeData || !state.biomeData.biomes) return;

    // Clear existing polygons
    state.biomePolygons.forEach(polygon => state.map.removeLayer(polygon));
    state.biomePolygons = [];

    const biomes = state.biomeData.biomes;

    Object.entries(biomes).forEach(([biomeName, biome]) => {
        if (!biome.bounds) return;

        // Convert game coords to pixel coords
        const corners = [
            gameToPixel(biome.bounds.minX, biome.bounds.minY),
            gameToPixel(biome.bounds.minX, biome.bounds.maxY),
            gameToPixel(biome.bounds.maxX, biome.bounds.maxY),
            gameToPixel(biome.bounds.maxX, biome.bounds.minY)
        ];

        // Random color for each biome
        const color = getRandomColor();

        const polygon = L.polygon(corners, {
            color: color,
            fillColor: color,
            fillOpacity: 0.1,
            weight: 2,
            opacity: 0.5
        }).addTo(state.map);

        polygon.bindTooltip(biomeName, { permanent: false, direction: 'center' });
        polygon.biome = biomeName;

        state.biomePolygons.push(polygon);
    });
}

// Load beacon data
function loadBeaconData() {
    if (!state.biomeData || !state.biomeData.beacons) return;

    state.beaconData = state.biomeData.beacons;
    drawBeacons();
}

// Draw beacons on map
function drawBeacons() {
    // Clear existing beacons
    state.beaconMarkers.forEach(marker => state.map.removeLayer(marker));
    state.beaconMarkers = [];

    if (!state.beaconData || state.beaconData.length === 0) return;

    state.beaconData.forEach(beacon => {
        const pixelCoords = gameToPixel(beacon.x, beacon.y);

        const marker = L.circleMarker(pixelCoords, {
            radius: 6,
            fillColor: '#fbbf24',
            color: '#f59e0b',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9
        }).addTo(state.map);

        marker.bindTooltip(`Beacon: ${beacon.name || 'Unknown'}<br>(${beacon.x}, ${beacon.y})`, {
            permanent: false,
            direction: 'top'
        });

        state.beaconMarkers.push(marker);
    });
}

// Get random color for biome polygons
function getRandomColor() {
    const colors = [
        '#ef4444', '#f59e0b', '#10b981', '#3b82f6',
        '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Toggle biome bounds visibility
function toggleBiomeBounds(show) {
    state.biomePolygons.forEach(polygon => {
        if (show) {
            if (!state.map.hasLayer(polygon)) {
                polygon.addTo(state.map);
            }

            // Apply filter if specific biome selected
            if (state.selectedBiome !== 'all') {
                if (polygon.biome === state.selectedBiome) {
                    polygon.setStyle({ opacity: 0.8, fillOpacity: 0.3 });
                } else {
                    polygon.setStyle({ opacity: 0.1, fillOpacity: 0.05 });
                }
            } else {
                polygon.setStyle({ opacity: 0.5, fillOpacity: 0.1 });
            }
        } else {
            state.map.removeLayer(polygon);
        }
    });
}

// Toggle beacon visibility
function toggleBeacons(show) {
    state.beaconMarkers.forEach(marker => {
        if (show) {
            if (!state.map.hasLayer(marker)) {
                marker.addTo(state.map);
            }
        } else {
            state.map.removeLayer(marker);
        }
    });
}

// Toggle grid visibility
function toggleGrid(show) {
    if (show) {
        if (!state.gridLayer) {
            createGridLayer();
        }
        if (!state.map.hasLayer(state.gridLayer)) {
            state.gridLayer.addTo(state.map);
        }
    } else {
        if (state.gridLayer) {
            state.map.removeLayer(state.gridLayer);
        }
    }
}

// Create grid layer
function createGridLayer() {
    const gridLines = [];

    // Vertical lines every 100 game units
    for (let x = CONFIG.gameBounds.minX; x <= CONFIG.gameBounds.maxX; x += 100) {
        const start = gameToPixel(x, CONFIG.gameBounds.minY);
        const end = gameToPixel(x, CONFIG.gameBounds.maxY);
        gridLines.push([start, end]);
    }

    // Horizontal lines every 100 game units
    for (let y = CONFIG.gameBounds.minY; y <= CONFIG.gameBounds.maxY; y += 100) {
        const start = gameToPixel(CONFIG.gameBounds.minX, y);
        const end = gameToPixel(CONFIG.gameBounds.maxX, y);
        gridLines.push([start, end]);
    }

    state.gridLayer = L.layerGroup(
        gridLines.map(line => L.polyline(line, {
            color: '#4b5563',
            weight: 1,
            opacity: 0.3
        }))
    );
}

// Handle biome filter change
function handleBiomeFilterChange(biomeName) {
    state.selectedBiome = biomeName;

    if (biomeName === 'all') {
        // Reset all polygons
        state.biomePolygons.forEach(polygon => {
            polygon.setStyle({ opacity: 0.5, fillOpacity: 0.1 });
        });
    } else {
        // Highlight selected biome
        state.biomePolygons.forEach(polygon => {
            if (polygon.biome === biomeName) {
                polygon.setStyle({ opacity: 0.8, fillOpacity: 0.3 });

                // Zoom to biome
                const bounds = polygon.getBounds();
                state.map.fitBounds(bounds, { padding: [50, 50] });
            } else {
                polygon.setStyle({ opacity: 0.1, fillOpacity: 0.05 });
            }
        });
    }

    updateStatus(`Filtered to: ${biomeName}`);
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize map
    initMap();

    // Load biome data
    loadBiomeData();

    // Button events
    document.getElementById('btn-clear').addEventListener('click', clearAllPoints);
    document.getElementById('btn-import').addEventListener('click', importPatrolPoints);
    document.getElementById('btn-export').addEventListener('click', exportPatrolPoints);

    // File input event
    document.getElementById('file-input').addEventListener('change', handleFileSelect);

    // Toggle events
    document.getElementById('toggle-biomes').addEventListener('change', function(e) {
        toggleBiomeBounds(e.target.checked);
    });

    document.getElementById('toggle-beacons').addEventListener('change', function(e) {
        toggleBeacons(e.target.checked);
    });

    document.getElementById('toggle-grid').addEventListener('change', function(e) {
        toggleGrid(e.target.checked);
    });

    // Biome selector
    document.getElementById('biome-selector').addEventListener('change', function(e) {
        handleBiomeFilterChange(e.target.value);
    });

    updateStatus('Ready. Click to add patrol points, right-click to delete.');
});

// Make functions globally accessible for inline event handlers
window.deletePatrolPoint = deletePatrolPoint;
