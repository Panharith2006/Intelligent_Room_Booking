let bookingToCancel = null;

function cancelBooking(bookingId) {
    console.log('Cancel booking clicked for ID:', bookingId);
    
    // Get the cancel button to check the booking start time
    const cancelButton = document.querySelector(`button[data-booking-id="${bookingId}"]`);
    
    if (cancelButton) {
        const startTimeStr = cancelButton.getAttribute('data-start-time');
        console.log('Start time string:', startTimeStr);
        
        const startTime = new Date(startTimeStr);
        const currentTime = new Date();
        const hoursUntilBooking = (startTime - currentTime) / (1000 * 60 * 60);
        
        console.log('Start time:', startTime);
        console.log('Current time:', currentTime);
        console.log('Hours until booking:', hoursUntilBooking);
        
        // Check 24-hour rule
        if (hoursUntilBooking < 24) {
            if (hoursUntilBooking <= 0) {
                alert('Cannot cancel booking that has already started.');
            } else {
                alert(`Cannot cancel booking. Must cancel at least 24 hours in advance. Only ${hoursUntilBooking.toFixed(1)} hours remaining.`);
            }
            return;
        }
    } else {
        console.log('Cancel button not found, proceeding without time check');
    }
    
    bookingToCancel = bookingId;
    const modal = document.getElementById('cancelModal');
    if (modal) {
        modal.style.display = 'block';
        console.log('Cancel modal displayed');
    } else {
        console.error('Cancel modal not found!');
    }
}

function closeCancelModal() {
    document.getElementById('cancelModal').style.display = 'none';
    bookingToCancel = null;
}

function confirmCancel() {
    console.log('Confirming cancel for booking:', bookingToCancel);
    
    if (bookingToCancel) {
        // Send AJAX request to cancel booking
        fetch(`/accounts/booking/${bookingToCancel}/cancel/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            },
        })
        .then(response => {
            console.log('Response status:', response.status);
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                return response.text().then(text => {
                    console.log('Received HTML instead of JSON:', text.substring(0, 200));
                    throw new Error('Server returned HTML instead of JSON');
                });
            }
        })
        .then(data => {
            console.log('Response data:', data);
            if (data.success) {
                // Show success message
                alert(data.message);
                // Refresh the page to show updated status
                location.reload();
            } else {
                alert('Error cancelling booking: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error cancelling booking. Please try again.');
        });
    }
    closeCancelModal();
}

// 👁️ View Booking Details Function
function viewBooking(bookingId) {
    console.log('View booking clicked for ID:', bookingId);
    // Redirect to the booking details page
    window.location.href = `/accounts/booking-detail/${bookingId}/`;
}

// 📋 NEW: Show booking details in modal (alternative to redirect)
function showBookingDetailsModal(booking) {
    const modal = document.getElementById('detailsModal');
    if (!modal) {
        // Create modal if it doesn't exist
        createBookingDetailsModal();
    }
    
    // Fill modal with booking details
    document.getElementById('detailsContent').innerHTML = `
        <h3>${booking.room_name}</h3>
        <div class="detail-item"><strong>Room Number:</strong> ${booking.room_number}</div>
        <div class="detail-item"><strong>Date:</strong> ${booking.date}</div>
        <div class="detail-item"><strong>Time:</strong> ${booking.start_time} - ${booking.end_time}</div>
        <div class="detail-item"><strong>Purpose:</strong> ${booking.purpose}</div>
        <div class="detail-item"><strong>Status:</strong> ${booking.status}</div>
        <div class="detail-item"><strong>Created:</strong> ${booking.created_at}</div>
    `;
    
    document.getElementById('detailsModal').style.display = 'block';
}

// 🆕 NEW: Create booking details modal dynamically
function createBookingDetailsModal() {
    const modalHTML = `
        <div id="detailsModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Booking Details</h2>
                    <span class="close" onclick="closeDetailsModal()">&times;</span>
                </div>
                <div class="modal-body" id="detailsContent">
                    <!-- Details will be filled here -->
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="closeDetailsModal()">Close</button>
                </div>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

// 🔒 NEW: Close details modal
function closeDetailsModal() {
    document.getElementById('detailsModal').style.display = 'none';
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

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('cancelModal');
    if (event.target === modal) {
        closeCancelModal();
    }
}

// Add smooth scrolling for better UX
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 Booked.js loaded successfully!');
    console.log('📊 Found booking cards:', document.querySelectorAll('.booking-card').length);
    console.log('🎯 Found cancel buttons:', document.querySelectorAll('button[data-booking-id]').length);
    console.log('👁️ Found view buttons:', document.querySelectorAll('button[onclick*="viewBooking"]').length);
    
    // Add loading animation for buttons
    const buttons = document.querySelectorAll('button');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (!this.classList.contains('cancel-btn')) {
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = '';
                }, 150);
            }
        });
    });
});