// ===== INITIALIZATION =====
const map = L.map('map').setView([3.1390, 101.6869], 13); // Kuala Lumpur

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors',
    detectRetina: true
}).addTo(map);

// IIUM Color Scheme
const IIUM_BLUE = '#0056A4';
const IIUM_DARK_BLUE = '#003C78';
const IIUM_GREEN = '#8BC34A';
const IIUM_DARK_GREEN = '#689F38';
const IIUM_GOLD = '#FFC107';

// Custom icons for optimized route with IIUM colors
const optimizedStartIcon = L.divIcon({
    html: `<div style="background: linear-gradient(135deg, ${IIUM_BLUE}, ${IIUM_DARK_BLUE}); 
                  width: 40px; height: 40px; border-radius: 50%; 
                  border: 3px solid white; box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                  display: flex; align-items: center; justify-content: center;
                  color: white; font-size: 18px;">
              <i class="fas fa-play"></i>
          </div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

const originalStartIcon = L.divIcon({
    html: `<div style="background: linear-gradient(135deg, ${IIUM_GREEN}, ${IIUM_DARK_GREEN}); 
                  width: 40px; height: 40px; border-radius: 50%; 
                  border: 3px solid white; box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                  display: flex; align-items: center; justify-content: center;
                  color: white; font-size: 18px;">
              <i class="fas fa-play"></i>
          </div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

const optimizedStopIcon = L.divIcon({
    html: (num) => `<div style="background: white; width: 36px; height: 36px; 
                        border-radius: 50%; border: 3px solid ${IIUM_BLUE};
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        display: flex; align-items: center; justify-content: center;
                        color: ${IIUM_BLUE}; font-weight: 800; font-size: 14px;">
                    ${num}
                </div>`,
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 18]
});

const originalStopIcon = L.divIcon({
    html: (num) => `<div style="background: white; width: 36px; height: 36px; 
                        border-radius: 50%; border: 3px solid ${IIUM_GREEN};
                        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        display: flex; align-items: center; justify-content: center;
                        color: ${IIUM_GREEN}; font-weight: 800; font-size: 14px;">
                    ${num}
                </div>`,
    className: '',
    iconSize: [36, 36],
    iconAnchor: [18, 18]
});

const optimizedEndIcon = L.divIcon({
    html: `<div style="background: linear-gradient(135deg, ${IIUM_BLUE}, ${IIUM_DARK_BLUE}); 
                  width: 40px; height: 40px; border-radius: 50%; 
                  border: 3px solid white; box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                  display: flex; align-items: center; justify-content: center;
                  color: white; font-size: 18px;">
              <i class="fas fa-flag-checkered"></i>
          </div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

const originalEndIcon = L.divIcon({
    html: `<div style="background: linear-gradient(135deg, ${IIUM_GREEN}, ${IIUM_DARK_GREEN}); 
                  width: 40px; height: 40px; border-radius: 50%; 
                  border: 3px solid white; box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                  display: flex; align-items: center; justify-content: center;
                  color: white; font-size: 18px;">
              <i class="fas fa-flag-checkered"></i>
          </div>`,
    className: '',
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

// ===== STATE MANAGEMENT =====
let addressItems = [];
let mapLayerGroup = L.layerGroup().addTo(map);
let currentRoute = null;
let chartInstance = null;
let showOriginalOnly = false;
let originalRouteLayer = null;
let optimizedRouteLayer = null;

// ===== DOM ELEMENTS =====
const addressInput = document.getElementById('address-input');
const addBtn = document.getElementById('add-btn');
const removeAllBtn = document.getElementById('remove-all-btn');
const optimizeBtn = document.getElementById('optimize-btn');
const clearRouteBtn = document.getElementById('clear-route-btn');
const addressList = document.getElementById('address-list');
const loadingOverlay = document.getElementById('loading-overlay');

// Metrics elements
const totalDistanceEl = document.getElementById('total-distance');
const co2SavingsEl = document.getElementById('co2-savings');
const timeSavedEl = document.getElementById('time-saved');
const fuelCostEl = document.getElementById('fuel-cost');
const fuelSavingsEl = document.getElementById('fuel-savings');
const distanceSavingsEl = document.getElementById('distance-savings');
const co2ComparisonEl = document.getElementById('co2-comparison');
const overallSavingsEl = document.getElementById('overall-savings');
const routeStepsEl = document.getElementById('route-steps');
const stopCountEl = document.getElementById('stop-count');

// Header stats
const headerDistanceEl = document.getElementById('header-distance');
const headerSavingsEl = document.getElementById('header-savings');
const headerStopsEl = document.getElementById('header-stops');

// Chart tabs
const chartTabs = document.querySelectorAll('.chart-tab');

// ===== EVENT LISTENERS =====
addBtn.addEventListener('click', addAddress);
addressInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') addAddress();
});
removeAllBtn.addEventListener('click', clearAllAddresses);
optimizeBtn.addEventListener('click', optimizeRoute);
clearRouteBtn.addEventListener('click', clearRoute);

// Map controls
document.getElementById('zoom-in').addEventListener('click', () => map.zoomIn());
document.getElementById('zoom-out').addEventListener('click', () => map.zoomOut());
document.getElementById('locate-me').addEventListener('click', locateUser);

// Chart tabs
        chartTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                chartTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                updateChartType(tab.dataset.chart);
            });
        });

// ===== CORE FUNCTIONS =====

function addAddress() {
    const text = addressInput.value.trim();
    if (!text) {
        showNotification('error', 'Empty Address', 'Please enter a delivery address');
        addressInput.focus();
        return;
    }
    
    if (addressItems.length >= 10) {
        showNotification('warning', 'Limit Reached', 'Maximum 10 delivery stops allowed');
        return;
    }
    
    // Check for duplicate address
    if (addressItems.some(item => item.text.toLowerCase() === text.toLowerCase())) {
        showNotification('warning', 'Duplicate Address', 'This address is already in the list');
        addressInput.value = '';
        addressInput.focus();
        return;
    }
    
    const addressItem = {
        id: Date.now() + Math.random(),
        text: text,
        number: addressItems.length + 1
    };
    
    addressItems.push(addressItem);
    renderAddressItem(addressItem);
    
    addressInput.value = '';
    addressInput.focus();
    
    updateUIState();
    showNotification('success', 'Address Added', 'Delivery stop added successfully');
}

function renderAddressItem(item) {
    // Remove empty state if present
    const emptyState = addressList.querySelector('.empty-state');
    if (emptyState) emptyState.remove();
    
    const div = document.createElement('div');
    div.className = 'address-item';
    div.dataset.id = item.id;
    
    div.innerHTML = `
        <div class="stop-marker">${item.number}</div>
        <div class="stop-info">
            <div class="stop-address">${item.text}</div>
            <div class="stop-status">
                <i class="fas fa-clock"></i>
                <span>Pending optimization</span>
            </div>
        </div>
        <div class="stop-actions">
            <button class="action-btn remove-btn" title="Remove address">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    // Remove button
    div.querySelector('.remove-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        removeAddress(item.id);
    });
    
    addressList.appendChild(div);
    div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function removeAddress(id) {
    const index = addressItems.findIndex(item => item.id === id);
    if (index === -1) return;
    
    addressItems.splice(index, 1);
    
    // Remove from DOM with animation
    const item = document.querySelector(`.address-item[data-id="${id}"]`);
    if (item) {
        item.style.animation = 'slideIn 0.3s ease reverse forwards';
        setTimeout(() => item.remove(), 300);
    }
    
    // Update numbers
    updateAddressNumbers();
    updateUIState();
    
    if (addressItems.length === 0) {
        showEmptyState();
    }
    
    showNotification('info', 'Address Removed', 'Delivery stop removed');
}

function updateAddressNumbers() {
    addressItems.forEach((item, index) => {
        item.number = index + 1;
        const element = document.querySelector(`.address-item[data-id="${item.id}"] .stop-marker`);
        if (element) {
            element.textContent = index + 1;
        }
    });
}

function showEmptyState() {
    addressList.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-route"></i>
            <p>No addresses added yet</p>
            <small>Add at least 2 addresses to optimize</small>
        </div>
    `;
}

function clearAllAddresses() {
    if (addressItems.length === 0) {
        showNotification('info', 'No Addresses', 'No addresses to remove');
        return;
    }
    
    if (confirm('Are you sure you want to remove all delivery addresses?')) {
        addressItems = [];
        addressList.innerHTML = '';
        showEmptyState();
        clearRoute();
        updateUIState();
        showNotification('success', 'Cleared All', 'All addresses removed');
    }
}

function updateUIState() {
    // Update stop count
    stopCountEl.textContent = `${addressItems.length} ${addressItems.length === 1 ? 'stop' : 'stops'}`;
    headerStopsEl.textContent = addressItems.length;
    
    // Enable/disable optimize button
    optimizeBtn.disabled = addressItems.length < 2;
    optimizeBtn.innerHTML = addressItems.length < 2 
        ? `<i class="fas fa-bolt"></i><span>Need ${2 - addressItems.length} more stops</span>`
        : `<i class="fas fa-bolt"></i><span>Optimize Route</span>`;
}

async function optimizeRoute() {
    if (addressItems.length < 2) {
        showNotification('error', 'Not Enough Stops', 'Please add at least 2 delivery addresses');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/process-route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                addresses: addressItems.map(item => item.text)
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            handleOptimizationSuccess(data);
        } else {
            throw new Error(data.error || 'Optimization failed');
        }
    } catch (error) {
        console.error('Optimization error:', error);
        showNotification('error', 'Optimization Failed', error.message || 'Please try again');
    } finally {
        showLoading(false);
    }
}

function handleOptimizationSuccess(data) {
    console.log("Optimization successful:", data);
    
    // ✅ Update metrics with NEW data structure
    updateMetrics(data.route_comparison);
    
    // Draw route on map with IIUM colors
    drawRoute(data.routes);
    
    // Update address list with optimized order
    updateAddressListWithOrder(data.routes.optimized_route);
    
    // Update chart with IIUM colors
    updateChart(data.route_comparison);
    
    // Update route steps
    updateRouteSteps(data.routes.optimized_route);
    
    // Update header stats
    headerDistanceEl.textContent = `${data.route_comparison.optimized_distance_km.toFixed(1)} km`;
    headerSavingsEl.textContent = `${data.route_comparison.co2_saved_kg.toFixed(1)} kg`;
    
    // Show success notification
    const savingsPercent = data.route_comparison.distance_savings_percentage;
    showNotification('success', 'Route Optimized!', 
        `Saved ${savingsPercent}% distance and ${data.route_comparison.co2_saved_kg.toFixed(1)}kg CO₂`);
}

function updateMetrics(comparison) {
    // ✅ Use the new comparison data structure
    const distanceSaved = comparison.original_distance_km - comparison.optimized_distance_km;
    const co2Saved = comparison.original_co2_kg - comparison.optimized_co2_kg;
    const fuelSaved = (comparison.original_fuel_cost_rm || 0) - (comparison.optimized_fuel_cost_rm || 0);
    
    // Update main metrics
    totalDistanceEl.textContent = comparison.optimized_distance_km.toFixed(1);
    co2SavingsEl.textContent = comparison.optimized_co2_kg.toFixed(1);
    timeSavedEl.textContent = Math.round(comparison.time_saved_minutes || 0);
    fuelCostEl.textContent = `RM ${(comparison.optimized_fuel_cost_rm || 0).toFixed(2)}`;
    
    // Update savings displays
    distanceSavingsEl.innerHTML = `<i class="fas fa-arrow-down"></i><span>${distanceSaved.toFixed(1)} km saved</span>`;
    co2ComparisonEl.innerHTML = `<i class="fas fa-tree"></i><span>≈ ${Math.round(co2Saved / 0.021)} trees saved</span>`;
    fuelSavingsEl.innerHTML = `<i class="fas fa-arrow-down"></i><span>RM ${fuelSaved.toFixed(2)} saved</span>`;
    overallSavingsEl.innerHTML = `<i class="fas fa-trophy"></i><span>${comparison.distance_savings_percentage.toFixed(1)}% More Efficient</span>`;
}

function drawRoute(routesData) {
    console.log("🔍 Drawing routes - Data received:");
    console.log("- Original route shape exists:", !!routesData.original_route_shape);
    console.log("- Original route shape length:", routesData.original_route_shape?.length);
    console.log("- Optimized route shape exists:", !!routesData.optimized_route_shape);
    console.log("- Optimized route shape length:", routesData.optimized_route_shape?.length);
    
    // Clear existing layers
    mapLayerGroup.clearLayers();
    
    // Reset layer references
    originalRouteLayer = null;
    optimizedRouteLayer = null;
    
    // Draw ORIGINAL route (dashed green line - IIUM GREEN)
    if (routesData.original_route_shape && routesData.original_route_shape.length > 0) {
        console.log("🟢 Drawing original route with", routesData.original_route_shape.length, "points");
        
        originalRouteLayer = L.polyline(routesData.original_route_shape, {
            color: IIUM_GREEN,
            weight: 5,
            opacity: 0.8,
            lineJoin: 'round',
            lineCap: 'round',
            dashArray: '15, 10',
            dashOffset: '0'
        }).addTo(mapLayerGroup);
        
        originalRouteLayer.bindPopup('<b>Original Route</b><br>User\'s input order');
        
        // Add start marker for original route
        if (routesData.original_route_shape[0]) {
            L.marker(routesData.original_route_shape[0], {
                icon: originalStartIcon
            }).addTo(mapLayerGroup).bindPopup('<b>Original Start</b><br>First address in your input order');
        }
        
        // Add end marker for original route
        if (routesData.original_route_shape[routesData.original_route_shape.length - 1]) {
            L.marker(routesData.original_route_shape[routesData.original_route_shape.length - 1], {
                icon: originalEndIcon
            }).addTo(mapLayerGroup).bindPopup('<b>Original End</b><br>Return to start point');
        }
    } else {
        console.log("❌ No original route shape data available");
    }
    
    // Draw OPTIMIZED route (solid blue line - IIUM BLUE)
    if (routesData.optimized_route_shape && routesData.optimized_route_shape.length > 0) {
        console.log("🔵 Drawing optimized route with", routesData.optimized_route_shape.length, "points");
        
        optimizedRouteLayer = L.polyline(routesData.optimized_route_shape, {
            color: IIUM_BLUE,
            weight: 6,
            opacity: 0.9,
            lineJoin: 'round',
            lineCap: 'round'
        }).addTo(mapLayerGroup);
        
        optimizedRouteLayer.bindPopup('<b>Optimized Route</b><br>Genetic Algorithm result');
        
        // Add start marker for optimized route
        if (routesData.optimized_route_shape[0]) {
            L.marker(routesData.optimized_route_shape[0], {
                icon: optimizedStartIcon
            }).addTo(mapLayerGroup).bindPopup('<b>Optimized Start</b><br>First stop in optimized sequence');
        }
        
        // Add end marker for optimized route
        if (routesData.optimized_route_shape[routesData.optimized_route_shape.length - 1]) {
            L.marker(routesData.optimized_route_shape[routesData.optimized_route_shape.length - 1], {
                icon: optimizedEndIcon
            }).addTo(mapLayerGroup).bindPopup('<b>Optimized End</b><br>Return to start point');
        }
    } else {
        console.log("❌ No optimized route shape data available");
    }
    
    // Add markers for OPTIMIZED stops with IIUM colors
    if (routesData.stops_coordinates && routesData.stops_coordinates.length > 0) {
        routesData.stops_coordinates.forEach((coord, index) => {
            const isStart = index === 0;
            const isEnd = index === routesData.stops_coordinates.length - 1;
            
            let icon;
            if (isStart) {
                icon = optimizedStartIcon;
            } else if (isEnd) {
                icon = optimizedEndIcon;
            } else {
                icon = L.divIcon({
                    html: `<div style="background: white; width: 36px; height: 36px; 
                                border-radius: 50%; border: 3px solid ${IIUM_BLUE};
                                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                                display: flex; align-items: center; justify-content: center;
                                color: ${IIUM_BLUE}; font-weight: 800; font-size: 14px;">
                            ${index + 1}
                        </div>`,
                    className: '',
                    iconSize: [36, 36],
                    iconAnchor: [18, 18]
                });
            }
            
            const marker = L.marker(coord, { icon })
                .bindPopup(`
                    <div style="font-family: -apple-system, sans-serif; padding: 8px; min-width: 200px;">
                        <strong style="color: ${IIUM_BLUE}; font-size: 14px;">Optimized Stop ${index + 1}</strong>
                        <div style="font-size: 12px; color: #666; margin-top: 4px; word-break: break-word;">
                            ${routesData.optimized_route ? routesData.optimized_route[index] : 'Unknown address'}
                        </div>
                        <div style="margin-top: 8px; font-size: 11px; color: #888;">
                            <i class="fas fa-location-dot"></i> 
                            ${coord[0].toFixed(4)}, ${coord[1].toFixed(4)}
                        </div>
                    </div>
                `)
                .addTo(mapLayerGroup);
                
            if (isStart) {
                setTimeout(() => marker.openPopup(), 500);
            }
        });
    }
    
    // Add route legend on the map
    addRouteLegend();
    
    // Fit bounds to both routes
    const allLayers = mapLayerGroup.getLayers();
    const bounds = L.latLngBounds([]);
    allLayers.forEach(layer => {
        if (layer.getBounds) {
            bounds.extend(layer.getBounds());
        } else if (layer.getLatLng) {
            bounds.extend(layer.getLatLng());
        }
    });
    
    if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.1));
    }
}

function addRouteLegend() {
    // Create a custom control for route legend
    const legend = L.control({ position: 'bottomright' });
    
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'route-legend');
        div.style.backgroundColor = 'white';
        div.style.padding = '10px';
        div.style.borderRadius = '8px';
        div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
        div.style.fontFamily = 'var(--font-family)';
        div.style.fontSize = '12px';
        
        div.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px; color: ${IIUM_BLUE}">
                <i class="fas fa-map"></i> Route Legend
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="width: 20px; height: 4px; background: ${IIUM_BLUE}; margin-right: 8px;"></div>
                <span>Optimized Route</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="width: 20px; height: 4px; background: ${IIUM_GREEN}; margin-right: 8px; border: 1px solid ${IIUM_GREEN}; background: repeating-linear-gradient(to right, ${IIUM_GREEN} 0, ${IIUM_GREEN} 4px, transparent 4px, transparent 8px);"></div>
                <span>Original Route</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 5px;">
                <div style="width: 12px; height: 12px; background: ${IIUM_BLUE}; border-radius: 50%; margin-right: 8px; border: 2px solid white; box-shadow: 0 0 3px rgba(0,0,0,0.3);"></div>
                <span>Optimized Stop</span>
            </div>
            <div style="margin-top: 8px; font-size: 11px; color: #666;">
                <i class="fas fa-info-circle"></i> Click lines for details
            </div>
        `;
        
        return div;
    };
    
    // Remove existing legend if any
    const existingLegend = document.querySelector('.route-legend');
    if (existingLegend && existingLegend.parentElement) {
        existingLegend.parentElement.remove();
    }
    
    legend.addTo(map);
}

function toggleRouteVisibility() {
    if (!originalRouteLayer || !optimizedRouteLayer) {
        showNotification('warning', 'No Routes', 'Please optimize a route first');
        return;
    }
    
    showOriginalOnly = !showOriginalOnly;
    
    if (showOriginalOnly) {
        // Show original only, hide optimized
        originalRouteLayer.setStyle({ 
            opacity: 0.9, 
            weight: 6,
            dashArray: '15, 10'
        });
        optimizedRouteLayer.setStyle({ 
            opacity: 0.2, 
            weight: 3 
        });
        showNotification('info', 'Showing Original Route', 'Optimized route is dimmed');
        
        // Update legend
        updateLegendForToggle(true);
    } else {
        // Show both routes
        originalRouteLayer.setStyle({ 
            opacity: 0.8, 
            weight: 5,
            dashArray: '15, 10'
        });
        optimizedRouteLayer.setStyle({ 
            opacity: 0.9, 
            weight: 6 
        });
        showNotification('info', 'Showing Both Routes', 'Comparing original vs optimized');
        
        // Update legend
        updateLegendForToggle(false);
    }
}

function updateLegendForToggle(showOriginalOnly) {
    const legend = document.querySelector('.route-legend');
    if (!legend) return;
    
    if (showOriginalOnly) {
        legend.querySelector('div:nth-child(2)').style.opacity = '1';
        legend.querySelector('div:nth-child(2)').style.fontWeight = 'bold';
        legend.querySelector('div:nth-child(3)').style.opacity = '0.5';
        legend.querySelector('div:nth-child(3)').style.fontWeight = 'normal';
    } else {
        legend.querySelector('div:nth-child(2)').style.opacity = '1';
        legend.querySelector('div:nth-child(2)').style.fontWeight = 'normal';
        legend.querySelector('div:nth-child(3)').style.opacity = '1';
        legend.querySelector('div:nth-child(3)').style.fontWeight = 'normal';
    }
}

function updateAddressListWithOrder(optimizedRoute) {
    // Clear current list
    addressList.innerHTML = '';
    
    // Re-add in optimized order (excluding the duplicate end point)
    optimizedRoute.slice(0, -1).forEach((address, index) => {
        const item = addressItems.find(item => item.text === address);
        if (item) {
            item.number = index + 1;
            renderAddressItem(item);
            
            // Update the status to show optimized
            const element = document.querySelector(`.address-item[data-id="${item.id}"] .stop-status`);
            if (element) {
                element.innerHTML = `<i class="fas fa-check-circle"></i><span>Optimized • Stop ${index + 1}</span>`;
                element.style.color = IIUM_BLUE;
            }
        }
    });
}

function updateChart(comparison) {
    // Store comparison data globally for chart tabs
    window.currentComparison = comparison;
    
    if (!chartInstance) {
        initializeChart();
    }
    
    const ctx = document.getElementById('metricsChart').getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Original Route', 'Optimized Route'],
            datasets: [{
                label: 'Distance (km)',
                data: [comparison.original_distance_km, comparison.optimized_distance_km],
                backgroundColor: [
                    `rgba(${hexToRgb(IIUM_GREEN)}, 0.9)`, 
                    `rgba(${hexToRgb(IIUM_BLUE)}, 0.9)`
                ],
                borderColor: [IIUM_GREEN, IIUM_BLUE],
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 14 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(1)} km`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        font: { size: 12, weight: 'bold' },
                        callback: function(value) {
                            return value + ' km';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Distance',
                        font: { size: 14, weight: 'bold' },
                        color: '#616161'
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 13, weight: 'bold' }
                    }
                }
            }
        }
    });
}

function updateChartType(type) {
    if (!chartInstance) return;
    
    const ctx = document.getElementById('metricsChart').getContext('2d');
    const comparison = chartInstance.data.datasets[0].data; // Use stored comparison data
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    let label = '';
    let data = [];
    let yTitle = '';
    
    switch(type) {
        case 'distance':
            label = 'Distance (km)';
            data = [comparison[0], comparison[1]]; // original, optimized
            yTitle = 'Distance';
            break;
        case 'co2':
            label = 'CO₂ Emissions (kg)';
            data = [comparison[0] * 0.120, comparison[1] * 0.120];
            yTitle = 'CO₂ Emissions';
            break;
        case 'time':
            label = 'Travel Time (min)';
            data = [(comparison[0] / 35) * 60, (comparison[1] / 35) * 60];
            yTitle = 'Travel Time';
            break;
        case 'fuel':
            label = 'Fuel Cost (RM)';
            data = [comparison.original_fuel_cost_rm || 0, comparison.optimized_fuel_cost_rm || 0];
            yTitle = 'Fuel Cost';
            break;
    }
    
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Original Route', 'Optimized Route'],
            datasets: [{
                label: label,
                data: data,
                backgroundColor: [
                    `rgba(${hexToRgb(IIUM_GREEN)}, 0.9)`, 
                    `rgba(${hexToRgb(IIUM_BLUE)}, 0.9)`
                ],
                borderColor: [IIUM_GREEN, IIUM_BLUE],
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 14 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const value = context.raw.toFixed(type === 'fuel' ? 2 : 1);
                            const unit = type === 'distance' ? ' km' : 
                                       type === 'co2' ? ' kg CO₂' : 
                                       type === 'time' ? ' min' :
                                       ' RM';
                            return `${label}: ${value}${unit}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        font: { size: 12, weight: 'bold' },
                        callback: function(value) {
                            const unit = type === 'distance' ? ' km' : 
                                       type === 'co2' ? ' kg' : 
                                       type === 'time' ? ' min' :
                                       ' RM';
                            return value + unit;
                        }
                    },
                    title: {
                        display: true,
                        text: yTitle,
                        font: { size: 14, weight: 'bold' },
                        color: '#616161'
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 13, weight: 'bold' }
                    }
                }
            }
        }
    });
}

function updateRouteSteps(optimizedRoute) {
    routeStepsEl.innerHTML = '';
    
    optimizedRoute.slice(0, -1).forEach((address, index) => {
        const step = document.createElement('div');
        step.className = 'route-step';
        step.innerHTML = `
            <div class="step-number">${index + 1}</div>
            <div class="step-address">${address}</div>
            <div class="step-icon">
                ${index === optimizedRoute.length - 2 
                    ? '<i class="fas fa-flag-checkered"></i>' 
                    : '<i class="fas fa-arrow-right"></i>'}
            </div>
        `;
        routeStepsEl.appendChild(step);
    });
}

function clearRoute() {
    mapLayerGroup.clearLayers();
    resetMetrics();
    showNotification('info', 'Route Cleared', 'Map visualization reset');
}

function resetMetrics() {
    totalDistanceEl.textContent = '0.0';
    co2SavingsEl.textContent = '0.0';
    timeSavedEl.textContent = '0';
    fuelCostEl.textContent = 'RM 0.00';
    distanceSavingsEl.innerHTML = '<i class="fas fa-arrow-down"></i><span>0.0 km saved</span>';
    co2ComparisonEl.innerHTML = '<i class="fas fa-tree"></i><span>≈ 0 trees saved</span>';
    fuelSavingsEl.innerHTML = '<i class="fas fa-arrow-down"></i><span>RM 0.00 saved</span>';
    overallSavingsEl.innerHTML = '<i class="fas fa-trophy"></i><span>0% More Efficient</span>';
    
    headerDistanceEl.textContent = '0 km';
    headerSavingsEl.textContent = '0 kg';
    
    // Reset route steps
    routeStepsEl.innerHTML = `
        <div class="empty-route">
            <i class="fas fa-directions"></i>
            <p>Optimize route to see delivery sequence</p>
        </div>
    `;
    
    // Reset address list status
    document.querySelectorAll('.address-item').forEach(item => {
        const status = item.querySelector('.stop-status');
        if (status) {
            status.innerHTML = '<i class="fas fa-clock"></i><span>Pending optimization</span>';
            status.style.color = IIUM_GREEN;
        }
    });
}

function locateUser() {
    if (!navigator.geolocation) {
        showNotification('error', 'Geolocation Error', 'Your browser does not support geolocation');
        return;
    }
    
    showNotification('info', 'Locating...', 'Finding your current position');
    
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const { latitude, longitude } = position.coords;
            map.setView([latitude, longitude], 15);
            
            // Add marker at user's location with IIUM colors
            L.marker([latitude, longitude], {
                icon: L.divIcon({
                    html: `<div style="background: ${IIUM_BLUE}; width: 40px; height: 40px; 
                                border-radius: 50%; border: 3px solid white; 
                                box-shadow: 0 3px 10px rgba(0,0,0,0.3);
                                display: flex; align-items: center; justify-content: center;
                                color: white; font-size: 18px;">
                            <i class="fas fa-user"></i>
                          </div>`,
                    className: '',
                    iconSize: [40, 40],
                    iconAnchor: [20, 20]
                })
            })
            .addTo(mapLayerGroup)
            .bindPopup('<b>Your Location</b>')
            .openPopup();
            
            showNotification('success', 'Location Found', 'Centered map on your location');
        },
        (error) => {
            showNotification('error', 'Location Error', 'Unable to retrieve your location');
        }
    );
}

function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
    optimizeBtn.disabled = show;
    
    if (show) {
        optimizeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Optimizing...</span>';
    } else {
        updateUIState();
    }
}

// ===== NOTIFICATION SYSTEM =====
function showNotification(type, title, message) {
    const container = document.querySelector('.toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    
    // Set border color based on type
    let borderColor = IIUM_BLUE;
    if (type === 'success') borderColor = IIUM_GREEN;
    else if (type === 'error') borderColor = '#F44336';
    else if (type === 'warning') borderColor = IIUM_GOLD;
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${icons[type]}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="action-btn close-toast" title="Close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Set border color
    toast.style.borderLeftColor = borderColor;
    
    container.appendChild(toast);
    
    // Close button
    toast.querySelector('.close-toast').addEventListener('click', () => {
        removeToast(toast);
    });
    
    // Auto-remove after 5 seconds
    const autoRemove = setTimeout(() => {
        removeToast(toast);
    }, 5000);
    
    // Keep toast on hover
    toast.addEventListener('mouseenter', () => {
        clearTimeout(autoRemove);
    });
    
    toast.addEventListener('mouseleave', () => {
        setTimeout(() => removeToast(toast), 3000);
    });
}

function removeToast(toast) {
    toast.style.animation = 'slideInRight 0.3s ease reverse forwards';
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// ===== INITIALIZATION =====
function initializeChart() {
    const ctx = document.getElementById('metricsChart').getContext('2d');
    
    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Original Route', 'Optimized Route'],
            datasets: [{
                label: 'Distance (km)',
                data: [0, 0],
                backgroundColor: [
                    `rgba(${hexToRgb(IIUM_GREEN)}, 0.9)`, 
                    `rgba(${hexToRgb(IIUM_BLUE)}, 0.9)`
                ],
                borderColor: [IIUM_GREEN, IIUM_BLUE],
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleFont: { size: 14, weight: 'bold' },
                    bodyFont: { size: 14 },
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw.toFixed(1)} km`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' },
                    ticks: {
                        font: { size: 12, weight: 'bold' },
                        callback: function(value) {
                            return value + ' km';
                        }
                    },
                    title: {
                        display: true,
                        text: 'Distance',
                        font: { size: 14, weight: 'bold' },
                        color: '#616161'
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: {
                        font: { size: 13, weight: 'bold' }
                    }
                }
            }
        }
    });
}

// ===== APP STARTUP =====
document.addEventListener('DOMContentLoaded', () => {
    // Initialize UI
    updateUIState();
    
    // Focus on input
    setTimeout(() => {
        addressInput.focus();
    }, 500);
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter to optimize
        if (e.ctrlKey && e.key === 'Enter') {
            optimizeRoute();
        }
        // Escape to clear input
        if (e.key === 'Escape') {
            addressInput.value = '';
            addressInput.focus();
        }
    });
    
    // Show welcome message
    setTimeout(() => {
        showNotification('info', 'Welcome to GreenPath', 
            'Add delivery addresses and click Optimize to find the best route');
    }, 2000);
});

// ===== UTILITY FUNCTIONS =====
function formatDistance(km) {
    if (km < 1) {
        return `${(km * 1000).toFixed(0)} m`;
    }
    return `${km.toFixed(1)} km`;
}

function formatCO2(kg) {
    return `${kg.toFixed(1)} kg`;
}

function calculateTreesSaved(co2Kg) {
    // 1 tree absorbs approximately 21kg CO2 per year
    return Math.round(co2Kg / 21);
}

function hexToRgb(hex) {
    // Convert hex color to RGB string
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? 
        `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : 
        '0, 0, 0';
}

// Add after other map control event listeners
document.getElementById('toggle-routes').addEventListener('click', toggleRouteVisibility);