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

    // Enhanced room search and filtering
    function initRoomSearch() {
        const searchInput = document.getElementById('roomSearch');
        const typeFilter = document.getElementById('typeFilter');
        const availabilityFilter = document.getElementById('availabilityFilter');
        const capacityFilter = document.getElementById('capacityFilter');
        const roomCards = document.querySelectorAll('.room-card');

        function filterRooms() {
            const searchTerm = searchInput?.value.toLowerCase() || '';
            const selectedType = typeFilter?.value || '';
            const selectedAvailability = availabilityFilter?.value || '';
            const selectedCapacity = capacityFilter?.value || '';

            let visibleCount = 0;

            roomCards.forEach(card => {
                const roomName = card.querySelector('.room-name')?.textContent.toLowerCase() || '';
                const roomNumber = card.querySelector('.room-number')?.textContent.toLowerCase() || '';
                const roomType = card.getAttribute('data-type') || '';
                const roomAvailability = card.getAttribute('data-availability') || '';
                const roomCapacity = parseInt(card.getAttribute('data-capacity')) || 0;

                const matchesSearch = roomName.includes(searchTerm) || roomNumber.includes(searchTerm);
                const matchesType = !selectedType || roomType === selectedType;
                const matchesAvailability = !selectedAvailability || roomAvailability === selectedAvailability;
                
                let matchesCapacity = true;
                if (selectedCapacity) {
                    switch(selectedCapacity) {
                        case 'small': matchesCapacity = roomCapacity <= 20; break;
                        case 'medium': matchesCapacity = roomCapacity > 20 && roomCapacity <= 50; break;
                        case 'large': matchesCapacity = roomCapacity > 50; break;
                    }
                }

                if (matchesSearch && matchesType && matchesAvailability && matchesCapacity) {
                    card.style.display = '';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            updateSearchResults(visibleCount);
        }

        function updateSearchResults(count) {
            let resultDiv = document.getElementById('searchResults');
            if (!resultDiv) {
                resultDiv = document.createElement('div');
                resultDiv.id = 'searchResults';
                resultDiv.className = 'text-muted mb-3';
                const roomsContainer = document.querySelector('.rooms-grid');
                if (roomsContainer) {
                    roomsContainer.parentNode.insertBefore(resultDiv, roomsContainer);
                }
            }
            
            if (searchInput?.value || typeFilter?.value || availabilityFilter?.value || capacityFilter?.value) {
                resultDiv.textContent = `Showing ${count} room(s) matching your filters`;
                resultDiv.style.display = 'block';
            } else {
                resultDiv.style.display = 'none';
            }
        }

        // Debounced search
        let searchTimeout;
        searchInput?.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(filterRooms, 300);
        });

        typeFilter?.addEventListener('change', filterRooms);
        availabilityFilter?.addEventListener('change', filterRooms);
        capacityFilter?.addEventListener('change', filterRooms);

        // Initialize
        filterRooms();
    }

    // Room management functions
    window.viewRoom = function(roomId) {
        window.location.href = `/accounts/admin/rooms/${roomId}/`;
    };

    window.editRoom = function(roomId) {
        // Get room data and populate edit modal
        const roomCard = document.querySelector(`[data-room-id="${roomId}"]`);
        if (roomCard) {
            const modal = document.getElementById('editRoomModal');
            const form = modal.querySelector('form');
            
            // Populate form fields
            form.querySelector('[name="room_id"]').value = roomId;
            form.querySelector('[name="room_name"]').value = roomCard.querySelector('.room-name').textContent;
            form.querySelector('[name="room_number"]').value = roomCard.querySelector('.room-number').textContent;
            form.querySelector('[name="room_type"]').value = roomCard.getAttribute('data-type');
            form.querySelector('[name="capacity"]').value = roomCard.getAttribute('data-capacity');
            form.querySelector('[name="description"]').value = roomCard.querySelector('.room-description')?.textContent || '';
            form.querySelector('[name="equipment"]').value = roomCard.querySelector('.room-equipment')?.textContent || '';
            
            // Show modal
            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();
        }
    };

    window.deleteRoom = function(roomId, roomName) {
        if (confirm(`Are you sure you want to delete "${roomName}"? This action cannot be undone.`)) {
            const button = event.target.closest('button');
            const originalHTML = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
            button.disabled = true;

            const formData = new FormData();
            formData.append('action', 'delete_room');
            formData.append('room_id', roomId);
            formData.append('csrfmiddlewaretoken', getCSRFToken());

            fetch(window.location.pathname, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    const roomCard = document.querySelector(`[data-room-id="${roomId}"]`);
                    if (roomCard) {
                        roomCard.style.transition = 'opacity 0.3s ease';
                        roomCard.style.opacity = '0';
                        setTimeout(() => {
                            roomCard.remove();
                            updateRoomCounts();
                        }, 300);
                    }
                    showNotification(`Room "${roomName}" deleted successfully!`, 'success');
                } else {
                    throw new Error('Failed to delete room');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = originalHTML;
                button.disabled = false;
                showNotification('Failed to delete room. Please try again.', 'error');
            });
        }
    };

    window.toggleAvailability = function(roomId, roomName, currentAvailability) {
        const button = event.target.closest('button');
        const originalHTML = button.innerHTML;
        
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        button.disabled = true;

        const formData = new FormData();
        formData.append('action', 'toggle_availability');
        formData.append('room_id', roomId);
        formData.append('csrfmiddlewaretoken', getCSRFToken());

        fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                const newAvailability = !currentAvailability;
                updateRoomAvailabilityUI(roomId, newAvailability, button);
                const status = newAvailability ? 'available' : 'unavailable';
                showNotification(`Room "${roomName}" is now ${status}`, 'success');
            } else {
                throw new Error('Failed to toggle availability');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            button.innerHTML = originalHTML;
            button.disabled = false;
            showNotification('Failed to update room availability. Please try again.', 'error');
        });
    };

    function updateRoomAvailabilityUI(roomId, isAvailable, button) {
        const roomCard = document.querySelector(`[data-room-id="${roomId}"]`);
        if (!roomCard) return;

        // Update card data attribute
        roomCard.setAttribute('data-availability', isAvailable ? 'true' : 'false');

        // Update availability badge
        const availabilityBadge = roomCard.querySelector('.availability-badge');
        if (availabilityBadge) {
            if (isAvailable) {
                availabilityBadge.className = 'badge bg-success availability-badge';
                availabilityBadge.textContent = 'Available';
            } else {
                availabilityBadge.className = 'badge bg-danger availability-badge';
                availabilityBadge.textContent = 'Unavailable';
            }
        }

        // Update button
        if (isAvailable) {
            button.className = 'btn btn-outline-danger btn-sm';
            button.innerHTML = '<i class="fas fa-power-off"></i> Disable';
            button.setAttribute('onclick', `toggleAvailability(${roomId}, '${roomCard.querySelector('.room-name').textContent}', true)`);
        } else {
            button.className = 'btn btn-outline-success btn-sm';
            button.innerHTML = '<i class="fas fa-power-off"></i> Enable';
            button.setAttribute('onclick', `toggleAvailability(${roomId}, '${roomCard.querySelector('.room-name').textContent}', false)`);
        }

        updateRoomCounts();
    }

    function updateRoomCounts() {
        const totalRooms = document.querySelectorAll('.room-card').length;
        const availableRooms = document.querySelectorAll('.room-card[data-availability="true"]').length;
        const unavailableRooms = totalRooms - availableRooms;

        // Update statistics cards if they exist
        const totalCard = document.querySelector('.stat-total');
        const availableCard = document.querySelector('.stat-available');
        const unavailableCard = document.querySelector('.stat-unavailable');

        if (totalCard) totalCard.textContent = totalRooms;
        if (availableCard) availableCard.textContent = availableRooms;
        if (unavailableCard) unavailableCard.textContent = unavailableRooms;
    }

    // Form validation for add/edit room
    function initRoomFormValidation() {
        const addForm = document.querySelector('#addRoomModal form');
        const editForm = document.querySelector('#editRoomModal form');

        [addForm, editForm].forEach(form => {
            if (!form) return;

            form.addEventListener('submit', function(e) {
                const roomName = this.querySelector('[name="room_name"]').value.trim();
                const roomNumber = this.querySelector('[name="room_number"]').value.trim();
                const roomType = this.querySelector('[name="room_type"]').value;
                const capacity = this.querySelector('[name="capacity"]').value;

                if (!roomName) {
                    e.preventDefault();
                    showError(this.querySelector('[name="room_name"]'), 'Room name is required');
                    return;
                }

                if (!roomNumber) {
                    e.preventDefault();
                    showError(this.querySelector('[name="room_number"]'), 'Room number is required');
                    return;
                }

                if (!roomType) {
                    e.preventDefault();
                    showError(this.querySelector('[name="room_type"]'), 'Room type is required');
                    return;
                }

                if (!capacity || capacity <= 0) {
                    e.preventDefault();
                    showError(this.querySelector('[name="capacity"]'), 'Valid capacity is required');
                    return;
                }

                // Show loading state
                const submitBtn = this.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
                submitBtn.disabled = true;
            });
        });
    }

    function showError(field, message) {
        // Remove existing error
        const existingError = field.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        // Add new error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message text-danger small mt-1';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);

        // Focus on field
        field.focus();
        field.classList.add('is-invalid');

        // Remove error styling on input
        field.addEventListener('input', function() {
            this.classList.remove('is-invalid');
            const errorMsg = this.parentNode.querySelector('.error-message');
            if (errorMsg) {
                errorMsg.remove();
            }
        });
    }

    // Bulk actions for rooms
    function initBulkActions() {
        const selectAllCheckbox = document.getElementById('selectAllRooms');
        const roomCheckboxes = document.querySelectorAll('.room-checkbox');
        const bulkActionSelect = document.getElementById('bulkActionSelect');
        const applyBulkActionBtn = document.getElementById('applyBulkAction');

        if (!selectAllCheckbox || !bulkActionSelect || !applyBulkActionBtn) return;

        function updateBulkActionControls() {
            const checkedBoxes = document.querySelectorAll('.room-checkbox:checked');
            const hasSelection = checkedBoxes.length > 0;
            
            bulkActionSelect.disabled = !hasSelection;
            applyBulkActionBtn.disabled = !hasSelection || !bulkActionSelect.value;
            
            selectAllCheckbox.checked = checkedBoxes.length === roomCheckboxes.length;
        }

        selectAllCheckbox.addEventListener('change', function() {
            roomCheckboxes.forEach(cb => cb.checked = this.checked);
            updateBulkActionControls();
        });

        roomCheckboxes.forEach(cb => {
            cb.addEventListener('change', updateBulkActionControls);
        });

        bulkActionSelect.addEventListener('change', updateBulkActionControls);

        applyBulkActionBtn.addEventListener('click', function() {
            const selectedRooms = Array.from(document.querySelectorAll('.room-checkbox:checked')).map(cb => cb.value);
            const action = bulkActionSelect.value;
            
            if (selectedRooms.length > 0 && action) {
                applyBulkRoomAction(selectedRooms, action);
            }
        });

        // Initialize
        updateBulkActionControls();
    }

    function applyBulkRoomAction(roomIds, action) {
        const actionText = {
            'set_available': 'make available',
            'set_unavailable': 'make unavailable',
            'delete': 'delete'
        }[action];

        if (!confirm(`Are you sure you want to ${actionText} ${roomIds.length} room(s)?`)) {
            return;
        }

        const applyBtn = document.getElementById('applyBulkAction');
        const originalText = applyBtn.innerHTML;
        applyBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        applyBtn.disabled = true;

        const formData = new FormData();
        formData.append('action', 'bulk_action');
        formData.append('bulk_action_type', action);
        formData.append('room_ids', JSON.stringify(roomIds));
        formData.append('csrfmiddlewaretoken', getCSRFToken());

        fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                showNotification(`Bulk action applied successfully to ${roomIds.length} room(s)`, 'success');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error('Bulk action failed');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Bulk action failed. Please try again.', 'error');
        })
        .finally(() => {
            applyBtn.innerHTML = originalText;
            applyBtn.disabled = false;
        });
    }

    // Export rooms functionality
    window.exportRoomsData = function() {
        const visibleRooms = document.querySelectorAll('.room-card:not([style*="display: none"])');
        let csvContent = "Room Name,Room Number,Type,Capacity,Availability,Description,Equipment\n";
        
        visibleRooms.forEach(room => {
            const name = room.querySelector('.room-name').textContent.trim();
            const number = room.querySelector('.room-number').textContent.trim();
            const type = room.getAttribute('data-type');
            const capacity = room.getAttribute('data-capacity');
            const availability = room.getAttribute('data-availability') === 'true' ? 'Available' : 'Unavailable';
            const description = room.querySelector('.room-description')?.textContent.trim() || '';
            const equipment = room.querySelector('.room-equipment')?.textContent.trim() || '';
            
            const rowData = [name, number, type, capacity, availability, description, equipment]
                .map(field => `"${field}"`)
                .join(',');
            csvContent += rowData + "\n";
        });

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `rooms_export_${new Date().getTime()}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showNotification('Room data exported successfully', 'success');
    };

    // Room quick actions
    window.quickBookRoom = function(roomId) {
        window.location.href = `/accounts/booking/?room_id=${roomId}`;
    };

    // Initialize all functionality
    initRoomSearch();
    initRoomFormValidation();
    initBulkActions();

    // Add responsive handling
    function handleResponsive() {
        const roomsGrid = document.querySelector('.rooms-grid');
        if (roomsGrid && window.innerWidth <= 768) {
            roomsGrid.classList.add('mobile-view');
        } else if (roomsGrid) {
            roomsGrid.classList.remove('mobile-view');
        }
    }

    window.addEventListener('resize', handleResponsive);
    handleResponsive();

    // Initialize room counts
    updateRoomCounts();
});
