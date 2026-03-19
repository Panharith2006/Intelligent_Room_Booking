// Updated Admin Functions with proper template integration
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all admin functions
    initializeUserManagement();
    initializeRoomManagement();
    initializeSearch();
    initializeFilters();
    setupEventListeners();
    
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// User Management Functions
function initializeUserManagement() {
    // Add event listeners for user action buttons
    document.querySelectorAll('.btn-make-admin').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            changeRole(userId, 'make_admin');
        });
    });
    
    document.querySelectorAll('.btn-make-user').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            changeRole(userId, 'make_user');
        });
    });
    
    document.querySelectorAll('.btn-toggle-status').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.dataset.userId;
            toggleStatus(userId, 'toggle_active');
        });
    });
}

function changeRole(userId, action) {
    const userName = getUserName(userId);
    const actionText = action === 'make_admin' ? 'make this user an Administrator' : 'remove admin privileges from this user';
    
    if (confirm(`Are you sure you want to ${actionText} for ${userName}?`)) {
        executeRoleChange(userId, action);
    }
}

function executeRoleChange(userId, action) {
    const button = document.querySelector(`[data-user-id="${userId}"]`);
    if (button) {
        button.style.opacity = '0.5';
        button.disabled = true;
    }
    
    fetch(`/accounts/admin/ajax/users/${userId}/change-role/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: action
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            updateUserRow(userId, data.user);
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while updating user role.', 'error');
    })
    .finally(() => {
        if (button) {
            button.style.opacity = '1';
            button.disabled = false;
        }
    });
}

function toggleStatus(userId, action) {
    const userName = getUserName(userId);
    const user = getUserFromRow(userId);
    const actionText = user.isActive ? 'deactivate' : 'activate';
    
    if (confirm(`Are you sure you want to ${actionText} ${userName}?`)) {
        executeStatusToggle(userId, action);
    }
}

function executeStatusToggle(userId, action) {
    const button = document.querySelector(`[data-user-id="${userId}"]`);
    if (button) {
        button.style.opacity = '0.5';
        button.disabled = true;
    }
    
    fetch(`/accounts/admin/ajax/users/${userId}/toggle-status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: action
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            updateUserRow(userId, data.user);
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while updating user status.', 'error');
    })
    .finally(() => {
        if (button) {
            button.style.opacity = '1';
            button.disabled = false;
        }
    });
}

// Room Management Functions
function initializeRoomManagement() {
    // Add event listeners for room action buttons
    document.querySelectorAll('.btn-delete-room').forEach(button => {
        button.addEventListener('click', function() {
            const roomId = this.dataset.roomId;
            deleteRoom(roomId);
        });
    });
    
    document.querySelectorAll('.btn-toggle-room').forEach(button => {
        button.addEventListener('click', function() {
            const roomId = this.dataset.roomId;
            toggleRoomAvailability(roomId);
        });
    });
}

function deleteRoom(roomId) {
    const roomName = getRoomName(roomId);
    
    if (confirm(`Are you sure you want to delete "${roomName}"? This action cannot be undone.`)) {
        executeRoomDelete(roomId);
    }
}

function executeRoomDelete(roomId) {
    fetch(`/accounts/admin/ajax/rooms/${roomId}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            removeRoomRow(roomId);
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while deleting the room.', 'error');
    });
}

function toggleRoomAvailability(roomId) {
    const roomName = getRoomName(roomId);
    
    if (confirm(`Are you sure you want to toggle availability for "${roomName}"?`)) {
        executeRoomToggle(roomId);
    }
}

function executeRoomToggle(roomId) {
    fetch(`/accounts/admin/ajax/rooms/${roomId}/toggle-availability/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            updateRoomRow(roomId, data.room);
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while toggling room availability.', 'error');
    });
}

// Search and Filter Functions
function initializeSearch() {
    const searchInput = document.getElementById('userSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterUsers();
        });
    }
}

function initializeFilters() {
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    
    if (roleFilter) {
        roleFilter.addEventListener('change', filterUsers);
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', filterUsers);
    }
}

function filterUsers() {
    const searchTerm = document.getElementById('userSearch')?.value.toLowerCase() || '';
    const roleFilter = document.getElementById('roleFilter')?.value || '';
    const statusFilter = document.getElementById('statusFilter')?.value || '';
    
    const table = document.getElementById('usersTable');
    if (!table) return;
    
    const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const name = row.cells[0].textContent.toLowerCase();
        const email = row.cells[1].textContent.toLowerCase();
        const role = row.getAttribute('data-role');
        const status = row.getAttribute('data-status');
        
        let showRow = true;
        
        // Search filter
        if (searchTerm && !name.includes(searchTerm) && !email.includes(searchTerm)) {
            showRow = false;
        }
        
        // Role filter
        if (roleFilter && role !== roleFilter) {
            showRow = false;
        }
        
        // Status filter
        if (statusFilter && status !== statusFilter) {
            showRow = false;
        }
        
        row.style.display = showRow ? '' : 'none';
    }
}

// Utility Functions
function getCsrfToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}

function getUserName(userId) {
    const row = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (row) {
        return row.cells[0].textContent.trim();
    }
    
    // Alternative: look for user name in the row
    const allRows = document.querySelectorAll('#usersTable tbody tr');
    for (let row of allRows) {
        const buttons = row.querySelectorAll(`[data-user-id="${userId}"]`);
        if (buttons.length > 0) {
            return row.cells[0].textContent.trim();
        }
    }
    
    return 'Unknown User';
}

function getUserFromRow(userId) {
    const row = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (row) {
        return {
            name: row.cells[0].textContent.trim(),
            email: row.cells[1].textContent.trim(),
            role: row.getAttribute('data-role'),
            isActive: row.getAttribute('data-status') === 'active'
        };
    }
    return null;
}

function getRoomName(roomId) {
    const row = document.querySelector(`tr[data-room-id="${roomId}"]`);
    if (row) {
        return row.cells[1].textContent.trim(); // Assuming room name is in the second column
    }
    return 'Unknown Room';
}

function updateUserRow(userId, userData) {
    const row = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (!row) return;
    
    // Update role badge
    const roleCell = row.cells[2];
    roleCell.innerHTML = `<span class="badge ${userData.role === 'Admin' ? 'bg-danger' : 'bg-primary'}">${userData.role}</span>`;
    
    // Update status badge
    const statusCell = row.cells[3];
    statusCell.innerHTML = `<span class="badge ${userData.is_active ? 'bg-success' : 'bg-danger'}">${userData.is_active ? 'Active' : 'Inactive'}</span>`;
    
    // Update action buttons
    const actionCell = row.cells[7];
    updateActionButtons(actionCell, userData);
    
    // Update row data attributes
    row.setAttribute('data-role', userData.role);
    row.setAttribute('data-status', userData.is_active ? 'active' : 'inactive');
}

function updateActionButtons(cell, userData) {
    const isAdmin = userData.role === 'Admin';
    const isActive = userData.is_active;
    
    cell.innerHTML = `
        <div class="btn-group" role="group">
            <button class="btn btn-sm btn-outline-${isAdmin ? 'warning' : 'success'}" 
                    data-user-id="${userData.id}"
                    onclick="${isAdmin ? 'changeRole' : 'changeRole'}(${userData.id}, '${isAdmin ? 'make_user' : 'make_admin'}')">
                <i class="fas fa-user${isAdmin ? '' : '-shield'}"></i> 
                ${isAdmin ? 'Make User' : 'Make Admin'}
            </button>
            <button class="btn btn-sm btn-outline-${isActive ? 'danger' : 'success'}" 
                    data-user-id="${userData.id}"
                    onclick="toggleStatus(${userData.id}, 'toggle_active')">
                <i class="fas fa-user-${isActive ? 'slash' : 'check'}"></i> 
                ${isActive ? 'Deactivate' : 'Activate'}
            </button>
        </div>
    `;
}

function updateRoomRow(roomId, roomData) {
    const row = document.querySelector(`tr[data-room-id="${roomId}"]`);
    if (!row) return;
    
    // Update availability status (assuming it's in the 5th column)
    const statusCell = row.cells[4];
    statusCell.innerHTML = `<span class="badge ${roomData.is_available ? 'bg-success' : 'bg-danger'}">${roomData.is_available ? 'Available' : 'Unavailable'}</span>`;
    
    // Update toggle button
    const actionCell = row.cells[5];
    const toggleButton = actionCell.querySelector('.btn-toggle-room');
    if (toggleButton) {
        toggleButton.innerHTML = `<i class="fas fa-eye${roomData.is_available ? '-slash' : ''}"></i>`;
        toggleButton.title = roomData.is_available ? 'Make Unavailable' : 'Make Available';
    }
}

function removeRoomRow(roomId) {
    const row = document.querySelector(`tr[data-room-id="${roomId}"]`);
    if (row) {
        row.remove();
    }
}

function setupEventListeners() {
    // Handle form submissions
    document.addEventListener('submit', function(e) {
        // Add loading state to submit buttons
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        }
    });
    
    // Handle CSRF token refresh
    document.addEventListener('DOMContentLoaded', function() {
        // Refresh CSRF token if needed
        refreshCsrfToken();
    });
}

function refreshCsrfToken() {
    // This function can be used to refresh CSRF token if needed
    // For now, we'll just ensure we have a valid token
    const token = getCsrfToken();
    if (!token) {
        console.warn('No CSRF token found. Some admin functions may not work.');
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Try to use Bootstrap alerts if available
    if (typeof bootstrap !== 'undefined') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at the top of the page
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    } else {
        // Fallback to simple alert
        alert(message);
    }
}

// Global functions for onclick handlers
window.changeRole = changeRole;
window.toggleStatus = toggleStatus;
window.deleteRoom = deleteRoom;
window.toggleRoomAvailability = toggleRoomAvailability;
