let bookingToCancel = null;

function editBooking(bookingId) {
    // Redirect to edit booking page
    window.location.href = `/accounts/edit-booking/${bookingId}/`;
}

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
                'Content-Type': 'application/json',
            },
        })
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
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

// Print booking details
function printBooking() {
    window.print();
}

// Add smooth animations
document.addEventListener('DOMContentLoaded', function() {
    // Animate info sections
    const sections = document.querySelectorAll('.info-section');
    sections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(20px)';
        setTimeout(() => {
            section.style.transition = 'all 0.5s ease';
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // Add button click animations
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
});