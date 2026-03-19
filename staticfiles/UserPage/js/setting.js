document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings page
    initializeSettingsPage();
    
    // Set up modal functionality
    setupModals();
    
    // Set up form validation
    setupFormValidation();
    
    // Initialize animations
    initializeAnimations();
});

function initializeSettingsPage() {
    // Load user preferences
    loadUserPreferences();
    
    // Set up card hover effects
    setupCardHoverEffects();
    
    // Initialize tooltips
    initializeTooltips();
}

function setupModals() {
    // Password modal
    const passwordModal = document.getElementById('passwordModal');
    const notificationModal = document.getElementById('notificationModal');
    
    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === passwordModal) {
            hidePasswordModal();
        }
        if (event.target === notificationModal) {
            hideNotificationModal();
        }
    });
    
    // Close modals with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            hidePasswordModal();
            hideNotificationModal();
        }
    });
}

function setupFormValidation() {
    // Password form validation
    const passwordForm = document.querySelector('#passwordModal .modal-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const currentPassword = document.getElementById('current_password').value;
            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            
            // Validate passwords
            if (!validatePasswordForm(currentPassword, newPassword, confirmPassword)) {
                return;
            }
            
            // Submit form
            submitPasswordForm(this);
        });
        
        // Real-time password validation
        const newPasswordInput = document.getElementById('new_password');
        if (newPasswordInput) {
            newPasswordInput.addEventListener('input', function() {
                validatePasswordStrength(this.value);
            });
        }
    }
    
    // Notification form validation
    const notificationForm = document.querySelector('#notificationModal .modal-form');
    if (notificationForm) {
        notificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitNotificationForm(this);
        });
    }
}

function validatePasswordForm(currentPassword, newPassword, confirmPassword) {
    // Clear previous errors
    clearFormErrors();
    
    let isValid = true;
    
    // Check if current password is provided
    if (!currentPassword) {
        showFieldError('current_password', 'Current password is required');
        isValid = false;
    }
    
    // Check if new password is provided
    if (!newPassword) {
        showFieldError('new_password', 'New password is required');
        isValid = false;
    } else if (!validatePasswordStrength(newPassword)) {
        showFieldError('new_password', 'Password does not meet requirements');
        isValid = false;
    }
    
    // Check if passwords match
    if (newPassword !== confirmPassword) {
        showFieldError('confirm_password', 'Passwords do not match');
        isValid = false;
    }
    
    return isValid;
}

function validatePasswordStrength(password) {
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    // Update UI indicators
    const requirementsList = document.querySelectorAll('.password-requirements li');
    if (requirementsList.length >= 4) {
        requirementsList[0].style.color = requirements.length ? '#27ae60' : '#e74c3c';
        requirementsList[1].style.color = (requirements.uppercase && requirements.lowercase) ? '#27ae60' : '#e74c3c';
        requirementsList[2].style.color = requirements.number ? '#27ae60' : '#e74c3c';
        requirementsList[3].style.color = requirements.special ? '#27ae60' : '#e74c3c';
    }
    
    return Object.values(requirements).every(req => req);
}

function submitPasswordForm(form) {
    // Show loading state
    const submitBtn = form.querySelector('.btn-confirm');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Changing...';
    submitBtn.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        showMessage('Password changed successfully!', 'success');
        hidePasswordModal();
        form.reset();
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }, 2000);
}

function submitNotificationForm(form) {
    // Show loading state
    const submitBtn = form.querySelector('.btn-confirm');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;
    
    // Simulate API call
    setTimeout(() => {
        showMessage('Notification settings updated!', 'success');
        hideNotificationModal();
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }, 1500);
}

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (field) {
        field.style.borderColor = '#e74c3c';
        
        // Remove existing error message
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error message
        const errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.textContent = message;
        errorElement.style.color = '#e74c3c';
        errorElement.style.fontSize = '0.8rem';
        errorElement.style.marginTop = '0.25rem';
        
        field.parentNode.appendChild(errorElement);
    }
}

function clearFormErrors() {
    // Clear field errors
    const errorElements = document.querySelectorAll('.field-error');
    errorElements.forEach(element => element.remove());
    
    // Reset field borders
    const formFields = document.querySelectorAll('#passwordModal input, #notificationModal input');
    formFields.forEach(field => {
        field.style.borderColor = '';
    });
}

function showMessage(message, type = 'info') {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message ${type}`;
    messageContainer.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="close-message" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    const mainContainer = document.querySelector('.main-container');
    mainContainer.insertBefore(messageContainer, mainContainer.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageContainer.parentNode) {
            messageContainer.style.opacity = '0';
            setTimeout(() => messageContainer.remove(), 300);
        }
    }, 5000);
}

function setupCardHoverEffects() {
    const cards = document.querySelectorAll('.action-card, .stat-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

function initializeAnimations() {
    // Staggered animation for cards
    const cards = document.querySelectorAll('.action-card, .stat-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 150);
    });
    
    // Fade in profile info
    const infoSections = document.querySelectorAll('.info-section');
    infoSections.forEach((section, index) => {
        section.style.opacity = '0';
        section.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            section.style.transition = 'all 0.6s ease';
            section.style.opacity = '1';
            section.style.transform = 'translateX(0)';
        }, index * 200);
    });
}

function loadUserPreferences() {
    // Load user preferences from localStorage
    const preferences = localStorage.getItem('userPreferences');
    if (preferences) {
        try {
            const data = JSON.parse(preferences);
            
            // Apply notification preferences
            const emailNotifications = document.getElementById('email_notifications');
            const smsNotifications = document.getElementById('sms_notifications');
            const bookingReminders = document.getElementById('booking_reminders');
            
            if (emailNotifications) emailNotifications.checked = data.email_notifications || false;
            if (smsNotifications) smsNotifications.checked = data.sms_notifications || false;
            if (bookingReminders) bookingReminders.checked = data.booking_reminders || false;
        } catch (e) {
            console.error('Error loading user preferences:', e);
        }
    }
}

function saveUserPreferences() {
    const preferences = {
        email_notifications: document.getElementById('email_notifications')?.checked || false,
        sms_notifications: document.getElementById('sms_notifications')?.checked || false,
        booking_reminders: document.getElementById('booking_reminders')?.checked || false
    };
    
    localStorage.setItem('userPreferences', JSON.stringify(preferences));
}

function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = e.target.getAttribute('data-tooltip');
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
        pointer-events: none;
        z-index: 1000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 10 + 'px';
    
    setTimeout(() => tooltip.style.opacity = '1', 10);
}

function hideTooltip() {
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => tooltip.remove());
}

// Export functions for global use
window.showPasswordModal = function() {
    document.getElementById('passwordModal').style.display = 'block';
};

window.hidePasswordModal = function() {
    document.getElementById('passwordModal').style.display = 'none';
};

window.showNotificationModal = function() {
    document.getElementById('notificationModal').style.display = 'block';
};

window.hideNotificationModal = function() {
    document.getElementById('notificationModal').style.display = 'none';
};

// Save preferences when notification checkboxes change
document.addEventListener('change', function(e) {
    if (e.target.type === 'checkbox' && e.target.name.includes('notification')) {
        saveUserPreferences();
    }
});