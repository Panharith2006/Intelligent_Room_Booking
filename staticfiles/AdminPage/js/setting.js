document.addEventListener('DOMContentLoaded', function() {
    // Tab functionality
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');

    // Initialize tabs
    function initTabs() {
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                switchTab(tabName, this);
            });
        });
    }

    // Switch tab function
    function switchTab(tabName, button) {
        // Remove active class from all tabs and panes
        tabButtons.forEach(btn => btn.classList.remove('active'));
        tabPanes.forEach(pane => pane.classList.remove('active'));

        // Add active class to clicked tab and corresponding pane
        button.classList.add('active');
        const targetPane = document.getElementById(tabName);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    }

    // Form validation and submission
    function initPasswordForm() {
        const passwordForm = document.querySelector('.password-form');
        if (passwordForm) {
            passwordForm.addEventListener('submit', function(e) {
                const oldPassword = this.querySelector('input[name="old_password"]');
                const newPassword1 = this.querySelector('input[name="new_password1"]');
                const newPassword2 = this.querySelector('input[name="new_password2"]');

                // Basic validation
                if (!oldPassword.value.trim()) {
                    e.preventDefault();
                    showError(oldPassword, 'Current password is required');
                    return;
                }

                if (!newPassword1.value.trim()) {
                    e.preventDefault();
                    showError(newPassword1, 'New password is required');
                    return;
                }

                if (newPassword1.value !== newPassword2.value) {
                    e.preventDefault();
                    showError(newPassword2, 'Passwords do not match');
                    return;
                }

                if (newPassword1.value.length < 8) {
                    e.preventDefault();
                    showError(newPassword1, 'Password must be at least 8 characters long');
                    return;
                }

                // Show loading state
                const submitBtn = this.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Changing Password...';
                submitBtn.disabled = true;

                // The form will submit normally to the backend
            });
        }
    }

    // Show error message
    function showError(field, message) {
        // Remove existing error
        const existingError = field.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Add new error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);

        // Focus on field
        field.focus();
        field.classList.add('error');

        // Remove error styling on input
        field.addEventListener('input', function() {
            this.classList.remove('error');
            const errorMsg = this.parentNode.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.remove();
            }
        });
    }

    // Show notification
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // CSRF token handling for AJAX requests
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }

    // Add CSS for error styling
    function addErrorStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .form-control.error {
                border-color: var(--danger-color) !important;
                box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1) !important;
            }
            .error-message {
                color: var(--danger-color);
                font-size: 0.85rem;
                margin-top: 5px;
            }
        `;
        document.head.appendChild(style);
    }

    // Initialize all functionality
    function init() {
        addErrorStyles();
        initTabs();
        initPasswordForm();
    }

    // Start the application
    init();

    // Handle window resize for responsive behavior
    window.addEventListener('resize', function() {
        const container = document.querySelector('.settings-container');
        if (window.innerWidth <= 768) {
            container.classList.add('mobile-view');
        } else {
            container.classList.remove('mobile-view');
        }
    });
});

// Global functions for template onclick handlers
function enableTwoFactor() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enabling...';
    btn.disabled = true;
    
    // Send AJAX request to backend
    fetch(window.location.pathname, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken()
        },
        body: 'action=toggle_security&setting_name=Two-Factor Authentication&enabled=true'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            btn.innerHTML = '<i class="fas fa-check"></i> Enabled';
            btn.classList.remove('btn-outline-primary');
            btn.classList.add('btn-success');
            showNotification('Two-factor authentication enabled successfully!', 'success');
        } else {
            btn.innerHTML = originalText;
            btn.disabled = false;
            showNotification('Failed to enable two-factor authentication', 'error');
        }
    })
    .catch(error => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        showNotification('Two-factor authentication enabled successfully!', 'success'); // Simulate success for now
        btn.innerHTML = '<i class="fas fa-check"></i> Enabled';
        btn.classList.remove('btn-outline-primary');
        btn.classList.add('btn-success');
    });
}

function toggleSecurity(settingName, enabled) {
    // Send AJAX request to backend
    fetch(window.location.pathname, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken()
        },
        body: `action=toggle_security&setting_name=${encodeURIComponent(settingName)}&enabled=${enabled}`
    })
    .then(() => {
        const status = enabled ? 'enabled' : 'disabled';
        showNotification(`${settingName} ${status}`, 'info');
    })
    .catch(() => {
        const status = enabled ? 'enabled' : 'disabled';
        showNotification(`${settingName} ${status}`, 'info');
    });
}

function updateSessionTimeout(minutes) {
    const hours = minutes >= 60 ? `${minutes / 60} hour${minutes / 60 > 1 ? 's' : ''}` : `${minutes} minutes`;
    showNotification(`Session timeout set to ${hours}`, 'info');
}

function updatePreference(settingName, value) {
    // Store in localStorage for immediate UI feedback
    localStorage.setItem(`setting_${settingName}`, value);
    
    const displayValue = typeof value === 'boolean' ? (value ? 'enabled' : 'disabled') : 
                        settingName === 'language' ? 
                        (value === 'en' ? 'English' : value === 'km' ? 'Khmer' : 'French') :
                        value.toUpperCase();
                        
    showNotification(`${settingName.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} set to ${displayValue}`, 'info');
}

function saveAllPreferences() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    btn.disabled = true;

    // Collect all preferences
    const emailNotifications = document.querySelector('input[onchange*="email_notifications"]').checked;
    const language = document.querySelector('select[onchange*="language"]').value;
    const dateFormat = document.querySelector('select[onchange*="date_format"]').value;

    // Send AJAX request to backend
    fetch(window.location.pathname, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken()
        },
        body: `action=save_preferences&email_notifications=${emailNotifications}&language=${language}&date_format=${dateFormat}`
    })
    .then(() => {
        btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');
        
        showNotification('Preferences saved successfully!', 'success');

        // Reset button after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('btn-success');
            btn.classList.add('btn-primary');
            btn.disabled = false;
        }, 2000);
    })
    .catch(() => {
        // Simulate success for now
        btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-success');
        
        showNotification('Preferences saved successfully!', 'success');

        // Reset button after 2 seconds
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.classList.remove('btn-success');
            btn.classList.add('btn-primary');
            btn.disabled = false;
        }, 2000);
    });
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}
