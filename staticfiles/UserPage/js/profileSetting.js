document.addEventListener('DOMContentLoaded', function() {
    // Initialize profile settings page
    initializeProfileSettings();
    
    // Set up form validation
    setupFormValidation();
    
    // Set up password strength checker
    setupPasswordStrengthChecker();
    
    // Set up image upload preview
    setupImageUploadPreview();
    
    // Set up auto-save functionality
    setupAutoSave();
});

function initializeProfileSettings() {
    // Load saved profile data if available
    loadProfileData();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize tooltips
    initializeTooltips();
}

function setupEventListeners() {
    // Form submission handlers
    const passwordForm = document.querySelector('.password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', handlePasswordSubmit);
    }
    
    // Input change handlers
    document.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('change', handleInputChange);
        input.addEventListener('blur', validateField);
    });
    
    // Department change handler
    const positionSelect = document.getElementById('position');
    if (positionSelect) {
        positionSelect.addEventListener('change', handlePositionChange);

function handleProfileSubmit(e) {
    e.preventDefault();
    
    // Show loading state
    showLoading();
    
    // Validate form
    if (!validateProfileForm()) {
        hideLoading();
        return;
    }
    
    // Submit form
    const formData = new FormData(e.target);
    
    fetch(e.target.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showMessage('Profile updated successfully!', 'success');
            // Update UI with new data
            updateProfileDisplay(data.user);
        } else {
            showMessage(data.error || 'An error occurred', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showMessage('Network error occurred', 'error');
        console.error('Error:', error);
    });
}

function handlePasswordSubmit(e) {
    e.preventDefault();
    
    const form = e.target;
    const newPassword1 = form.querySelector('#new_password1').value;
    const newPassword2 = form.querySelector('#new_password2').value;
    
    // Validate passwords match
    if (newPassword1 !== newPassword2) {
        showMessage('Passwords do not match', 'error');
        return;
    }
    
    // Validate password strength
    if (!validatePasswordStrength(newPassword1)) {
        showMessage('Password does not meet requirements', 'error');
        return;
    }
    
    // Show loading state
    showLoading();
    
    // Submit form
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showMessage('Password changed successfully!', 'success');
            form.reset();
        } else {
            showMessage(data.error || 'Failed to change password', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showMessage('Network error occurred', 'error');
        console.error('Error:', error);
    });
}

function validateProfileForm() {
    const requiredFields = ['first_name', 'last_name', 'email'];
    let isValid = true;
    
    requiredFields.forEach(fieldName => {
        const field = document.getElementById(fieldName);
        if (field && !field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        }
    });
    
    // Validate email format
    const emailField = document.getElementById('email');
    if (emailField && emailField.value) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(emailField.value)) {
            showFieldError(emailField, 'Please enter a valid email address');
            isValid = false;
        }
    }
    
    return isValid;
}

function validatePasswordStrength(password) {
    const requirements = {
        length: password.length >= 8,
        upperLower: /[a-z]/.test(password) && /[A-Z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
    };
    
    return Object.values(requirements).every(req => req);
}

function setupPasswordStrengthChecker() {
    const passwordField = document.getElementById('new_password1');
    if (!passwordField) return;
    
    passwordField.addEventListener('input', function() {
        const password = this.value;
        const requirements = document.querySelectorAll('.password-requirements li');
        
        if (requirements.length >= 4) {
            // Check length
            requirements[0].style.color = password.length >= 8 ? '#27ae60' : '#e74c3c';
            
            // Check uppercase and lowercase
            requirements[1].style.color = /[a-z]/.test(password) && /[A-Z]/.test(password) ? '#27ae60' : '#e74c3c';
            
            // Check number
            requirements[2].style.color = /\d/.test(password) ? '#27ae60' : '#e74c3c';
            
            // Check special character
            requirements[3].style.color = /[!@#$%^&*(),.?":{}|<>]/.test(password) ? '#27ae60' : '#e74c3c';
        }
    });
}

function setupImageUploadPreview() {
    const imageInput = document.getElementById('profilePicture');
    const preview = document.getElementById('profilePreview');
    
    if (imageInput && preview) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Validate file type
                const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
                if (!allowedTypes.includes(file.type)) {
                    showMessage('Please select a valid image file (JPEG, PNG, or GIF)', 'error');
                    return;
                }
                
                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    showMessage('Image size must be less than 5MB', 'error');
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    preview.style.animation = 'fadeIn 0.3s ease';
                }
                reader.readAsDataURL(file);
            }
        });
    }
}

function setupAutoSave() {
    let autoSaveTimeout;
    
    document.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('input', function() {
            clearTimeout(autoSaveTimeout);
            autoSaveTimeout = setTimeout(() => {
                saveToLocalStorage();
            }, 1000);
        });
    });
}

function saveToLocalStorage() {
    const formData = {};
    document.querySelectorAll('input, select, textarea').forEach(input => {
        if (input.type !== 'password' && input.type !== 'file') {
            formData[input.name] = input.value;
        }
    });
    
    localStorage.setItem('profileFormData', JSON.stringify(formData));
}

        updateDepartmentOptions(departmentSelect, options);
    }
}

function updateDepartmentOptions(select, options) {
    const currentValue = select.value;
    select.innerHTML = '<option value="">Select Department</option>';
    
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        if (option === currentValue) {
            optionElement.selected = true;
        }
        select.appendChild(optionElement);
    });
}

function validateField(e) {
    const field = e.target;
    const value = field.value.trim();
    
    // Clear previous errors
    clearFieldError(field);
    
    // Validate required fields
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, 'This field is required');
        return false;
    }
    
    // Validate specific field types
    if (field.type === 'email' && value) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(value)) {
            showFieldError(field, 'Please enter a valid email address');
            return false;
        }
    }
    
    if (field.type === 'tel' && value) {
        const phonePattern = /^[\d\s\+\-\(\)]{8,}$/;
        if (!phonePattern.test(value)) {
            showFieldError(field, 'Please enter a valid phone number');
            return false;
        }
    }
    
    return true;
}

function showFieldError(field, message) {
    field.classList.add('error');
    
    const errorElement = document.createElement('div');
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    
    field.parentNode.appendChild(errorElement);
}

function clearFieldError(field) {
    field.classList.remove('error');
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

function showMessage(message, type = 'info') {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message ${type}`;
    messageContainer.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="close-message" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    const main = document.querySelector('main');
    main.insertBefore(messageContainer, main.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (messageContainer.parentNode) {
            messageContainer.remove();
        }
    }, 5000);
}

function showLoading() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => form.classList.add('loading'));
}

function hideLoading() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => form.classList.remove('loading'));
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

function updateProfileDisplay(userData) {
    // Update profile display with new data
    const nameElements = document.querySelectorAll('[data-user-name]');
    nameElements.forEach(el => {
        el.textContent = `${userData.first_name} ${userData.last_name}`;
    });
    
    const emailElements = document.querySelectorAll('[data-user-email]');
    emailElements.forEach(el => {
        el.textContent = userData.email;
    });
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
    document.body.appendChild(tooltip);
    
    const rect = e.target.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 + 'px';
    tooltip.style.top = rect.top - 40 + 'px';
    
    setTimeout(() => tooltip.classList.add('show'), 10);
}

function hideTooltip() {
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => tooltip.remove());
}

// Handle input changes
function handleInputChange(e) {
    const field = e.target;
    
    // Clear errors on change
    clearFieldError(field);
    
    // Trigger auto-save
    saveToLocalStorage();
}

// Export functions for global use
window.cancelForm = function() {
    if(confirm('Are you sure you want to cancel? All unsaved changes will be lost.')) {
        window.location.reload();
    }
};