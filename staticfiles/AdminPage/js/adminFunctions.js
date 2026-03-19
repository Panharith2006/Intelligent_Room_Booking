// Admin Functions JavaScript
// Comprehensive admin functionality for CRUD operations

// Global variables
let currentUserId = null;
let currentAction = null;

// Initialize admin functions when document loads
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminFunctions();
    setupEventListeners();
    initializeTooltips();
});

// Initialize all admin functions
function initializeAdminFunctions() {
    // Initialize search functionality
    initializeSearch();
    
    // Initialize filters
    initializeFilters();
    
    // Initialize bulk actions - DISABLED for user management
    initializeBulkActions(); // Now has path check to disable on user management pages
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize confirmation modals
    initializeConfirmationModals();
}

// Setup event listeners for all admin actions
function setupEventListeners() {
    // User management actions
    document.addEventListener('click', function(e) {
        if (e.target.closest('.btn-make-admin')) {
            handleRoleChange(e.target.closest('.btn-make-admin'), 'make_admin');
        }
        
        if (e.target.closest('.btn-make-user')) {
            handleRoleChange(e.target.closest('.btn-make-user'), 'make_user');
        }
        
        if (e.target.closest('.btn-toggle-status')) {
            handleStatusToggle(e.target.closest('.btn-toggle-status'));
        }
        
        if (e.target.closest('.btn-delete')) {
            handleDeleteAction(e.target.closest('.btn-delete'));
        }
        
        if (e.target.closest('.btn-edit')) {
            handleEditAction(e.target.closest('.btn-edit'));
        }
    });
    
    // Form submission handling
    document.addEventListener('submit', function(e) {
        if (e.target.classList.contains('admin-form')) {
            handleFormSubmission(e);
        }
    });
}

// User Role Management Functions
function changeRole(userId, action) {
    currentUserId = userId;
    currentAction = action;
    
    const userName = getUserName(userId);
    const actionText = action === 'make_admin' ? 'make this user an Administrator' : 'remove admin privileges from this user';
    
    showConfirmationModal({
        title: 'Change User Role',
        message: `Are you sure you want to ${actionText}?`,
        user: userName,
        type: 'warning',
        confirmText: 'Yes, Change Role',
        cancelText: 'Cancel',
        onConfirm: () => executeRoleChange(userId, action)
    });
}

function executeRoleChange(userId, action) {
    const button = document.querySelector(`[onclick*="${userId}"][onclick*="${action}"]`);
    if (button) {
        button.classList.add('user-action-loading');
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
            showToast(data.message, 'success');
            updateUserRow(userId, data.user);
        } else {
            showToast('Error updating user role: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while updating user role.', 'error');
    })
    .finally(() => {
        if (button) {
            button.classList.remove('user-action-loading');
            button.disabled = false;
        }
    });
}

function toggleStatus(userId, action) {
    currentUserId = userId;
    currentAction = action;
    
    const userName = getUserName(userId);
    const user = getUserData(userId);
    const actionText = user.is_active ? 'deactivate' : 'activate';
    
    showConfirmationModal({
        title: 'Toggle User Status',
        message: `Are you sure you want to ${actionText} this user?`,
        user: userName,
        type: user.is_active ? 'danger' : 'success',
        confirmText: `Yes, ${actionText.charAt(0).toUpperCase() + actionText.slice(1)}`,
        cancelText: 'Cancel',
        onConfirm: () => executeStatusToggle(userId, action)
    });
}

function executeStatusToggle(userId, action) {
    const button = document.querySelector(`[onclick*="${userId}"][onclick*="${action}"]`);
    if (button) {
        button.classList.add('user-action-loading');
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
            showToast(data.message, 'success');
            updateUserRow(userId, data.user);
        } else {
            showToast('Error updating user status: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while updating user status.', 'error');
    })
    .finally(() => {
        if (button) {
            button.classList.remove('user-action-loading');
            button.disabled = false;
        }
    });
}

// Room Management Functions
function handleRoomAction(action, roomId = null) {
    switch(action) {
        case 'delete':
            handleRoomDelete(roomId);
            break;
        case 'toggle_availability':
            handleRoomToggle(roomId);
            break;
        case 'edit':
            handleRoomEdit(roomId);
            break;
        default:
            console.warn('Unknown room action:', action);
    }
}

function handleRoomDelete(roomId) {
    const roomName = getRoomName(roomId);
    
    showConfirmationModal({
        title: 'Delete Room',
        message: 'Are you sure you want to delete this room? This action cannot be undone.',
        room: roomName,
        type: 'danger',
        confirmText: 'Yes, Delete Room',
        cancelText: 'Cancel',
        onConfirm: () => executeRoomDelete(roomId)
    });
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
            showToast(data.message, 'success');
            removeRoomRow(roomId);
        } else {
            showToast('Error deleting room: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while deleting the room.', 'error');
    });
}

// Search and Filter Functions
function initializeSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    }
}

function performSearch(query) {
    const tableRows = document.querySelectorAll('tbody tr');
    
    tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matches = text.includes(query.toLowerCase());
        row.style.display = matches ? '' : 'none';
    });
}

function initializeFilters() {
    const filterSelects = document.querySelectorAll('.filter-select');
    
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            applyFilters();
        });
    });
}

function applyFilters() {
    const roleFilter = document.getElementById('roleFilter');
    const statusFilter = document.getElementById('statusFilter');
    const tableRows = document.querySelectorAll('tbody tr');
    
    tableRows.forEach(row => {
        let showRow = true;
        
        if (roleFilter && roleFilter.value) {
            const userRole = row.dataset.role;
            if (userRole !== roleFilter.value) {
                showRow = false;
            }
        }
        
        if (statusFilter && statusFilter.value) {
            const userStatus = row.dataset.status;
            if (userStatus !== statusFilter.value) {
                showRow = false;
            }
        }
        
        row.style.display = showRow ? '' : 'none';
    });
}

// Bulk Actions - DISABLED for user management pages
function initializeBulkActions() {
    // Check if this is user management page and disable bulk actions
    const currentPath = window.location.pathname;
    if (currentPath.includes('manage-users') || currentPath.includes('user-management')) {
        console.log('Bulk actions disabled for user management page');
        return; // Exit early for user management pages
    }
    
    const selectAllCheckbox = document.getElementById('selectAll');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const bulkActionSelect = document.getElementById('bulkAction');
    const bulkActionButton = document.getElementById('bulkActionButton');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            itemCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionButton();
        });
    }
    
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateBulkActionButton();
        });
    });
    
    if (bulkActionButton) {
        bulkActionButton.addEventListener('click', function() {
            executeBulkAction();
        });
    }
}

function updateBulkActionButton() {
    const selectedItems = document.querySelectorAll('.item-checkbox:checked');
    const bulkActionButton = document.getElementById('bulkActionButton');
    
    if (bulkActionButton) {
        bulkActionButton.disabled = selectedItems.length === 0;
    }
}

function executeBulkAction() {
    const selectedItems = document.querySelectorAll('.item-checkbox:checked');
    const bulkActionSelect = document.getElementById('bulkAction');
    
    if (selectedItems.length === 0) {
        showToast('Please select at least one item.', 'warning');
        return;
    }
    
    if (!bulkActionSelect || !bulkActionSelect.value) {
        showToast('Please select an action.', 'warning');
        return;
    }
    
    const action = bulkActionSelect.value;
    const itemIds = Array.from(selectedItems).map(checkbox => checkbox.value);
    
    showConfirmationModal({
        title: 'Bulk Action',
        message: `Are you sure you want to perform "${action}" on ${itemIds.length} selected item(s)?`,
        type: 'warning',
        confirmText: 'Yes, Continue',
        cancelText: 'Cancel',
        onConfirm: () => executeBulkRequest(action, itemIds)
    });
}

function executeBulkRequest(action, itemIds) {
    fetch('/accounts/admin/ajax/bulk-action/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            action: action,
            item_ids: itemIds
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            location.reload();
        } else {
            showToast('Error performing bulk action: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('An error occurred while performing the bulk action.', 'error');
    });
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.admin-form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                clearFieldError(this);
            });
        });
    });
}

function validateField(field) {
    const formGroup = field.closest('.form-group');
    const value = field.value.trim();
    let isValid = true;
    let errorMessage = '';
    
    // Required field validation
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required.';
    }
    
    // Email validation
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address.';
        }
    }
    
    // Number validation
    if (field.type === 'number' && value) {
        const min = field.getAttribute('min');
        const max = field.getAttribute('max');
        
        if (min && parseFloat(value) < parseFloat(min)) {
            isValid = false;
            errorMessage = `Value must be at least ${min}.`;
        }
        
        if (max && parseFloat(value) > parseFloat(max)) {
            isValid = false;
            errorMessage = `Value must not exceed ${max}.`;
        }
    }
    
    // Update field appearance
    if (isValid) {
        formGroup.classList.remove('error');
        formGroup.classList.add('success');
        removeFieldError(field);
    } else {
        formGroup.classList.remove('success');
        formGroup.classList.add('error');
        showFieldError(field, errorMessage);
    }
    
    return isValid;
}

function showFieldError(field, message) {
    removeFieldError(field);
    
    const errorElement = document.createElement('small');
    errorElement.className = 'error-message';
    errorElement.textContent = message;
    
    field.parentNode.appendChild(errorElement);
}

function removeFieldError(field) {
    const existingError = field.parentNode.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
}

function clearFieldError(field) {
    const formGroup = field.closest('.form-group');
    formGroup.classList.remove('error');
    removeFieldError(field);
}

// Utility Functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function getUserName(userId) {
    const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (userRow) {
        return userRow.querySelector('td:first-child').textContent.trim();
    }
    return 'Unknown User';
}

function getUserData(userId) {
    const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (userRow) {
        return {
            name: userRow.querySelector('td:first-child').textContent.trim(),
            role: userRow.dataset.role,
            is_active: userRow.dataset.status === 'active'
        };
    }
    return null;
}

function getRoomName(roomId) {
    const roomRow = document.querySelector(`tr[data-room-id="${roomId}"]`);
    if (roomRow) {
        return roomRow.querySelector('td:nth-child(2)').textContent.trim();
    }
    return 'Unknown Room';
}

function updateUserRow(userId, userData) {
    const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (userRow) {
        // Update role badge
        const roleBadge = userRow.querySelector('.role-badge');
        if (roleBadge) {
            roleBadge.textContent = userData.role;
            roleBadge.className = `role-badge ${userData.role.toLowerCase()}`;
        }
        
        // Update status badge
        const statusBadge = userRow.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = userData.is_active ? 'Active' : 'Inactive';
            statusBadge.className = `status-badge ${userData.is_active ? 'active' : 'inactive'}`;
        }
        
        // Update action buttons
        const actionButtons = userRow.querySelector('.role-actions');
        if (actionButtons) {
            updateActionButtons(actionButtons, userData);
        }
        
        // Update row data attributes
        userRow.dataset.role = userData.role;
        userRow.dataset.status = userData.is_active ? 'active' : 'inactive';
    }
}

function updateActionButtons(container, userData) {
    const isAdmin = userData.role === 'Admin';
    const isActive = userData.is_active;
    
    container.innerHTML = `
        <button class="btn-${isAdmin ? 'make-user' : 'make-admin'}" 
                onclick="${isAdmin ? 'changeRole' : 'changeRole'}(${userData.id}, '${isAdmin ? 'make_user' : 'make_admin'}')">
            <i class="fas fa-user${isAdmin ? '' : '-shield'}"></i> 
            ${isAdmin ? 'Make User' : 'Make Admin'}
        </button>
        <button class="btn-toggle-status ${isActive ? 'deactivate' : 'activate'}" 
                onclick="toggleStatus(${userData.id}, 'toggle_active')">
            <i class="fas fa-user-${isActive ? 'slash' : 'check'}"></i> 
            ${isActive ? 'Deactivate' : 'Activate'}
        </button>
    `;
}

function removeUserRow(userId) {
    const userRow = document.querySelector(`tr[data-user-id="${userId}"]`);
    if (userRow) {
        userRow.remove();
    }
}

function removeRoomRow(roomId) {
    const roomRow = document.querySelector(`tr[data-room-id="${roomId}"]`);
    if (roomRow) {
        roomRow.remove();
    }
}

// Modal Functions
function showConfirmationModal(config) {
    const modal = document.getElementById('confirmationModal') || createConfirmationModal();
    
    // Update modal content
    modal.querySelector('.modal-title').textContent = config.title;
    modal.querySelector('.modal-body .message').textContent = config.message;
    
    if (config.user) {
        modal.querySelector('.modal-body .user-name').textContent = config.user;
        modal.querySelector('.modal-body .user-info').style.display = 'block';
    } else {
        modal.querySelector('.modal-body .user-info').style.display = 'none';
    }
    
    // Update modal styling
    const modalHeader = modal.querySelector('.modal-header');
    modalHeader.className = `modal-header ${config.type}`;
    
    // Update buttons
    const confirmButton = modal.querySelector('.btn-confirm');
    const cancelButton = modal.querySelector('.btn-cancel');
    
    confirmButton.textContent = config.confirmText;
    cancelButton.textContent = config.cancelText;
    
    // Set up event listeners
    confirmButton.onclick = () => {
        config.onConfirm();
        hideModal(modal);
    };
    
    cancelButton.onclick = () => {
        hideModal(modal);
    };
    
    // Show modal
    showModal(modal);
}

function createConfirmationModal() {
    const modal = document.createElement('div');
    modal.id = 'confirmationModal';
    modal.className = 'modal fade user-action-modal';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Confirm Action</h5>
                </div>
                <div class="modal-body">
                    <div class="icon">
                        <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <p class="message">Are you sure you want to perform this action?</p>
                    <div class="user-info">
                        <strong>User: <span class="user-name"></span></strong>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary btn-cancel">Cancel</button>
                    <button type="button" class="btn btn-primary btn-confirm">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    return modal;
}

function showModal(modal) {
    modal.style.display = 'block';
    modal.classList.add('show');
    document.body.classList.add('modal-open');
}

function hideModal(modal) {
    modal.style.display = 'none';
    modal.classList.remove('show');
    document.body.classList.remove('modal-open');
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas fa-${getToastIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" onclick="removeToast(this.parentElement)">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        removeToast(toast);
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function getToastIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'error': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

function removeToast(toast) {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => {
        if (toast.parentElement) {
            toast.parentElement.removeChild(toast);
        }
    }, 300);
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = event.target.dataset.tooltip;
    
    document.body.appendChild(tooltip);
    
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
    
    event.target.tooltipElement = tooltip;
}

function hideTooltip(event) {
    if (event.target.tooltipElement) {
        document.body.removeChild(event.target.tooltipElement);
        event.target.tooltipElement = null;
    }
}

// Export functions for global use
window.changeRole = changeRole;
window.toggleStatus = toggleStatus;
window.handleRoomAction = handleRoomAction;
window.showToast = showToast;
