document.addEventListener('DOMContentLoaded', function() {
    // CSRF token for AJAX requests
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    }

    // Show notification
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
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

    // Enhanced user search functionality
    function initUserSearch() {
        const searchInput = document.getElementById('userSearch');
        const roleFilter = document.getElementById('roleFilter');
        const statusFilter = document.getElementById('statusFilter');
        const tableRows = document.querySelectorAll('#usersTable tbody tr');

        function filterUsers() {
            const searchTerm = searchInput.value.toLowerCase();
            const selectedRole = roleFilter.value;
            const selectedStatus = statusFilter.value;

            let visibleCount = 0;

            tableRows.forEach(row => {
                // Skip empty rows
                if (row.cells.length < 8) return;

                const userName = row.cells[0].textContent.toLowerCase();
                const userEmail = row.cells[1].textContent.toLowerCase();
                const userFaculty = row.cells[4].textContent.toLowerCase();
                const userDepartment = row.cells[5].textContent.toLowerCase();
                const userRole = row.getAttribute('data-role');
                const userStatus = row.getAttribute('data-status');

                const matchesSearch = userName.includes(searchTerm) || 
                                    userEmail.includes(searchTerm) ||
                                    userFaculty.includes(searchTerm) ||
                                    userDepartment.includes(searchTerm);
                const matchesRole = !selectedRole || userRole === selectedRole;
                const matchesStatus = !selectedStatus || userStatus === selectedStatus;

                if (matchesSearch && matchesRole && matchesStatus) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            // Update search results count
            updateSearchResults(visibleCount);
        }

        function updateSearchResults(count) {
            let resultDiv = document.getElementById('searchResults');
            if (!resultDiv) {
                resultDiv = document.createElement('div');
                resultDiv.id = 'searchResults';
                resultDiv.className = 'text-muted mb-2';
                const tableContainer = document.querySelector('.table-responsive');
                tableContainer.parentNode.insertBefore(resultDiv, tableContainer);
            }
            
            if (searchInput.value || roleFilter.value || statusFilter.value) {
                resultDiv.textContent = `Showing ${count} user(s) matching your filters`;
                resultDiv.style.display = 'block';
            } else {
                resultDiv.style.display = 'none';
            }
        }

        // Debounced search to improve performance
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(filterUsers, 300);
        });

        roleFilter.addEventListener('change', filterUsers);
        statusFilter.addEventListener('change', filterUsers);

        // Initialize
        filterUsers();
    }

    // AJAX user actions with better UX
    window.changeRoleAjax = function(userId, action, userName) {
        const button = event.target.closest('button');
        const originalHTML = button.innerHTML;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        button.disabled = true;

        // Prepare data
        const formData = new FormData();
        formData.append('action', action);
        formData.append('user_id', userId);
        formData.append('csrfmiddlewaretoken', getCSRFToken());

        // Send AJAX request
        fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.text();
            }
            throw new Error('Network response was not ok');
        })
        .then(data => {
            // Update UI immediately for better UX
            updateUserRoleUI(userId, action, userName);
            
            const actionText = action === 'make_admin' ? 'promoted to Administrator' : 'demoted to Regular User';
            showNotification(`${userName} has been ${actionText}`, 'success');
            
            // Reload page after a short delay to ensure data consistency
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        })
        .catch(error => {
            console.error('Error:', error);
            button.innerHTML = originalHTML;
            button.disabled = false;
            showNotification('An error occurred. Please try again.', 'error');
        });
    };

    window.toggleStatusAjax = function(userId, action, userName, currentStatus) {
        const button = event.target.closest('button');
        const originalHTML = button.innerHTML;
        
        // Show loading state
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        button.disabled = true;

        // Prepare data
        const formData = new FormData();
        formData.append('action', action);
        formData.append('user_id', userId);
        formData.append('csrfmiddlewaretoken', getCSRFToken());

        // Send AJAX request
        fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.text();
            }
            throw new Error('Network response was not ok');
        })
        .then(data => {
            // Update UI immediately for better UX
            updateUserStatusUI(userId, !currentStatus, userName);
            
            const statusText = currentStatus ? 'deactivated' : 'activated';
            showNotification(`${userName} has been ${statusText}`, 'success');
            
            // Reload page after a short delay to ensure data consistency
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        })
        .catch(error => {
            console.error('Error:', error);
            button.innerHTML = originalHTML;
            button.disabled = false;
            showNotification('An error occurred. Please try again.', 'error');
        });
    };

    // Update UI immediately for better user experience
    function updateUserRoleUI(userId, action, userName) {
        const row = document.querySelector(`tr[data-user-id="${userId}"]`);
        if (!row) return;

        const roleBadge = row.querySelector('.badge');
        const actionButton = row.querySelector('button[onclick*="changeRole"]');
        
        if (action === 'make_admin') {
            roleBadge.className = 'badge bg-danger';
            roleBadge.textContent = 'Admin';
            row.setAttribute('data-role', 'Admin');
            
            actionButton.innerHTML = '<i class="fas fa-user"></i> Demote to User';
            actionButton.setAttribute('onclick', `changeRoleAjax(${userId}, 'make_user', '${userName}')`);
            actionButton.className = 'btn btn-sm btn-outline-warning';
        } else {
            roleBadge.className = 'badge bg-primary';
            roleBadge.textContent = 'User';
            row.setAttribute('data-role', 'User');
            
            actionButton.innerHTML = '<i class="fas fa-user-shield"></i> Make Admin';
            actionButton.setAttribute('onclick', `changeRoleAjax(${userId}, 'make_admin', '${userName}')`);
            actionButton.className = 'btn btn-sm btn-outline-success';
        }
    }

    function updateUserStatusUI(userId, newStatus, userName) {
        const row = document.querySelector(`tr[data-user-id="${userId}"]`);
        if (!row) return;

        const statusBadge = row.querySelector('.badge:nth-of-type(2)') || row.querySelectorAll('.badge')[1];
        const statusButton = row.querySelector('button[onclick*="toggleStatus"]');
        
        if (newStatus) {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Active';
            row.setAttribute('data-status', 'active');
            
            statusButton.innerHTML = '<i class="fas fa-user-slash"></i> Deactivate';
            statusButton.setAttribute('onclick', `toggleStatusAjax(${userId}, 'toggle_active', '${userName}', true)`);
            statusButton.className = 'btn btn-sm btn-outline-danger';
        } else {
            statusBadge.className = 'badge bg-danger';
            statusBadge.textContent = 'Inactive';
            row.setAttribute('data-status', 'inactive');
            
            statusButton.innerHTML = '<i class="fas fa-user-check"></i> Activate';
            statusButton.setAttribute('onclick', `toggleStatusAjax(${userId}, 'toggle_active', '${userName}', false)`);
            statusButton.className = 'btn btn-sm btn-outline-success';
        }
    }

    // Enhanced modal functionality
    window.changeRole = function(userId, action) {
        document.getElementById('role_user_id').value = userId;
        document.getElementById('role_action').value = action;
        
        const userName = event.target.closest('tr').cells[0].textContent.trim();
        const message = action === 'make_admin' ? 
            `Are you sure you want to make "${userName}" an administrator? This will give them full access to the admin panel.` :
            `Are you sure you want to demote "${userName}" to a regular user? They will lose admin privileges.`;
        
        document.getElementById('role_message').textContent = message;
        
        const modal = new bootstrap.Modal(document.getElementById('roleModal'));
        modal.show();
    };

    window.toggleStatus = function(userId, action) {
        document.getElementById('status_user_id').value = userId;
        document.getElementById('status_action').value = action;
        
        const userName = event.target.closest('tr').cells[0].textContent.trim();
        const isActive = event.target.closest('tr').getAttribute('data-status') === 'active';
        const message = isActive ? 
            `Are you sure you want to deactivate "${userName}"? They will not be able to log in or make bookings.` :
            `Are you sure you want to activate "${userName}"? They will be able to log in and make bookings.`;
        
        document.getElementById('status_message').textContent = message;
        
        const modal = new bootstrap.Modal(document.getElementById('statusModal'));
        modal.show();
    };

    // Add user IDs to table rows for easier manipulation
    function addUserIdsToRows() {
        const tableRows = document.querySelectorAll('#usersTable tbody tr');
        tableRows.forEach(row => {
            const roleButton = row.querySelector('button[onclick*="changeRole"]');
            const statusButton = row.querySelector('button[onclick*="toggleStatus"]');
            
            if (roleButton) {
                const onclickAttr = roleButton.getAttribute('onclick');
                const userIdMatch = onclickAttr.match(/changeRole\((\d+),/);
                if (userIdMatch) {
                    row.setAttribute('data-user-id', userIdMatch[1]);
                }
            } else if (statusButton) {
                const onclickAttr = statusButton.getAttribute('onclick');
                const userIdMatch = onclickAttr.match(/toggleStatus\((\d+),/);
                if (userIdMatch) {
                    row.setAttribute('data-user-id', userIdMatch[1]);
                }
            }
        });
    }

    // Bulk actions functionality - COMPLETELY DISABLED
    function initBulkActions() {
        // Bulk actions disabled - only keeping export functionality
        console.log('Bulk actions disabled by admin request');
        
        // Force remove any bulk action elements that might have been added
        removeBulkActionElements();
    }
    
    // Force remove bulk action elements
    function removeBulkActionElements() {
        // Remove any bulk action controls that might exist
        const bulkActionsDiv = document.getElementById('bulkActions');
        if (bulkActionsDiv) {
            bulkActionsDiv.remove();
        }
        
        // Remove select all checkboxes
        const selectAllCheckboxes = document.querySelectorAll('#selectAll, #selectAllTable');
        selectAllCheckboxes.forEach(checkbox => checkbox.remove());
        
        // Remove user checkboxes
        const userCheckboxes = document.querySelectorAll('.user-checkbox');
        userCheckboxes.forEach(checkbox => {
            const cell = checkbox.closest('td');
            if (cell) cell.remove();
        });
        
        // Remove checkbox headers
        const checkboxHeaders = document.querySelectorAll('.checkbox-header');
        checkboxHeaders.forEach(header => header.remove());
        
        // Remove bulk action selects and buttons
        const bulkSelects = document.querySelectorAll('#bulkActionSelect, #applyBulkAction');
        bulkSelects.forEach(element => element.remove());
    }

    function applyBulkAction(userIds, action) {
        // Bulk actions disabled by admin request
        console.log('Bulk action attempted but disabled:', action, userIds);
        showNotification('Bulk actions have been disabled by administrator', 'warning');
        return;
    }

    // Export functionality - KEPT AS REQUESTED
    function initExportFeatures() {
        const cardHeader = document.querySelector('.card-header');
        if (cardHeader && !document.getElementById('exportBtn')) {
            // Create export button without bulk actions
            const exportContainer = document.createElement('div');
            exportContainer.className = 'd-flex justify-content-between align-items-center';
            exportContainer.innerHTML = `
                <h5 class="mb-0">All Users</h5>
                <button id="exportBtn" class="btn btn-outline-primary">
                    <i class="fas fa-download"></i> Export Users
                </button>
            `;
            
            // Replace the existing content
            cardHeader.innerHTML = '';
            cardHeader.appendChild(exportContainer);
            
            // Add event listener to the new button
            document.getElementById('exportBtn').onclick = exportUsersData;
        }
    }

    window.exportUsersData = function() {
        // Get visible table rows (respecting current filters)
        const tableRows = document.querySelectorAll('#usersTable tbody tr');
        let csvContent = "Name,Email,Role,Status,Faculty,Department,Date Joined\n";
        
        tableRows.forEach(row => {
            if (row.style.display !== 'none' && row.cells.length > 1) {
                // Extract data from each visible row (skip actions column)
                const name = row.cells[0].textContent.trim();
                const email = row.cells[1].textContent.trim();
                const role = row.cells[2].textContent.trim();
                const status = row.cells[3].textContent.trim();
                const faculty = row.cells[4].textContent.trim();
                const department = row.cells[5].textContent.trim();
                const dateJoined = row.cells[6].textContent.trim();
                
                const rowData = [name, email, role, status, faculty, department, dateJoined]
                    .map(cell => `"${cell.replace(/"/g, '""')}"`)
                    .join(',');
                csvContent += rowData + "\n";
            }
        });

        // Create and download the CSV file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `users_export_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('User data exported successfully!', 'success');
    };

    // Initialize all functionality
    addUserIdsToRows();
    initUserSearch();
    // initBulkActions(); // DISABLED - Bulk actions removed by admin request
    initExportFeatures(); // KEPT - Export functionality maintained
    
    // Force remove bulk actions after a short delay (in case other scripts add them)
    setTimeout(function() {
        removeBulkActionElements();
        console.log('Bulk actions forcefully removed');
    }, 100);
    
    // Also remove bulk actions on any dynamic content changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                setTimeout(removeBulkActionElements, 50);
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Add responsive table handling
    function makeTableResponsive() {
        const table = document.getElementById('usersTable');
        if (table && window.innerWidth <= 768) {
            table.classList.add('table-sm');
        }
    }

    window.addEventListener('resize', makeTableResponsive);
    makeTableResponsive();
});
