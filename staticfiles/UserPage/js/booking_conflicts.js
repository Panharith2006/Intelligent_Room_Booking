// Booking conflict prevention JavaScript
function checkBookingAvailability() {
    const roomId = document.getElementById('id_room').value;
    const startTime = document.getElementById('id_start_time').value;
    const endTime = document.getElementById('id_end_time').value;
    const date = document.getElementById('id_date').value;
    
    if (!roomId || !startTime || !endTime || !date) {
        return; // Don't check if not all fields are filled
    }
    
    // Clear previous messages
    clearAvailabilityMessages();
    
    // Make AJAX request to check availability
    fetch('/booking/api/check-room-availability-ajax/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            room_id: roomId,
            start_time: startTime,
            end_time: endTime,
            date: date
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.available) {
            showAvailabilityMessage('✓ Room is available for the selected time!', 'success');
        } else {
            let message = '⚠ Room is not available: ' + data.reason;
            if (data.conflicts && data.conflicts.length > 0) {
                message += '\n\nConflicting bookings:';
                data.conflicts.forEach(conflict => {
                    message += `\n• ${conflict.user} (${conflict.start_time} - ${conflict.end_time})`;
                });
            }
            if (data.alternative_slots && data.alternative_slots.length > 0) {
                message += '\n\nSuggested available slots:';
                data.alternative_slots.forEach(slot => {
                    message += `\n• ${slot.start_time} - ${slot.end_time}`;
                });
            }
            showAvailabilityMessage(message, 'error');
        }
    })
    .catch(error => {
        console.error('Error checking availability:', error);
        showAvailabilityMessage('Error checking availability. Please try again.', 'error');
    });
}

function showAvailabilityMessage(message, type) {
    let messageDiv = document.getElementById('availability-message');
    if (!messageDiv) {
        messageDiv = document.createElement('div');
        messageDiv.id = 'availability-message';
        messageDiv.style.padding = '10px';
        messageDiv.style.margin = '10px 0';
        messageDiv.style.borderRadius = '5px';
        messageDiv.style.whiteSpace = 'pre-line';
        
        // Insert after the form or at a suitable location
        const form = document.querySelector('form');
        if (form) {
            form.insertBefore(messageDiv, form.firstChild);
        }
    }
    
    messageDiv.textContent = message;
    if (type === 'success') {
        messageDiv.style.backgroundColor = '#d4edda';
        messageDiv.style.color = '#155724';
        messageDiv.style.border = '1px solid #c3e6cb';
    } else {
        messageDiv.style.backgroundColor = '#f8d7da';
        messageDiv.style.color = '#721c24';
        messageDiv.style.border = '1px solid #f5c6cb';
    }
}

function clearAvailabilityMessages() {
    const messageDiv = document.getElementById('availability-message');
    if (messageDiv) {
        messageDiv.remove();
    }
}

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

// Set up event listeners when the page loads
document.addEventListener('DOMContentLoaded', function() {
    const roomField = document.getElementById('id_room');
    const startTimeField = document.getElementById('id_start_time');
    const endTimeField = document.getElementById('id_end_time');
    const dateField = document.getElementById('id_date');
    
    if (roomField) roomField.addEventListener('change', checkBookingAvailability);
    if (startTimeField) startTimeField.addEventListener('change', checkBookingAvailability);
    if (endTimeField) endTimeField.addEventListener('change', checkBookingAvailability);
    if (dateField) dateField.addEventListener('change', checkBookingAvailability);
    
    // Also check when user stops typing (for time fields)
    if (startTimeField) startTimeField.addEventListener('blur', checkBookingAvailability);
    if (endTimeField) endTimeField.addEventListener('blur', checkBookingAvailability);
});
