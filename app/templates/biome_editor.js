// RotMG Biome Beacon Editor

const CONFIG = {
    gameBounds: { minX: 283, maxX: 2048, minY: 130, maxY: 1871 },
    imageDimensions: { width: 1801, height: 1872 },
    mapImagePath: 'realm_map.png',
    offsetX: 14
};

// All biomes from the game
const BIOMES = [
    // Rookie Biomes
    { id: 'beach', name: 'Beach', beacon: 'Shores Beacon', tier: 'Rookie', color: '#f4d03f' },
    { id: 'undead_forest', name: 'Undead Forest', beacon: 'Gloomy Beacon', tier: 'Rookie', color: '#5d6d7e' },
    { id: 'low_forest', name: 'Low Forest', beacon: 'Forest Beacon', tier: 'Rookie', color: '#58d68d' },
    { id: 'mid_plains', name: 'Mid Plains', beacon: 'Plains Beacon', tier: 'Rookie', color: '#abebc6' },
    { id: 'nature_ruins', name: 'Nature Ruins (Mid Forest)', beacon: 'Forest Beacon', tier: 'Rookie', color: '#1e8449' },
    { id: 'mid_desert', name: 'Mid Desert', beacon: 'Arid Beacon', tier: 'Rookie', color: '#f5b041' },
    { id: 'high_plains', name: 'High Plains (Withered)', beacon: 'Plains Beacon', tier: 'Rookie', color: '#b7950b' },
    { id: 'high_forest', name: 'High Forest (Dark)', beacon: 'Forest Beacon', tier: 'Rookie', color: '#196f3d' },
    { id: 'high_desert', name: 'High Desert', beacon: 'Arid Beacon', tier: 'Rookie', color: '#e67e22' },

    // Adept Biomes
    { id: 'coral_reefs', name: 'Coral Reefs', beacon: 'Oceanic Beacon', tier: 'Adept', color: '#5dade2' },
    { id: 'sprite_forest', name: 'Sprite Forest', beacon: 'Fey Beacon', tier: 'Adept', color: '#af7ac5' },
    { id: 'haunted_hallows', name: 'Haunted Hallows', beacon: 'Haunted Beacon', tier: 'Adept', color: '#8e44ad' },
    { id: 'shipwreck_cove', name: 'Shipwreck Cove', beacon: 'Shipwrecked Beacon', tier: 'Adept', color: '#1abc9c' },
    { id: 'dead_church', name: 'Dead Church', beacon: 'Gothic Beacon', tier: 'Adept', color: '#7f8c8d' },
    { id: 'risen_hell', name: 'Risen Hell', beacon: 'Hell Beacon', tier: 'Adept', color: '#e74c3c' },
    { id: 'abandoned_city', name: 'Abandoned City', beacon: 'Abandoned Beacon', tier: 'Adept', color: '#95a5a6' },

    // Veteran Biomes
    { id: 'deep_sea_abyss', name: 'Deep Sea Abyss', beacon: 'Abyssal Beacon', tier: 'Veteran', color: '#2c3e50' },
    { id: 'prehistoric', name: 'Prehistoric (Carboniferous)', beacon: 'Prehistoric Beacon', tier: 'Veteran', color: '#27ae60' },
    { id: 'floral_escape', name: 'Floral Escape', beacon: 'Floral Beacon', tier: 'Veteran', color: '#f1948a' },
    { id: 'sanguine_forest', name: 'Sanguine Forest', beacon: 'Sanguine Beacon', tier: 'Veteran', color: '#c0392b' },
    { id: 'runic_tundra', name: 'Runic Tundra', beacon: 'Frozen Beacon', tier: 'Veteran', color: '#85c1e9' }
];

// State
const state = {
    map: null,
    selectedBiome: null,
    biomeBeacons: {},  // { biomeId: [{x, y, marker}, ...] }
    gridLayer: null
};

// Initialize
function init() {
    initMap();
    initBiomeList();
    initEventListeners();
    updateStatus('Ready. Select a biome from the list, then click on the map to place beacons.');
}

function initMap() {
    const bounds = [[0, 0], [CONFIG.imageDimensions.height, CONFIG.imageDimensions.width]];

    state.map = L.map('map', {
        crs: L.CRS.Simple,
        minZoom: -2,
        maxZoom: 3,
        zoomSnap: 0.25
    });

    L.imageOverlay(CONFIG.mapImagePath, bounds).addTo(state.map);
    state.map.fitBounds(bounds);

    state.map.on('click', onMapClick);
    state.map.on('mousemove', onMouseMove);
    state.map.getContainer().addEventListener('contextmenu', e => e.preventDefault());
}

function initBiomeList() {
    const container = document.getElementById('biome-list');
    let html = '';

    let currentTier = '';
    BIOMES.forEach(biome => {
        if (biome.tier !== currentTier) {
            currentTier = biome.tier;
            html += `<div style="padding: 8px 0 4px; color: #e94560; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">${currentTier}</div>`;
        }

        state.biomeBeacons[biome.id] = [];

        html += `
            <div class="biome-item" data-biome="${biome.id}" style="border-left: 4px solid ${biome.color}">
                <span class="biome-name">${biome.name}</span>
                <span class="beacon-count" id="count-${biome.id}">0</span>
            </div>
        `;
    });

    container.innerHTML = html;

    // Add click handlers
    container.querySelectorAll('.biome-item').forEach(item => {
        item.addEventListener('click', () => selectBiome(item.dataset.biome));
    });
}

function initEventListeners() {
    document.getElementById('btn-export').addEventListener('click', exportBiomeData);
    document.getElementById('btn-clear').addEventListener('click', clearSelectedBiome);
    document.getElementById('btn-clear-all').addEventListener('click', clearAllBeacons);
    document.getElementById('toggle-grid').addEventListener('change', e => toggleGrid(e.target.checked));
}

// Coordinate conversion
function gameToPixel(gx, gy) {
    const { minX, maxX, minY, maxY } = CONFIG.gameBounds;
    const { width, height } = CONFIG.imageDimensions;
    const px = (((gx + CONFIG.offsetX) - minX) / (maxX - minX)) * width;
    const py = height - ((gy - minY) / (maxY - minY)) * height;
    return [py, px];  // Leaflet uses [lat, lng] = [y, x]
}

function pixelToGame(py, px) {
    const { minX, maxX, minY, maxY } = CONFIG.gameBounds;
    const { width, height } = CONFIG.imageDimensions;
    const gx = Math.round((px / width) * (maxX - minX) + minX - CONFIG.offsetX);
    const gy = Math.round(((height - py) / height) * (maxY - minY) + minY);
    return { x: gx, y: gy };
}

// Biome selection
function selectBiome(biomeId) {
    // Update UI
    document.querySelectorAll('.biome-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.biome === biomeId);
    });

    state.selectedBiome = biomeId;
    const biome = BIOMES.find(b => b.id === biomeId);

    document.getElementById('mode-indicator').textContent = `Adding beacons to: ${biome.name}`;
    document.getElementById('mode-indicator').classList.add('active');

    updateBeaconList();
    updateStatus(`Selected ${biome.name}. Click on map to add ${biome.beacon} locations.`);
}

// Map click handler
function onMapClick(e) {
    if (!state.selectedBiome) {
        updateStatus('Please select a biome first!');
        return;
    }

    const coords = pixelToGame(e.latlng.lat, e.latlng.lng);
    addBeacon(state.selectedBiome, coords.x, coords.y);
}

function onMouseMove(e) {
    const coords = pixelToGame(e.latlng.lat, e.latlng.lng);
    document.getElementById('mouse-coords').textContent = `Coords: ${coords.x}, ${coords.y}`;
}

// Beacon management
function addBeacon(biomeId, x, y) {
    const biome = BIOMES.find(b => b.id === biomeId);
    const pixelCoords = gameToPixel(x, y);

    const marker = L.circleMarker(pixelCoords, {
        radius: 10,
        fillColor: biome.color,
        color: '#ffffff',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(state.map);

    const index = state.biomeBeacons[biomeId].length + 1;
    marker.bindTooltip(`${biome.name} #${index}<br>(${x}, ${y})`, { direction: 'top' });

    marker.on('contextmenu', function(e) {
        L.DomEvent.stopPropagation(e);
        removeBeacon(biomeId, marker);
    });

    state.biomeBeacons[biomeId].push({ x, y, marker });

    updateBeaconCount(biomeId);
    updateBeaconList();
    updateTotalCount();
    updateStatus(`Added beacon at (${x}, ${y}) to ${biome.name}`);
}

function removeBeacon(biomeId, marker) {
    const beacons = state.biomeBeacons[biomeId];
    const index = beacons.findIndex(b => b.marker === marker);

    if (index !== -1) {
        state.map.removeLayer(marker);
        beacons.splice(index, 1);

        updateBeaconCount(biomeId);
        updateBeaconList();
        updateTotalCount();
        updateStatus(`Removed beacon from ${BIOMES.find(b => b.id === biomeId).name}`);
    }
}

function clearSelectedBiome() {
    if (!state.selectedBiome) {
        updateStatus('No biome selected');
        return;
    }

    const biome = BIOMES.find(b => b.id === state.selectedBiome);
    const beacons = state.biomeBeacons[state.selectedBiome];

    if (beacons.length === 0) {
        updateStatus(`${biome.name} has no beacons to clear`);
        return;
    }

    if (!confirm(`Clear all ${beacons.length} beacons from ${biome.name}?`)) return;

    beacons.forEach(b => state.map.removeLayer(b.marker));
    state.biomeBeacons[state.selectedBiome] = [];

    updateBeaconCount(state.selectedBiome);
    updateBeaconList();
    updateTotalCount();
    updateStatus(`Cleared all beacons from ${biome.name}`);
}

function clearAllBeacons() {
    const total = Object.values(state.biomeBeacons).reduce((sum, arr) => sum + arr.length, 0);
    if (total === 0) {
        updateStatus('No beacons to clear');
        return;
    }

    if (!confirm(`Clear ALL ${total} beacons from all biomes?`)) return;

    Object.keys(state.biomeBeacons).forEach(biomeId => {
        state.biomeBeacons[biomeId].forEach(b => state.map.removeLayer(b.marker));
        state.biomeBeacons[biomeId] = [];
        updateBeaconCount(biomeId);
    });

    updateBeaconList();
    updateTotalCount();
    updateStatus('Cleared all beacons');
}

// UI updates
function updateBeaconCount(biomeId) {
    const count = state.biomeBeacons[biomeId].length;
    document.getElementById(`count-${biomeId}`).textContent = count;
}

function updateTotalCount() {
    const total = Object.values(state.biomeBeacons).reduce((sum, arr) => sum + arr.length, 0);
    document.getElementById('beacon-count').textContent = `Total Beacons: ${total}`;
}

function updateBeaconList() {
    const container = document.getElementById('beacon-list');

    if (!state.selectedBiome) {
        container.innerHTML = '<p class="empty-message">Select a biome first</p>';
        return;
    }

    const beacons = state.biomeBeacons[state.selectedBiome];

    if (beacons.length === 0) {
        container.innerHTML = '<p class="empty-message">No beacons yet. Click on map to add.</p>';
        return;
    }

    container.innerHTML = beacons.map((b, i) => `
        <div class="beacon-entry">
            <span>#${i + 1}: (${b.x}, ${b.y})</span>
            <button onclick="removeBeaconByIndex('${state.selectedBiome}', ${i})">X</button>
        </div>
    `).join('');
}

function removeBeaconByIndex(biomeId, index) {
    const beacon = state.biomeBeacons[biomeId][index];
    if (beacon) {
        removeBeacon(biomeId, beacon.marker);
    }
}

function updateStatus(msg) {
    document.getElementById('status-message').textContent = msg;
}

// Grid
function toggleGrid(show) {
    if (show) {
        if (!state.gridLayer) {
            const lines = [];
            for (let x = CONFIG.gameBounds.minX; x <= CONFIG.gameBounds.maxX; x += 100) {
                lines.push([gameToPixel(x, CONFIG.gameBounds.minY), gameToPixel(x, CONFIG.gameBounds.maxY)]);
            }
            for (let y = CONFIG.gameBounds.minY; y <= CONFIG.gameBounds.maxY; y += 100) {
                lines.push([gameToPixel(CONFIG.gameBounds.minX, y), gameToPixel(CONFIG.gameBounds.maxX, y)]);
            }
            state.gridLayer = L.layerGroup(lines.map(l => L.polyline(l, { color: '#444', weight: 1, opacity: 0.4 })));
        }
        state.gridLayer.addTo(state.map);
    } else if (state.gridLayer) {
        state.map.removeLayer(state.gridLayer);
    }
}

// Export
function exportBiomeData() {
    const exportData = {
        biomes: {},
        beacons: [],
        metadata: {
            exported: new Date().toISOString(),
            game_bounds: CONFIG.gameBounds
        }
    };

    BIOMES.forEach(biome => {
        const beacons = state.biomeBeacons[biome.id];
        if (beacons.length > 0) {
            exportData.biomes[biome.id] = {
                name: biome.name,
                beacon_type: biome.beacon,
                tier: biome.tier,
                color: biome.color,
                beacon_positions: beacons.map(b => ({ x: b.x, y: b.y }))
            };

            beacons.forEach(b => {
                exportData.beacons.push({
                    name: biome.beacon,
                    biome: biome.id,
                    x: b.x,
                    y: b.y
                });
            });
        }
    });

    // Download
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `biome_beacons_${new Date().toISOString().slice(0,19).replace(/[:-]/g,'')}.json`;
    a.click();
    URL.revokeObjectURL(url);

    updateStatus(`Exported ${exportData.beacons.length} beacons from ${Object.keys(exportData.biomes).length} biomes`);
}

// Global function for inline handlers
window.removeBeaconByIndex = removeBeaconByIndex;

// Start
document.addEventListener('DOMContentLoaded', init);
