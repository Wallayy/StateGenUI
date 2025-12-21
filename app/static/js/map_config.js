// Shared Map Configuration
// CALIBRATED from 5 reference points (Updated 2025-12-11)
const MAP_CONFIG = {
    imageDimensions: { width: 1801, height: 1872 },
    mapImagePath: 'realm_map.png',
    scaleX: 0.999134,
    offsetX: -5.764631,
    scaleY: 0.998806,
    offsetY: 39.379864
};

// Global alias for backward compatibility if needed, or users can just use MAP_CONFIG
// For now, let's keep CONFIG as the variable name if scripts expect it, 
// or I'll change scripts to use MAP_CONFIG or just assign CONFIG = MAP_CONFIG.
// Current scripts define 'const CONFIG = ...'. 
// If I use 'const CONFIG' here, it might conflict if they re-declare it.
// I'll use 'const CONFIG' here and REMOVE the declaration from the HTML files.
const CONFIG = MAP_CONFIG;
