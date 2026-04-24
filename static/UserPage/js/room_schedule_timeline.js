(function () {
    function renderTimeline(slots) {
        const panel = document.getElementById('roomTimelinePanel');
        if (!panel) return;

        if (!slots || !slots.length) {
            panel.innerHTML = '<small class="text-gray-500">No timeline data available.</small>';
            return;
        }

        panel.innerHTML = slots.map(function (slot) {
            const badgeClass = slot.status === 'available'
                ? 'bg-green-100 text-green-700'
                : (slot.status === 'occupied' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-200 text-gray-700');
            const label = slot.status.charAt(0).toUpperCase() + slot.status.slice(1);

            return '<div class="flex items-center justify-between border-b py-1">'
                + '<span>' + slot.start + ' - ' + slot.end + '</span>'
                + '<span class="px-2 py-0.5 rounded text-xs font-semibold ' + badgeClass + '">' + label + '</span>'
                + '</div>';
        }).join('');
    }

    function loadTimeline() {
        const roomSelect = document.getElementById('timelineRoomSelect');
        const dateInput = document.getElementById('timelineDateInput');
        const panel = document.getElementById('roomTimelinePanel');

        if (!roomSelect || !dateInput || !panel) return;

        const roomId = roomSelect.value;
        const dateValue = dateInput.value;
        if (!roomId || !dateValue) {
            panel.innerHTML = '<small class="text-gray-500">Select both room and date.</small>';
            return;
        }

        panel.innerHTML = '<small class="text-gray-500">Loading timeline...</small>';

        fetch(window.roomTimelineApiUrl + '?room_id=' + encodeURIComponent(roomId) + '&date=' + encodeURIComponent(dateValue))
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data.success) {
                    panel.innerHTML = '<small class="text-red-600">' + (data.error || 'Unable to load timeline.') + '</small>';
                    return;
                }
                renderTimeline(data.slots || []);
            })
            .catch(function () {
                panel.innerHTML = '<small class="text-red-600">Unable to load timeline.</small>';
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const loadBtn = document.getElementById('timelineLoadBtn');
        const roomSelect = document.getElementById('timelineRoomSelect');
        const dateInput = document.getElementById('timelineDateInput');

        if (loadBtn) loadBtn.addEventListener('click', loadTimeline);
        if (roomSelect) roomSelect.addEventListener('change', loadTimeline);
        if (dateInput) {
            if (!dateInput.value) {
                dateInput.value = new Date().toISOString().split('T')[0];
            }
            dateInput.addEventListener('change', loadTimeline);
        }

        loadTimeline();
    });
})();
