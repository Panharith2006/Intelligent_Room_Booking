document.addEventListener('DOMContentLoaded', function() {
    initializeBooki    .then(data => {
        if (data.rooms) {
            data.rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room.id;
                option.textContent = `${room.room_number} - ${room.name} (${room.capacity} people)`;
                roomSelect.appendChild(option);
            });
            
            // Check if there's a pending room selection for autofill
            if (window.pendingRoomSelection) {
                roomSelect.value = window.pendingRoomSelection;
                roomSelect.dispatchEvent(new Event('change'));
                window.pendingRoomSelection = null; // Clear the pending selection
            }
        }
    })
});

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initializeBookingPage() {
    // Form validation
    const form = document.getElementById('bookingForm');
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, select, textarea');
    
    // Add real-time validation
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearErrors);
    });
    
    // Initialize building/room dropdown
    initializeBuildingRoomDropdown();
    
    // Initialize date/time validation
    initializeDateTimeValidation();
    
    // Add availability checking
    initializeAvailabilityChecking();
    
    // Form submission
    form.addEventListener('submit', handleFormSubmission);
    
    // Show success modal if there are success messages
    showSuccessModalIfNeeded();
    
    // URL parameter handling for autofill
    handleURLParameters();
}

function initializeBuildingRoomDropdown() {
    const buildingSelect = document.getElementById('buildingSelect');
    const roomSelect = document.getElementById('roomSelect');
    
    if (buildingSelect && roomSelect) {
        buildingSelect.addEventListener('change', function() {
            const buildingId = this.value;
            updateRoomOptions(buildingId, roomSelect);
        });
    }
}

function updateRoomOptions(buildingId, roomSelect) {
    // Clear existing options
    roomSelect.innerHTML = '<option value="">Select a room</option>';
    
    if (!buildingId) return;
    
    // Make AJAX call to get rooms for the selected building
    fetch(`/accounts/ajax/get-rooms/?building_id=${buildingId}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.rooms) {
            data.rooms.forEach(room => {
                const option = document.createElement('option');
                option.value = room.id;
                option.textContent = `${room.room_number} - ${room.name} (${room.capacity} seats)`;
                roomSelect.appendChild(option);
            });
        }
    })
    .catch(error => {
        console.error('Error fetching rooms:', error);
        // Fallback to static data
        const fallbackRooms = {
            '1': [
                { id: 1, name: 'Lecture Hall A', capacity: 100 },
                { id: 2, name: 'Classroom 201', capacity: 40 }
            ],
            '2': [
                { id: 3, name: 'Computer Lab 1', capacity: 30 },
                { id: 4, name: 'Computer Lab 2', capacity: 25 }
            ],
            '3': [
                { id: 5, name: 'Study Room 1', capacity: 8 },
                { id: 6, name: 'Conference Room', capacity: 20 }
            ]
        };
        
        const rooms = fallbackRooms[buildingId] || [];
        rooms.forEach(room => {
            const option = document.createElement('option');
            option.value = room.id;
            option.textContent = `${room.name} (${room.capacity} people)`;
            roomSelect.appendChild(option);
        });
    });
}

function initializeDateTimeValidation() {
    const dateInput = document.getElementById('dateInput');
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    
    if (dateInput) {
        // Set minimum date to today
        const today = new Date().toISOString().split('T')[0];
        dateInput.min = today;
        
        // Set default to today if empty
        if (!dateInput.value) {
            dateInput.value = today;
        }
    }
    
    if (startTimeInput && endTimeInput) {
        startTimeInput.addEventListener('change', validateTimeRange);
        endTimeInput.addEventListener('change', validateTimeRange);
    }
}

function validateTimeRange() {
    const startTime = document.getElementById('startTime')?.value;
    const endTime = document.getElementById('endTime')?.value;
    
    if (startTime && endTime) {
        if (startTime >= endTime) {
            showError('End time must be after start time');
            return false;
        }
        
        // Check if duration is reasonable (max 4 hours)
        const start = new Date(`2000-01-01T${startTime}`);
        const end = new Date(`2000-01-01T${endTime}`);
        const diffHours = (end - start) / (1000 * 60 * 60);
        
        if (diffHours > 4) {
            showError('Maximum booking duration is 4 hours');
            return false;
        }
    }
    
    return true;
}

function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    
    // Remove existing error styling
    field.classList.remove('error');
    
    // Validate required fields
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Validate email format
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            showFieldError(field, 'Please enter a valid email address');
            return false;
        }
    }
    
    return true;
}

function showFieldError(field, message) {
    field.classList.add('error');
    
    // Remove existing error message
    const existingError = field.parentNode.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    // Add new error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    field.parentNode.insertBefore(errorDiv, field.nextSibling);
}

function clearErrors(e) {
    const field = e.target;
    field.classList.remove('error');
    const errorMsg = field.parentNode.querySelector('.error-message');
    if (errorMsg) {
        errorMsg.remove();
    }
}

function showError(message) {
    console.error(message);
    // Create a temporary notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #e74c3c;
        color: white;
        padding: 15px 20px;
        border-radius: 5px;
        z-index: 1000;
        font-size: 14px;
        max-width: 300px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function handleFormSubmission(e) {
    e.preventDefault();
    
    // Validate all fields
    const form = e.target;
    const inputs = form.querySelectorAll('input, select, textarea');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!validateField({ target: input })) {
            isValid = false;
        }
    });
    
    // Validate time range
    if (!validateTimeRange()) {
        isValid = false;
    }
    
    if (isValid) {
        // Show loading state
        showLoading();
        
        // Submit the form
        form.submit();
    }
}

function showLoading() {
    const submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }
}

function hideLoading() {
    const submitBtn = document.querySelector('button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-calendar-plus"></i> Book Room';
    }
}

// Success modal functions
function showSuccessModal() {
    const modal = document.getElementById('successModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeSuccessModal() {
    const modal = document.getElementById('successModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function showSuccessModalIfNeeded() {
    // Check for Django messages in the page
    const messageElements = document.querySelectorAll('.alert-success, .message.success, .alert.alert-success');
    
    // Also check for any message containing success-related text
    const allMessages = document.querySelectorAll('.alert, .message');
    let hasSuccessMessage = false;
    
    allMessages.forEach(message => {
        const text = message.textContent.toLowerCase();
        if (text.includes('success') || text.includes('booked') || text.includes('confirmed')) {
            hasSuccessMessage = true;
        }
    });
    
    if (messageElements.length > 0 || hasSuccessMessage) {
        setTimeout(() => {
            showSuccessModal();
        }, 500);
    }
}

// Add real-time availability checking
function checkAvailability() {
    const roomSelect = document.getElementById('roomSelect');
    const dateInput = document.getElementById('bookingDate');
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    
    if (!roomSelect || !dateInput || !startTimeInput || !endTimeInput) return;
    
    const roomId = roomSelect.value;
    const date = dateInput.value;
    const startTime = startTimeInput.value;
    const endTime = endTimeInput.value;
    
    if (!roomId || !date || !startTime || !endTime) return;
    
    // Show loading indicator
    const availabilityDiv = document.getElementById('availabilityStatus') || createAvailabilityDiv();
    availabilityDiv.innerHTML = '<div class="availability-loading">Checking availability...</div>';
    
    // Make AJAX call to check availability
    fetch('/accounts/ajax/check-availability/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            room_id: roomId,
            date: date,
            start_time: startTime,
            end_time: endTime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.available) {
            availabilityDiv.innerHTML = '<div class="availability-success">✓ Room is available</div>';
            enableSubmitButton();
        } else {
            availabilityDiv.innerHTML = `<div class="availability-error">✗ ${data.message}</div>`;
            disableSubmitButton();
        }
    })
    .catch(error => {
        console.error('Error checking availability:', error);
        availabilityDiv.innerHTML = '<div class="availability-error">Error checking availability</div>';
        enableSubmitButton(); // Allow submission despite error
    });
}

function createAvailabilityDiv() {
    const div = document.createElement('div');
    div.id = 'availabilityStatus';
    div.className = 'availability-status';
    
    const form = document.getElementById('bookingForm');
    const submitButton = form.querySelector('button[type="submit"]');
    form.insertBefore(div, submitButton);
    
    return div;
}

function enableSubmitButton() {
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = false;
        submitButton.style.opacity = '1';
    }
}

function disableSubmitButton() {
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.style.opacity = '0.5';
    }
}

function initializeAvailabilityChecking() {
    const roomSelect = document.getElementById('roomSelect');
    const dateInput = document.getElementById('bookingDate');
    const startTimeInput = document.getElementById('startTime');
    const endTimeInput = document.getElementById('endTime');
    
    if (roomSelect && dateInput && startTimeInput && endTimeInput) {
        // Add event listeners for real-time checking
        roomSelect.addEventListener('change', checkAvailability);
        dateInput.addEventListener('change', checkAvailability);
        startTimeInput.addEventListener('change', checkAvailability);
        endTimeInput.addEventListener('change', checkAvailability);
    }
}

// URL parameter handling for autofill
function handleURLParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Autofill room
    const roomId = urlParams.get('room_id');
    if (roomId) {
        // Need to find the building for this room first
        autofillRoomAndBuilding(roomId);
    }
    
    // Autofill date
    const date = urlParams.get('date');
    if (date) {
        const dateInput = document.getElementById('dateInput');
        if (dateInput) {
            dateInput.value = date;
            dateInput.dispatchEvent(new Event('change'));
        }
    }
    
    // Autofill time
    const time = urlParams.get('time');
    if (time) {
        const timeInput = document.getElementById('startTime');
        if (timeInput) {
            timeInput.value = time;
            timeInput.dispatchEvent(new Event('change'));
        }
    }
    
    // If any parameters were found, show a notification
    if (roomId || date || time) {
        showAutofillNotification();
    }
}

function autofillRoomAndBuilding(roomId) {
    // First, fetch the room details to find its building
    fetch(`/accounts/ajax/get-room-details/?room_id=${roomId}`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.room) {
            const buildingSelect = document.getElementById('buildingSelect');
            const roomSelect = document.getElementById('roomSelect');
            
            if (buildingSelect && roomSelect) {
                // Set the building
                buildingSelect.value = data.room.building_id;
                buildingSelect.dispatchEvent(new Event('change'));
                
                // Wait for rooms to load, then set the room
                setTimeout(() => {
                    const roomOption = roomSelect.querySelector(`option[value="${roomId}"]`);
                    if (roomOption) {
                        roomSelect.value = roomId;
                        roomSelect.dispatchEvent(new Event('change'));
                    }
                }, 500);
            }
        }
    })
    .catch(error => {
        console.error('Error fetching room details:', error);
        // Fallback: try to find the room in the existing options
        autofillRoomWhenAvailable(roomId);
    });
}

function autofillRoomWhenAvailable(roomId) {
    // Store the room ID to select once rooms are loaded
    window.pendingRoomSelection = roomId;
    
    // Try to find the room in available rooms and select its building
    // This will be handled when building/room dropdowns are populated
}

function showAutofillNotification() {
    const notification = document.createElement('div');
    notification.className = 'autofill-notification';
    notification.innerHTML = `
        <div class="alert alert-info alert-dismissible fade show" role="alert">
            <i class="fas fa-info-circle"></i> 
            Booking form has been pre-filled with your selected room details.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(notification, container.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Add dynamic styling
const style = document.createElement('style');
style.textContent = `
    .error {
        border-color: #e74c3c !important;
        box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.2);
    }
    
    .error-message {
        color: #e74c3c;
        font-size: 0.875rem;
        margin-top: 0.25rem;
        display: block;
    }
    
    .success {
        border-color: #27ae60 !important;
        box-shadow: 0 0 0 2px rgba(39, 174, 96, 0.2);
    }
    
    .loading {
        opacity: 0.6;
        pointer-events: none;
    }
    
    .fade-in {
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .checking {
        position: relative;
    }
    
    .checking::after {
        content: '';
        position: absolute;
        top: 50%;
        right: 10px;
        width: 16px;
        height: 16px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        transform: translateY(-50%);
    }
    
    @keyframes spin {
        0% { transform: translateY(-50%) rotate(0deg); }
        100% { transform: translateY(-50%) rotate(360deg); }
    }
`;
document.head.appendChild(style);