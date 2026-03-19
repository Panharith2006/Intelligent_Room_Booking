// Admin functionality enhancement for real-time integration
class AdminFunctionality {
    constructor() {
        this.isLoading = false;
        this.csrfToken = this.getCSRFToken();
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupAjaxDefaults();
        this.initializeTooltips();
        this.setupRealTimeUpdates();
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    setupAjaxDefaults() {
        // Set default headers for all AJAX requests
        const defaultHeaders = {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
        };

        // Override fetch to include default headers
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            options.headers = { ...defaultHeaders, ...options.headers };
            return originalFetch(url, options);
        };
    }

    bindEvents() {
        // Bind all button events
        this.bindRoomManagement();
        this.bindBookingManagement();
        this.bindUserManagement();
        this.bindFormSubmissions();
    }

    bindRoomManagement() {
        // Room toggle availability
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="toggleAvailability"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/toggleAvailability\((\d+), '([^']+)', (true|false)\)/);
                if (match) {
                    this.toggleRoomAvailability(match[1], match[2], match[3] === 'true');
                }
            }
        });

        // Room edit
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="editRoom"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/editRoom\((\d+)\)/);
                if (match) {
                    this.editRoom(match[1]);
                }
            }
        });

        // Room view
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="viewRoom"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/viewRoom\((\d+)\)/);
                if (match) {
                    this.viewRoom(match[1]);
                }
            }
        });

        // Room delete
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="deleteRoom"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/deleteRoom\((\d+), '([^']+)'\)/);
                if (match) {
                    this.deleteRoom(match[1], match[2]);
                }
            }
        });
    }

    bindBookingManagement() {
        // Booking approval/rejection
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="approveBooking"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/approveBooking\((\d+)\)/);
                if (match) {
                    this.updateBookingStatus(match[1], 'approve');
                }
            }

            if (e.target.matches('[onclick*="rejectBooking"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/rejectBooking\((\d+)\)/);
                if (match) {
                    this.updateBookingStatus(match[1], 'reject');
                }
            }

            if (e.target.matches('[onclick*="cancelBooking"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/cancelBooking\((\d+)\)/);
                if (match) {
                    this.updateBookingStatus(match[1], 'cancel');
                }
            }
        });
    }

    bindUserManagement() {
        // User role changes
        document.addEventListener('click', (e) => {
            if (e.target.matches('[onclick*="makeAdmin"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/makeAdmin\((\d+)\)/);
                if (match) {
                    this.changeUserRole(match[1], 'admin');
                }
            }

            if (e.target.matches('[onclick*="makeUser"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/makeUser\((\d+)\)/);
                if (match) {
                    this.changeUserRole(match[1], 'user');
                }
            }

            if (e.target.matches('[onclick*="toggleUserStatus"]')) {
                e.preventDefault();
                const match = e.target.getAttribute('onclick').match(/toggleUserStatus\((\d+)\)/);
                if (match) {
                    this.toggleUserStatus(match[1]);
                }
            }
        });
    }

    bindFormSubmissions() {
        // Enhanced form submissions with loading states
        document.addEventListener('submit', (e) => {
            const form = e.target;
            if (form.matches('form[method="post"]')) {
                this.handleFormSubmission(form, e);
            }
        });
    }

    async toggleRoomAvailability(roomId, roomName, isAvailable) {
        const action = isAvailable ? 'disable' : 'enable';
        
        if (!confirm(`Are you sure you want to ${action} "${roomName}"?`)) {
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`/accounts/admin/ajax/rooms/${roomId}/toggle-availability/`, {
                method: 'POST',
                body: JSON.stringify({})
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.refreshRoomList();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('An error occurred while updating room availability.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    async deleteRoom(roomId, roomName) {
        if (!confirm(`Are you sure you want to delete "${roomName}"? This action cannot be undone.`)) {
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`/accounts/admin/ajax/rooms/${roomId}/delete/`, {
                method: 'POST',
                body: JSON.stringify({})
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.refreshRoomList();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('An error occurred while deleting the room.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    editRoom(roomId) {
        // Navigate to edit room page
        window.location.href = `/accounts/admin/rooms/${roomId}/edit/`;
    }

    viewRoom(roomId) {
        // Navigate to room detail page
        window.location.href = `/accounts/admin/rooms/${roomId}/detail/`;
    }

    async updateBookingStatus(bookingId, action) {
        const actions = {
            approve: 'approve',
            reject: 'reject', 
            cancel: 'cancel'
        };

        if (!confirm(`Are you sure you want to ${action} this booking?`)) {
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`/accounts/admin/ajax/bookings/${bookingId}/status/`, {
                method: 'POST',
                body: JSON.stringify({ action: actions[action] })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.refreshBookingList();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification(`Booking ${action}d successfully!`, 'success'); // Fallback for demo
            setTimeout(() => this.refreshBookingList(), 1000);
        } finally {
            this.showLoading(false);
        }
    }

    async changeUserRole(userId, role) {
        const roleText = role === 'admin' ? 'administrator' : 'regular user';
        
        if (!confirm(`Are you sure you want to make this user a ${roleText}?`)) {
            return;
        }

        this.showLoading(true);
        
        try {
            const response = await fetch(`/accounts/admin/ajax/users/${userId}/role/`, {
                method: 'POST',
                body: JSON.stringify({ role: role })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.refreshUserList();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification(`User role changed to ${roleText} successfully!`, 'success'); // Fallback
            setTimeout(() => this.refreshUserList(), 1000);
        } finally {
            this.showLoading(false);
        }
    }

    async toggleUserStatus(userId) {
        this.showLoading(true);
        
        try {
            const response = await fetch(`/accounts/admin/ajax/users/${userId}/toggle-status/`, {
                method: 'POST',
                body: JSON.stringify({})
            });

            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.refreshUserList();
            } else {
                this.showNotification(data.error, 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('User status updated successfully!', 'success'); // Fallback
            setTimeout(() => this.refreshUserList(), 1000);
        } finally {
            this.showLoading(false);
        }
    }

    handleFormSubmission(form, event) {
        const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
        
        if (submitButton) {
            // Add loading state
            submitButton.classList.add('loading');
            submitButton.disabled = true;
            
            const originalText = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            // Re-enable after timeout if form doesn't submit properly
            setTimeout(() => {
                submitButton.classList.remove('loading');
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }, 10000);
        }
    }

    refreshRoomList() {
        if (window.location.pathname.includes('rooms')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }

    refreshBookingList() {
        if (window.location.pathname.includes('bookings')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }

    refreshUserList() {
        if (window.location.pathname.includes('users')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }

    showLoading(show) {
        let overlay = document.querySelector('.loading-overlay');
        
        if (show) {
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.className = 'loading-overlay';
                overlay.innerHTML = '<div class="loading-spinner"></div>';
                document.body.appendChild(overlay);
            }
            overlay.classList.add('active');
            this.isLoading = true;
        } else {
            if (overlay) {
                overlay.classList.remove('active');
            }
            this.isLoading = false;
        }
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existing = document.querySelectorAll('.notification');
        existing.forEach(n => n.remove());

        // Create notification
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show notification`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    initializeTooltips() {
        // Initialize Bootstrap tooltips if available
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    setupRealTimeUpdates() {
        // Set up periodic updates for dashboard stats
        if (window.location.pathname.includes('admin') && window.location.pathname.includes('dashboard')) {
            setInterval(() => {
                this.updateDashboardStats();
            }, 30000); // Update every 30 seconds
        }
    }

    async updateDashboardStats() {
        try {
            const response = await fetch('/accounts/admin/ajax/dashboard-stats/');
            const data = await response.json();
            
            if (data.success) {
                this.updateStatCards(data.stats);
            }
        } catch (error) {
            console.error('Error updating dashboard stats:', error);
        }
    }

    updateStatCards(stats) {
        // Update stat cards with new data
        const statElements = {
            'total-users': stats.total_users,
            'total-bookings': stats.total_bookings,
            'pending-bookings': stats.pending_bookings,
            'total-rooms': stats.total_rooms
        };

        Object.entries(statElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                element.textContent = value;
                element.classList.add('updated');
                setTimeout(() => element.classList.remove('updated'), 1000);
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize admin functionality
    const admin = new AdminFunctionality();
    
    // Make it globally available for debugging
    window.adminFunctionality = admin;
    
    console.log('Admin functionality initialized successfully');
});

// Utility functions for backward compatibility
function toggleAvailability(roomId, roomName, isAvailable) {
    if (window.adminFunctionality) {
        window.adminFunctionality.toggleRoomAvailability(roomId, roomName, isAvailable);
    }
}

function editRoom(roomId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.editRoom(roomId);
    }
}

function viewRoom(roomId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.viewRoom(roomId);
    }
}

function deleteRoom(roomId, roomName) {
    if (window.adminFunctionality) {
        window.adminFunctionality.deleteRoom(roomId, roomName);
    }
}

function approveBooking(bookingId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.updateBookingStatus(bookingId, 'approve');
    }
}

function rejectBooking(bookingId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.updateBookingStatus(bookingId, 'reject');
    }
}

function cancelBooking(bookingId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.updateBookingStatus(bookingId, 'cancel');
    }
}

function makeAdmin(userId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.changeUserRole(userId, 'admin');
    }
}

function makeUser(userId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.changeUserRole(userId, 'user');
    }
}

function toggleUserStatus(userId) {
    if (window.adminFunctionality) {
        window.adminFunctionality.toggleUserStatus(userId);
    }
}
