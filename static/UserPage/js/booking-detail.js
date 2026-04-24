let bookingToCancel = null;
let cancellationInProgress = false;

function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.getAttribute('content')) {
        return meta.getAttribute('content');
    }

    const formToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (formToken && formToken.value) {
        return formToken.value;
    }

    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrftoken=')) {
            return decodeURIComponent(cookie.substring('csrftoken='.length));
        }
    }

    return null;
}

function openCancelModal() {
    const modal = document.getElementById('cancelModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeCancelModal() {
    const modal = document.getElementById('cancelModal');
    if (modal) {
        modal.style.display = 'none';
        modal.removeAttribute('data-booking-id');
    }
    bookingToCancel = null;
}

function submitCancelFallback(bookingId, csrfToken) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/accounts/booking/${bookingId}/cancel/`;

    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);

    document.body.appendChild(form);
    form.submit();
}

function cancelBooking(bookingId) {
    if (!bookingId) {
        alert('Invalid booking selected for cancellation.');
        return;
    }

    const cancelButton = document.querySelector(`button[data-booking-id="${bookingId}"]`);
    if (!cancelButton) {
        alert('Unable to start cancellation. Please refresh and try again.');
        return;
    }

    const startTimeStr = cancelButton.getAttribute('data-start-time');
    if (startTimeStr) {
        const startTime = new Date(startTimeStr);
        const now = new Date();
        const hoursUntilBooking = (startTime - now) / (1000 * 60 * 60);

        if (hoursUntilBooking <= 0) {
            alert('Cannot cancel booking that has already started.');
            return;
        }

        if (hoursUntilBooking < 3) {
            const proceed = confirm('This is a late cancellation (less than 3 hours before start). A penalty record may be added. Continue?');
            if (!proceed) {
                return;
            }
        }
    }

    bookingToCancel = bookingId;
    const modal = document.getElementById('cancelModal');
    if (modal) {
        modal.setAttribute('data-booking-id', String(bookingId));
    }
    openCancelModal();
}

async function confirmCancel() {
    if (cancellationInProgress) {
        return;
    }

    const modal = document.getElementById('cancelModal');
    const modalBookingId = modal ? modal.getAttribute('data-booking-id') : null;
    const targetBookingId = bookingToCancel || modalBookingId;

    if (!targetBookingId) {
        alert('No booking selected for cancellation. Please try again.');
        return;
    }

    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        alert('Security token missing. Please refresh the page and try again.');
        return;
    }

    const confirmBtn = document.querySelector('#cancelModal .btn.btn-danger');
    cancellationInProgress = true;
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Cancelling...';
    }

    try {
        const response = await fetch(`/accounts/booking/${targetBookingId}/cancel/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        });

        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            submitCancelFallback(targetBookingId, csrfToken);
            return;
        }

        const data = await response.json();
        if (!response.ok || !data.success) {
            throw new Error(data.message || 'Failed to cancel booking.');
        }

        alert(data.message || 'Booking cancelled successfully.');
        window.location.reload();
    } catch (error) {
        alert(`Error cancelling booking: ${error.message}`);
    } finally {
        cancellationInProgress = false;
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Yes, Cancel';
        }
        closeCancelModal();
    }
}

function printBooking() {
    window.print();
}

document.addEventListener('DOMContentLoaded', function() {
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

    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });

    window.addEventListener('click', function(event) {
        const modal = document.getElementById('cancelModal');
        if (event.target === modal) {
            closeCancelModal();
        }
    });

    window.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeCancelModal();
        }
    });
});

window.cancelBooking = cancelBooking;
window.closeCancelModal = closeCancelModal;
window.confirmCancel = confirmCancel;
window.printBooking = printBooking;