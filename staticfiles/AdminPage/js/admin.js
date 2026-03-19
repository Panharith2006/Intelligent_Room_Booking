// Admin JavaScript Functions
// Basic admin functionality

document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin JS loaded successfully');
    
    // Initialize any admin-specific functionality here
    initializeAdminFeatures();
});

function initializeAdminFeatures() {
    // Add any admin-specific JavaScript functionality here
    console.log('Admin features initialized');
    
    // Example: Add confirmation to dangerous actions
    const dangerousButtons = document.querySelectorAll('.btn-danger');
    dangerousButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to perform this action?')) {
                e.preventDefault();
            }
        });
    });
}
