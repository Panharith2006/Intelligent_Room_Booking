// Room feature initialization - supports inline HTML implementations
document.addEventListener('DOMContentLoaded', function() {
    const roomTypeSelect = document.getElementById('room-type');
    const capacitySelect = document.getElementById('capacity');

    // Add change listeners to trigger search automatically
    if (roomTypeSelect) {
        roomTypeSelect.addEventListener('change', function() {
            if (typeof searchRooms === 'function') {
                searchRooms();
            }
        });
    }
    
    if (capacitySelect) {
        capacitySelect.addEventListener('change', function() {
            if (typeof searchRooms === 'function') {
                searchRooms();
            }
        });
    }
});
