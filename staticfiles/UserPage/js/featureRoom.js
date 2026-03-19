// Enhanced room search functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeFeatureRoom();
});

function initializeFeatureRoom() {
    // Initialize all event listeners
    initializeFilters();
    // Note: displayRooms is called from inline script in HTML template
}

function initializeFilters() {
    const roomTypeSelect = document.getElementById('room-type');
    const capacitySelect = document.getElementById('capacity');
    const availabilitySelect = document.getElementById('availability');
    const dateInput = document.getElementById('date');
    const timeSelect = document.getElementById('time');

    if (roomTypeSelect) roomTypeSelect.addEventListener('change', enhancedSearch);
    if (capacitySelect) capacitySelect.addEventListener('change', enhancedSearch);
    if (availabilitySelect) availabilitySelect.addEventListener('change', enhancedSearch);
    if (dateInput) dateInput.addEventListener('change', enhancedSearch);
    if (timeSelect) timeSelect.addEventListener('change', enhancedSearch);
}

function enhancedSearch() {
    const roomType = document.getElementById('room-type')?.value || '';
    const capacity = document.getElementById('capacity')?.value || '';
    const availability = document.getElementById('availability')?.value || '';

    // Show loading state
    showLoading();

    // Simulate API call delay
    setTimeout(() => {
        let filteredRooms = rooms.filter(room => {
            if (roomType && room.type !== roomType) return false;
            if (capacity) {
                const [min, max] = capacity.includes('+') ? [51, Infinity] : capacity.split('-').map(Number);
                if (room.capacity < min || (max && room.capacity > max)) return false;
            }
            if (availability === 'available' && !room.available) return false;
            if (availability === 'unavailable' && room.available) return false;
            return true;
        });

        currentRooms = filteredRooms;
        displayRooms(filteredRooms);
        hideLoading();
        
        // Show results message
        if (filteredRooms.length > 0) {
            showToast(`Found ${filteredRooms.length} room(s) matching your criteria`, 'success');
        } else {
            showToast('No rooms found matching your criteria', 'warning');
        }
    }, 1000);
}

// Loading state management
function showLoading() {
    const grid = document.getElementById('rooms-grid');
    grid.innerHTML = '<div class="loading-spinner">Searching rooms...</div>';
}

function hideLoading() {
    // Loading will be hidden when displayRooms is called
}

// Enhanced room card with animations
function createRoomCard(room) {
    const roomCard = document.createElement('div');
    roomCard.className = 'room-card';
    roomCard.style.opacity = '0';
    roomCard.style.transform = 'translateY(20px)';
    
    roomCard.innerHTML = `
        <div class="room-image">
            <div class="room-status ${room.available ? 'available' : 'unavailable'}">
                ${room.available ? 'Available' : 'Unavailable'}
            </div>
            <div class="room-overlay">
                <button class="quick-view-btn" onclick="viewRoomDetails(${room.id})">
                    <i class="bi bi-eye"></i> Quick View
                </button>
            </div>
        </div>
        <div class="room-info">
            <h3 class="room-title">${room.name}</h3>
            <p class="room-location">
                <i class="bi bi-geo-alt"></i> ${room.location}
            </p>
            <p class="room-capacity">
                <i class="bi bi-people"></i> Capacity: ${room.capacity} people
            </p>
            <div class="room-features">
                ${room.features.map(feature => `<span class="feature-tag">${feature}</span>`).join('')}
            </div>
            <div class="room-footer">
                <button class="view-details-btn" onclick="viewRoomDetails(${room.id})">
                    <i class="bi bi-info-circle"></i> Details
                </button>
                <button class="book-btn ${room.available ? '' : 'disabled'}" 
                    ${room.available ? `onclick="redirectToBooking(${room.id})"` : 'disabled'}>
                    <i class="bi bi-calendar-check"></i>
                    ${room.available ? 'Book Now' : 'Unavailable'}
                </button>
            </div>
        </div>
    `;
    
    return roomCard;
}

// Animate room cards on load
function animateRoomCards() {
    const cards = document.querySelectorAll('.room-card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Advanced filtering with real-time updates
function setupRealTimeFiltering() {
    const filterInputs = document.querySelectorAll('#room-type, #capacity, #date, #time');
    
    filterInputs.forEach(input => {
        input.addEventListener('change', debounce(searchRooms, 300));
    });
}

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Enhanced room details with more information
function showEnhancedRoomDetails(room) {
    const modal = document.getElementById('quickBookingModal');
    const roomDetails = document.getElementById('roomDetails');
    
    roomDetails.innerHTML = `
        <div class="room-detail-header">
            <h4>${room.name}</h4>
            <span class="status-badge ${room.available ? 'available' : 'unavailable'}">
                ${room.available ? 'Available' : 'Unavailable'}
            </span>
        </div>
        
        <div class="room-detail-gallery">
            <div class="room-main-image">
                <img src="https://www.rupp.edu.kh/fe/factor4.0/images/desk_and_chairs_are_installed_beforePCarrived1.jpg" 
                     alt="${room.name}" />
            </div>
        </div>
        
        <div class="room-detail-info">
            <div class="info-grid">
                <div class="info-item">
                    <i class="bi bi-geo-alt"></i>
                    <div>
                        <strong>Location</strong>
                        <p>${room.location}</p>
                    </div>
                </div>
                <div class="info-item">
                    <i class="bi bi-people"></i>
                    <div>
                        <strong>Capacity</strong>
                        <p>${room.capacity} people</p>
                    </div>
                </div>
                <div class="info-item">
                    <i class="bi bi-tag"></i>
                    <div>
                        <strong>Type</strong>
                        <p>${room.type}</p>
                    </div>
                </div>
                <div class="info-item">
                    <i class="bi bi-info-circle"></i>
                    <div>
                        <strong>Description</strong>
                        <p>${room.description}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="room-detail-features">
            <h5><i class="bi bi-gear"></i> Features & Amenities</h5>
            <div class="features-grid">
                ${room.features.map(feature => `
                    <div class="feature-item">
                        <i class="bi bi-check-circle"></i>
                        <span>${feature}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        
        <div class="room-availability">
            <h5><i class="bi bi-calendar"></i> Availability</h5>
            <div class="availability-calendar">
                <p>Click "Book This Room" to check detailed availability</p>
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Initialize advanced features
document.addEventListener('DOMContentLoaded', function() {
    setupRealTimeFiltering();
    
    // Add smooth scrolling for all internal links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Initialize tooltips
    initializeTooltips();
    
    // Add keyboard navigation
    setupKeyboardNavigation();
});

// Tooltip initialization
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.getAttribute('data-tooltip');
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 + 'px';
    tooltip.style.top = rect.top - 40 + 'px';
    
    setTimeout(() => tooltip.classList.add('show'), 10);
}

function hideTooltip() {
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => tooltip.remove());
}

// Keyboard navigation
function setupKeyboardNavigation() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
        if (e.key === 'Enter' && e.target.classList.contains('room-card')) {
            const roomId = e.target.getAttribute('data-room-id');
            if (roomId) {
                viewRoomDetails(parseInt(roomId));
            }
        }
    });
}

// Booking redirection functions
function redirectToBooking(roomId) {
    const selectedDate = document.getElementById('date')?.value || '';
    const selectedTime = document.getElementById('time')?.value || '';
    
    // Build URL with room details for autofill
    let bookingUrl = '/accounts/booking/';
    const params = new URLSearchParams();
    
    if (roomId) params.append('room_id', roomId);
    if (selectedDate) params.append('date', selectedDate);
    if (selectedTime) params.append('time', selectedTime);
    
    if (params.toString()) {
        bookingUrl += '?' + params.toString();
    }
    
    // Redirect to booking page
    window.location.href = bookingUrl;
}

function proceedToBooking() {
    const modal = document.getElementById('quickBookingModal');
    const roomId = modal.getAttribute('data-room-id');
    
    if (roomId) {
        redirectToBooking(roomId);
    } else {
        // Fallback to general booking page
        window.location.href = '/accounts/booking/';
    }
}

// Update the viewRoomDetails function to store room ID in modal
if (!window.originalViewRoomDetails) {
    window.originalViewRoomDetails = window.viewRoomDetails;
}
function viewRoomDetails(roomId) {
    const room = rooms.find(r => r.id === roomId);
    if (room) {
        const modal = document.getElementById('quickBookingModal');
        if (modal) {
            modal.setAttribute('data-room-id', roomId);
            showEnhancedRoomDetails(room);
        }
    }
}

// Export functions for global use
window.enhancedSearch = enhancedSearch;
window.showEnhancedRoomDetails = showEnhancedRoomDetails;