// Enhanced room search functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeFeatureRoom();
});

function initializeFeatureRoom() {
    initializeFilters();
    initializeBookingModal();
    setDateDefaults();
    displayRooms();
}

function initializeFilters() {
    const roomTypeSelect = document.getElementById('room-type');
    const capacitySelect = document.getElementById('capacity');
    const dateInput = document.getElementById('date');
    const timeSelect = document.getElementById('time');

    if (roomTypeSelect) roomTypeSelect.addEventListener('change', enhancedSearch);
    if (capacitySelect) capacitySelect.addEventListener('change', enhancedSearch);
    if (dateInput) dateInput.addEventListener('change', enhancedSearch);
    if (timeSelect) timeSelect.addEventListener('change', enhancedSearch);
}

function initializeBookingModal() {
    console.log('Booking modal initialized');
}

function setDateDefaults() {
    const dateInput = document.getElementById('date');
    if (dateInput) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;
    }
}

function displayRooms(filteredRooms = null) {
    const roomsContainer = document.getElementById('rooms-container');
    if (!roomsContainer) return;
    
    const roomsToDisplay = filteredRooms || rooms || [];
    
    if (roomsToDisplay.length === 0) {
        roomsContainer.innerHTML = '<p>No rooms available.</p>';
        return;
    }

    roomsContainer.innerHTML = roomsToDisplay.map(room => `
        <div class="room-card">
            <h3>${room.name || 'Room'}</h3>
            <p>Capacity: ${room.capacity || 'N/A'}</p>
            <button onclick="viewRoomDetails(${room.id})">View Details</button>
        </div>
    `).join('');
}

function enhancedSearch() {
    const roomType = document.getElementById('room-type')?.value || '';
    const capacity = document.getElementById('capacity')?.value || '';
    
    if (!window.rooms) return;
    
    let filtered = window.rooms.filter(room => {
        if (roomType && room.type !== roomType) return false;
        if (capacity && room.capacity < parseInt(capacity)) return false;
        return true;
    });

    displayRooms(filtered);
}

function viewRoomDetails(roomId) {
    console.log('View room details:', roomId);
    if (!window.rooms) return;
    
    const room = window.rooms.find(r => r.id === roomId);
    if (room) {
        const modal = document.getElementById('quickBookingModal');
        if (modal) {
            modal.setAttribute('data-room-id', roomId);
            modal.style.display = 'block';
        }
    }
}

// Make functions globally available
window.enhancedSearch = enhancedSearch;
window.viewRoomDetails = viewRoomDetails;
window.displayRooms = displayRooms;
