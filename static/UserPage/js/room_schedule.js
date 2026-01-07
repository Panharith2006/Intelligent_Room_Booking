// Declare weekOffset globally to avoid initialization errors
let weekOffset = 0;
// room_schedule.js - JS logic for Room Booking Calendar

document.addEventListener('DOMContentLoaded', function() {
    // Floating + button opens create booking modal
    const floatingCreateBtn = document.getElementById('floatingCreateBtn');
    if (floatingCreateBtn) {
        floatingCreateBtn.onclick = function() {
            window.location.href = '/accounts/booking/';
        };
    }
    // Fix: Declare weekOffset at the top to avoid initialization errors
    // Tab logic
    const calendarTabBtn = document.getElementById('calendarTabBtn');
    const tableTabBtn = document.getElementById('tableTabBtn');
    const calendarViewPanel = document.getElementById('calendarViewPanel');
    const tableViewPanel = document.getElementById('tableViewPanel');
    calendarTabBtn.onclick = function() {
        calendarViewPanel.classList.remove('hidden');
        tableViewPanel.classList.add('hidden');
        calendarTabBtn.classList.add('bg-indigo-500', 'text-white');
        calendarTabBtn.classList.remove('bg-gray-200', 'text-indigo-700');
        tableTabBtn.classList.remove('bg-indigo-500', 'text-white');
        tableTabBtn.classList.add('bg-gray-200', 'text-indigo-700');
    };
    tableTabBtn.onclick = function() {
        calendarViewPanel.classList.add('hidden');
        tableViewPanel.classList.remove('hidden');
        tableTabBtn.classList.add('bg-indigo-500', 'text-white');
        tableTabBtn.classList.remove('bg-gray-200', 'text-indigo-700');
        calendarTabBtn.classList.remove('bg-indigo-500', 'text-white');
        calendarTabBtn.classList.add('bg-gray-200', 'text-indigo-700');
    };
    tableTabBtn.click();

    // Elements
    const calendarEl = document.getElementById('calendar');
    const bookingModal = document.getElementById('bookingModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalContent = document.getElementById('modalContent');
    const modalRoomName = document.getElementById('modalRoomName');
    const roomFilter = document.getElementById('filterRoom');
    const filterStartDate = document.getElementById('filterStartDate');
    const filterEndDate = document.getElementById('filterEndDate');
    const filterUser = document.getElementById('filterUser');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const refreshTableBtn = document.getElementById('refreshTableBtn');
    const bookingTableBody = document.getElementById('bookingTableBody');
    const noTableBookingsMsg = document.getElementById('noTableBookingsMsg');
    const currentUserId = window.currentUserId || null;
    let allBookings = [];
    let todaysBookings = [];

    // Debug panel
    function showDebugPanel(bookings) {
        const debugPanel = document.getElementById('debugPanel');
        if (!debugPanel) return;
        debugPanel.innerHTML = `<pre style="max-height:300px;overflow:auto;background:#f3f4f6;border-radius:8px;padding:12px;font-size:12px;">${JSON.stringify(bookings, null, 2)}</pre>`;
    }
    function showDebugPanelTable(bookings) {
        const tablePanel = document.getElementById('tableViewPanel');
        if (!tablePanel) return;
        let debugDiv = document.getElementById('debugPanelTable');
        if (!debugDiv) {
            debugDiv = document.createElement('div');
            debugDiv.id = 'debugPanelTable';
            debugDiv.className = 'mb-2';
            tablePanel.insertBefore(debugDiv, tablePanel.firstChild);
        }
        debugDiv.innerHTML = `<pre style="max-height:200px;overflow:auto;background:#f3f4f6;border-radius:8px;padding:8px;font-size:12px;">${JSON.stringify(bookings, null, 2)}</pre>`;
    }

    // Fetch all bookings
    function fetchAllBookingsTable() {
        const apiUrl = window.apiRoomBookingsUrl || '/accounts/api/room-bookings/';
        axios.get(apiUrl)
        .then(response => {
            allBookings = response.data.slice().sort((a, b) => {
                if (a.created && b.created) {
                    return new Date(b.created) - new Date(a.created);
                }
                return new Date(b.start) - new Date(a.start);
            });
            renderBookingTable(allBookings);
            renderWeeklyBookings(allBookings);
            renderPreviousUserBookings(allBookings);
            // Ensure Prev/Next buttons always work
            const prevWeekBtn = document.getElementById('prevWeekBtn');
            const nextWeekBtn = document.getElementById('nextWeekBtn');
            if (prevWeekBtn) {
                prevWeekBtn.onclick = function() {
                    weekOffset--;
                    renderWeeklyBookings(allBookings);
                };
            }
            if (nextWeekBtn) {
                nextWeekBtn.onclick = function() {
                    weekOffset++;
                    renderWeeklyBookings(allBookings);
                };
            }
            // Hide debug panel unless error
            const debugPanel = document.getElementById('tableDebugPanel');
            if (debugPanel) debugPanel.style.display = 'none';
            if (allBookings.length === 0 && noTableBookingsMsg) {
                noTableBookingsMsg.classList.remove('hidden');
                noTableBookingsMsg.textContent = 'No bookings found.';
            } else if (noTableBookingsMsg) {
                noTableBookingsMsg.classList.add('hidden');
            }
        })
        .catch(error => {
            bookingTableBody.innerHTML = '';
            const debugPanel = document.getElementById('tableDebugPanel');
            if (debugPanel) {
                debugPanel.style.display = '';
                debugPanel.innerHTML = `<strong>Error fetching bookings:</strong><br><pre>${error && error.response ? JSON.stringify(error.response.data, null, 2) : error.message}</pre>`;
            }
            if (noTableBookingsMsg) {
                noTableBookingsMsg.textContent = 'Error fetching bookings.';
                noTableBookingsMsg.classList.remove('hidden');
            }
            console.error('Error fetching bookings:', error);
        });
    }
    // Professional: Render today's bookings as hourly slots (00:00-24:00)
    function renderTodaysBookings(bookings) {
        const tbody = document.getElementById('todaysBookingsBody');
        if (!tbody) return;
        tbody.innerHTML = '';
        const today = new Date();
        today.setHours(0,0,0,0);
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);
        const todaysBookings = bookings.filter(ev => {
            const start = new Date(ev.start);
            const end = new Date(ev.end);
            return start < tomorrow && end > today;
        });
        // Only show 7AM to 9PM
        for (let hour = 7; hour <= 21; hour++) {
            let slotStart = new Date(today);
            slotStart.setHours(hour, 0, 0, 0);
            let slotEnd = new Date(today);
            slotEnd.setHours(hour+1, 0, 0, 0);
            let slotBookings = todaysBookings.filter(ev => {
                const start = new Date(ev.start);
                const end = new Date(ev.end);
                return start < slotEnd && end > slotStart;
            });
            if (slotBookings.length === 0) {
                tbody.innerHTML += `<tr class="transition">
                    <td class="px-4 py-2">${slotStart.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} - ${slotEnd.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</td>
                    <td class="px-4 py-2 text-gray-400">-</td>
                    <td class="px-4 py-2 text-gray-400">-</td>
                    <td class="px-4 py-2 text-gray-400">-</td>
                </tr>`;
            } else {
                slotBookings.forEach(ev => {
                    let statusColor = ev.status === 'confirmed' ? 'bg-green-100 text-green-700' : ev.status === 'pending' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
                    let statusText = ev.status ? (ev.status.charAt(0).toUpperCase() + ev.status.slice(1)) : '';
                    let ownRow = ev.user_id == currentUserId ? 'font-bold bg-indigo-50' : '';
                    let userDisplay = (ev.user_id == currentUserId || (ev.user && ev.user.toLowerCase() === 'daly')) ? `${ev.user} <span class="text-indigo-600 font-semibold">(You)</span>` : ev.user;
                    tbody.innerHTML += `<tr class="transition ${ownRow}" tabindex="0">
                        <td class="px-4 py-2">${slotStart.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})} - ${slotEnd.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}</td>
                        <td class="px-4 py-2">${userDisplay ? userDisplay : '<span class="text-gray-400">-</span>'}</td>
                        <td class="px-4 py-2">${ev.room_name ? ev.room_name : '<span class="text-gray-400">-</span>'} ${ev.room_number ? '(' + ev.room_number + ')' : ''}</td>
                        <td class="px-4 py-2"><span class="rounded px-2 py-1 ${statusColor}">${statusText ? statusText : '-'}</span></td>
                    </tr>`;
                });
            }
        }
    }

    // Render table rows
    function renderBookingTable(bookings) {
        bookingTableBody.innerHTML = '';
        if (!bookings || bookings.length === 0) {
            bookingTableBody.innerHTML = '';
            if (noTableBookingsMsg) noTableBookingsMsg.classList.remove('hidden');
            return;
        }
        if (noTableBookingsMsg) noTableBookingsMsg.classList.add('hidden');
        bookings.forEach(ev => {
            let isOwn = ev.user_id == currentUserId || (ev.user && ev.user.trim().toLowerCase() === 'daly chea'.toLowerCase());
            let userDisplay = isOwn ? `${ev.user} <span class="text-indigo-600 font-semibold">(You)</span>` : ev.user;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-4 py-2">${userDisplay}</td>
                <td class="px-4 py-2">${ev.room_name} ${ev.room_number ? '(' + ev.room_number + ')' : ''}</td>
                <td class="px-4 py-2">${ev.start ? new Date(ev.start).toLocaleDateString() : '-'}</td>
                <td class="px-4 py-2">${ev.start ? new Date(ev.start).toLocaleTimeString() : '-'} - ${ev.end ? new Date(ev.end).toLocaleTimeString() : '-'}</td>
            `;
            bookingTableBody.appendChild(tr);
        });
    }

    // Filter logic
    function applyFilters() {
        let filtered = allBookings.slice();
        if (filterStartDate.value) {
            filtered = filtered.filter(ev => new Date(ev.start) >= new Date(filterStartDate.value));
        }
        if (filterEndDate.value) {
            filtered = filtered.filter(ev => new Date(ev.end) <= new Date(filterEndDate.value));
        }
        if (roomFilter.value) {
            filtered = filtered.filter(ev => String(ev.room_id) === String(roomFilter.value));
        }
        if (filterUser.value) {
            filtered = filtered.filter(ev => ev.user && ev.user.toLowerCase().includes(filterUser.value.toLowerCase()));
        }
        renderBookingTable(filtered);
    }
    applyFiltersBtn.onclick = function(e) {
        e.preventDefault();
        applyFilters();
    };
    refreshTableBtn.onclick = function(e) {
        e.preventDefault();
        filterStartDate.value = '';
        filterEndDate.value = '';
        roomFilter.value = '';
        filterUser.value = '';
        fetchAllBookingsTable();
    };

    // Initial fetch
    fetchAllBookingsTable();
    setInterval(fetchAllBookingsTable, 30000);

    // Calendar logic
    let calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridWeek',
        themeSystem: 'standard',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'timeGridWeek,timeGridDay'
        },
        height: 'auto',
        aspectRatio: 1.6,
        slotMinTime: '13:00:00',
        slotMaxTime: '23:59:59',
        allDaySlot: false,
        firstDay: 0,
        weekends: true,
        nowIndicator: true,
        selectable: true,
        selectMirror: true,
        dayMaxEvents: true,
        eventDisplay: 'block',
        events: function(fetchInfo, successCallback, failureCallback) {
            axios.get(window.apiRoomBookingsUrl, {
                params: {
                    start: fetchInfo.startStr,
                    end: fetchInfo.endStr,
                    room_id: roomFilter.value || ''
                }
            })
            const apiUrl = window.apiRoomBookingsUrl || '/accounts/api/room-bookings/';
            axios.get(apiUrl, {
                params: {
                    start: fetchInfo.startStr,
                    end: fetchInfo.endStr,
                    room_id: roomFilter.value || ''
                }
            })
            .then(response => {
                const events = response.data.map(ev => ({
                    id: ev.id,
                    title: ev.room_name,
                    start: ev.start,
                    end: ev.end,
                    status: ev.status,
                    user: ev.user,
                    user_id: ev.user_id,
                    room_name: ev.room_name,
                    room_number: ev.room_number,
                    building: ev.building,
                    location: ev.location
                }));
                successCallback(events);
                // Show/hide noEventsMsg
                const noEventsMsg = document.getElementById('noEventsMsg');
                if (events.length === 0) {
                    if (noEventsMsg) noEventsMsg.classList.remove('hidden');
                } else {
                    if (noEventsMsg) noEventsMsg.classList.add('hidden');
                }
            })
            .catch(error => {
                if (failureCallback) failureCallback(error);
                const noEventsMsg = document.getElementById('noEventsMsg');
                if (noEventsMsg) {
                    noEventsMsg.textContent = 'Error fetching calendar events.';
                    noEventsMsg.classList.remove('hidden');
                }
                console.error('Error fetching calendar events:', error);
            });
        },
        eventContent: function(arg) {
            var status = arg.event.extendedProps.status;
            var isOwn = arg.event.extendedProps.user_id == currentUserId;
            var color = '#2563eb';
            var textColor = '#fff';
            var user = arg.event.extendedProps.user || '';
            var room = arg.event.extendedProps.room_name || '';
            var roomNumber = arg.event.extendedProps.room_number ? ' (' + arg.event.extendedProps.room_number + ')' : '';
            var userDisplay = isOwn ? `${user} <span style=\"color:#fff;font-weight:600;\">(You)</span>` : user;
            var tooltip = `${room}${roomNumber}\n${user}${isOwn ? ' (You)' : ''}\n${formatEventTime(arg.event)}`;
            return {
                html: `<div title="${tooltip}" style="background:${color};color:${textColor};padding:4px 8px;border-radius:8px;font-size:1em;font-weight:600;box-shadow:0 2px 8px rgba(60,64,67,0.10);margin-bottom:2px;display:flex;flex-direction:column;align-items:flex-start;">
                    <span style="font-weight:600;">${room}${roomNumber}</span>
                    <span style="font-size:0.95em;opacity:0.95;">${userDisplay}</span>
                    <span style="opacity:0.8;font-size:12px;">${formatEventTime(arg.event)}</span>
                </div>`
            };
            function formatEventTime(ev) {
                if (ev.allDay) {
                    return 'All day';
                }
                const start = ev.start;
                const end = ev.end;
                if (!start || !end) return '';
                const startStr = start.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                const endStr = end.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                return `${startStr} - ${endStr}`;
            }
        },
        eventClick: function(arg) {
            showModal(arg.event.extendedProps, true);
        },
        select: function(selectionInfo) {
            showCreateBookingModal(selectionInfo.startStr, selectionInfo.endStr);
        },
    });
    calendar.render();
    setInterval(function() { calendar.refetchEvents(); }, 30000);

    // Calendar navigation
    if (document.getElementById('prevBtn')) document.getElementById('prevBtn').onclick = function() { calendar.prev(); };
    if (document.getElementById('nextBtn')) document.getElementById('nextBtn').onclick = function() { calendar.next(); };
    if (document.getElementById('todayBtn')) document.getElementById('todayBtn').onclick = function() { calendar.today(); };
    if (document.getElementById('datePicker')) document.getElementById('datePicker').onchange = function() {
        if (this.value) calendar.gotoDate(this.value);
    };
    if (document.getElementById('calendarView')) document.getElementById('calendarView').onchange = function() {
        calendar.changeView(this.value);
    };

    // Modal logic
    function showModal(details, canEdit=false) {
        let buildingName = details.building || '';
        if (!buildingName && details.location) {
            let match = details.location.match(/(Building|Bldg)\s*[A-Za-z0-9]+/i);
            if (match) buildingName = match[0];
            else buildingName = details.location.split(',')[0].trim();
        }
        modalRoomName.textContent = details.room_name || 'Booking Details';
        modalContent.innerHTML = `
            <div style="display:flex;align-items:center;gap:8px;"><strong>Room:</strong> <span class="text-indigo-700">${details.room_name}</span> <span class="text-gray-700">${details.room_number ? '(' + details.room_number + ')' : ''}</span> <span style="color:#667eea;font-weight:500;display:inline-flex;align-items:center;"><i class="bi bi-geo-alt" style="margin-right:4px;"></i> ${buildingName}</span></div>
            <div><strong>Time:</strong> <span class="text-gray-700">${details.start} - ${details.end}</span></div>
            <div><strong>Purpose:</strong> <span class="text-gray-700">${details.purpose || 'N/A'}</span></div>
            ${canEdit ? `<button id='editBookingBtn' class='google-btn bg-yellow-100 text-yellow-700 mt-2'>Edit Booking</button>` : ''}
        `;
        bookingModal.classList.remove('hidden');
        if (canEdit) {
            document.getElementById('editBookingBtn').onclick = function() {
                alert('Edit booking feature coming soon!');
            };
        }
    }
    closeModalBtn.onclick = function() { bookingModal.classList.add('hidden'); };
    bookingModal.onclick = function(e) { if (e.target === bookingModal) bookingModal.classList.add('hidden'); };

    // Create booking modal (placeholder)
    function showCreateBookingModal(start, end) {
    window.location.href = '/accounts/booking/';
    }
    if (document.getElementById('createBtn')) document.getElementById('createBtn').onclick = function() { showCreateBookingModal('', ''); };
    if (document.getElementById('floatingCreateBtn')) document.getElementById('floatingCreateBtn').onclick = function() { showCreateBookingModal('', ''); };

    // Render calendar table (always show week grid with hourly slots)
    function renderCalendarTable(events, rangeStart, rangeEnd) {
        const tableHeader = document.getElementById('calendarTableHeader');
        const tableBody = document.getElementById('calendarTableBody');
        let startDate = new Date(rangeStart);
        let days = [];
        for (let i = 0; i < 7; i++) {
            let d = new Date(startDate);
            d.setDate(startDate.getDate() + i);
            days.push(d);
        }
        tableHeader.innerHTML = '<th class="px-2 py-2 bg-gray-100 text-xs text-gray-700">Time</th>' + days.map(day => `<th class="px-2 py-2 bg-gray-100 text-xs text-gray-700">${day.getDate()} ${day.toLocaleString('default',{month:'short'})} (${day.toLocaleString('default',{weekday:'short'})})</th>`).join('');
        tableBody.innerHTML = '';
        for (let hour = 7; hour <= 20; hour++) {
            let row = `<tr>`;
            row += `<td class="px-2 py-2 text-xs text-gray-700 bg-gray-50">${hour.toString().padStart(2,'0')}:00</td>`;
            for (let dayIdx = 0; dayIdx < days.length; dayIdx++) {
                let cellDate = new Date(days[dayIdx]);
                cellDate.setHours(hour,0,0,0);
                let cellEnd = new Date(cellDate); cellEnd.setHours(hour+1,0,0,0);
                let cellEvents = events.filter(ev => {
                    let evStart = new Date(ev.start);
                    let evEnd = new Date(ev.end);
                    return evStart < cellEnd && evEnd > cellDate;
                });
                if (cellEvents.length === 0) {
                    row += `<td class="px-2 py-2 border text-gray-300 text-xs text-center cursor-pointer" data-date="${cellDate.toISOString()}" data-hour="${hour}">-</td>`;
                } else {
                    row += `<td class="px-2 py-2 border text-xs text-center cursor-pointer" style="background:#e8f0fe;">`;
                    row += cellEvents.map(ev => {
                        const roomText = ev.room_name + (ev.room_number ? ' (' + ev.room_number + ')' : '');
                        const userText = ev.user + (ev.user_id == currentUserId ? ' <span style=\"color:#fff;font-weight:600;\">(You)</span>' : '');
                        return `<div class=\"rounded px-2 py-1 mb-1\" style=\"background:#2563eb;color:white;font-size:12px;cursor:pointer;\" title=\"${roomText} | ${ev.user}\">${roomText}<br><span style='font-size:11px;'>${userText}</span></div>`;
                    }).join('');
                    row += `</td>`;
                }
            }
            row += `</tr>`;
            tableBody.innerHTML += row;
        }
        Array.from(tableBody.querySelectorAll('td[data-date]')).forEach(cell => {
            cell.onclick = function() {
                let dateStr = cell.getAttribute('data-date');
                let hour = cell.getAttribute('data-hour');
                let start = new Date(dateStr);
                let end = new Date(start); end.setHours(start.getHours()+1);
                showCreateBookingModal(start.toISOString(), end.toISOString());
            };
        });
        Array.from(tableBody.querySelectorAll('div[title]')).forEach(evDiv => {
            evDiv.onclick = function(e) {
                e.stopPropagation();
                let title = evDiv.getAttribute('title');
                let event = events.find(ev => (ev.room_name + (ev.room_number ? ' ('+ev.room_number+')':'') + ' | ' + ev.user) === title);
                if (event) showModal(event, true);
            };
        });
    }

    // Weekly bookings rendering
    function renderWeeklyBookings(bookings) {
        const tbody = document.getElementById('weeklyBookingsBody');
        if (!tbody) return;
        // Show loading spinner if present
        let spinner = document.getElementById('weeklyGridLoading');
        if (spinner) spinner.style.display = '';
        tbody.innerHTML = '';
        // Get start of week (Monday) with offset
        const today = new Date();
        const weekStart = new Date(today);
        weekStart.setDate(today.getDate() - ((today.getDay() + 6) % 7) + weekOffset * 7);
        weekStart.setHours(0,0,0,0);
        // Update week range label
        const weekRangeLabel = document.getElementById('weekRangeLabel');
        if (weekRangeLabel) {
            let weekEnd = new Date(weekStart);
            weekEnd.setDate(weekStart.getDate() + 6);
            let month = weekStart.toLocaleString('default', { month: 'long' });
            let year = weekStart.getFullYear();
            weekRangeLabel.textContent = `${month} ${weekStart.getDate()} - ${weekEnd.getDate()}, ${year}`;
        }
        // Render weekday headers with date
        const headerRow = document.getElementById('weeklyGridHeaderRow');
        if (headerRow) {
            headerRow.innerHTML = `<th class="px-4 py-2 text-left text-xs font-semibold text-gray-700 uppercase">Time</th>`;
            for (let day = 0; day < 7; day++) {
                let cellDate = new Date(weekStart);
                cellDate.setDate(weekStart.getDate() + day);
                let weekday = cellDate.toLocaleString('default', { weekday: 'short' });
                let dateStr = `${cellDate.getDate()} ${cellDate.toLocaleString('default', { month: 'short' })}`;
                headerRow.innerHTML += `<th class="px-4 py-2 text-center text-xs font-semibold text-gray-700 uppercase">${weekday}<br><span class="text-xs text-gray-500">${dateStr}</span></th>`;
            }
        }
    // Find all unique booking time ranges for the week
    let timeRanges = [];
    for (let day = 0; day < 7; day++) {
        let cellDate = new Date(weekStart);
        cellDate.setDate(weekStart.getDate() + day);
        let bookingsForDay = bookings.filter(ev => {
            let evStart = new Date(ev.start);
            return evStart.toDateString() === cellDate.toDateString();
        });
        bookingsForDay.forEach(ev => {
            let evStart = new Date(ev.start);
            let evEnd = new Date(ev.end);
            let startStr = evStart.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
            let endStr = evEnd.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
            let found = timeRanges.find(tr => tr.start === startStr && tr.end === endStr);
            if (!found) timeRanges.push({ start: startStr, end: endStr });
        });
    }
    // Sort timeRanges by start time
    timeRanges.sort((a, b) => a.start.localeCompare(b.start));
    // If no bookings, show default hourly slots
    if (timeRanges.length === 0) {
        for (let hour = 7; hour <= 21; hour++) {
            let row = `<tr>`;
            row += `<td class="px-4 py-2 text-xs text-gray-700 bg-gray-50">${hour.toString().padStart(2,'0')}:00</td>`;
            for (let day = 0; day < 7; day++) {
                row += `<td class="px-4 py-2 border text-gray-300 text-xs text-center cursor-pointer">-</td>`;
            }
            row += `</tr>`;
            tbody.innerHTML += row;
        }
    } else {
        // Render rows for each unique booking time range
        timeRanges.forEach(tr => {
            let row = `<tr>`;
            row += `<td class="px-4 py-2 text-xs text-gray-700 bg-gray-50">${tr.start} - ${tr.end}</td>`;
            for (let day = 0; day < 7; day++) {
                let cellDate = new Date(weekStart);
                cellDate.setDate(weekStart.getDate() + day);
                let cellBookings = bookings.filter(ev => {
                    let evStart = new Date(ev.start);
                    let evEnd = new Date(ev.end);
                    let startStr = evStart.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                    let endStr = evEnd.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
                    return evStart.toDateString() === cellDate.toDateString() && startStr === tr.start && endStr === tr.end;
                });
                if (cellBookings.length === 0) {
                    row += `<td class="px-4 py-2 border text-gray-300 text-xs text-center cursor-pointer">-</td>`;
                } else {
                    let ev = cellBookings[0];
                    let statusColor = ev.status === 'confirmed' ? 'bg-green-100 text-green-700' : ev.status === 'pending' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
                    let userDisplay = (ev.user_id == currentUserId || (ev.user && ev.user.trim().toLowerCase() === 'daly chea')) ? `${ev.user} <span class="text-indigo-600 font-semibold">(You)</span>` : ev.user;
                    row += `<td class="px-2 py-2 border text-xs text-center cursor-pointer ${statusColor}" style="background:#e8f0fe;">
                        <div><span>${userDisplay}</span></div>
                        <div><span>${ev.room_name}${ev.room_number ? ' (' + ev.room_number + ')' : ''}</span></div>
                        <div><span>${ev.status ? ev.status.charAt(0).toUpperCase() + ev.status.slice(1) : '-'}</span></div>
                    </td>`;
                }
            }
            row += `</tr>`;
            tbody.innerHTML += row;
        });
    }
    }

    // Call renderCalendarTable on initial load
    let initialStart = new Date();
    initialStart.setDate(initialStart.getDate() - initialStart.getDay());
    let initialEnd = new Date(initialStart);
    initialEnd.setDate(initialEnd.getDate() + 6);
    renderCalendarTable(allBookings, initialStart, initialEnd);

    // Add event listeners for week navigation
    window.addEventListener('DOMContentLoaded', function() {
        const prevWeekBtn = document.getElementById('prevWeekBtn');
        const nextWeekBtn = document.getElementById('nextWeekBtn');
        function setLoading(isLoading) {
            const spinner = document.getElementById('weeklyGridLoading');
            if (spinner) spinner.style.display = isLoading ? '' : 'none';
            if (prevWeekBtn) prevWeekBtn.disabled = isLoading;
            if (nextWeekBtn) nextWeekBtn.disabled = isLoading;
        }
        if (prevWeekBtn) {
            prevWeekBtn.onclick = function() {
                setLoading(true);
                weekOffset--;
                setTimeout(() => {
                    renderWeeklyBookings(allBookings);
                    setLoading(false);
                }, 200);
            };
        }
        if (nextWeekBtn) {
            nextWeekBtn.onclick = function() {
                setLoading(true);
                weekOffset++;
                setTimeout(() => {
                    renderWeeklyBookings(allBookings);
                    setLoading(false);
                }, 200);
            };
        }
    // Hide loading spinner after render (this line is removed)
    });

    // Real-time update for weekly booking grid
    let bookingRefreshInterval = null;
    function startBookingAutoRefresh() {
        if (bookingRefreshInterval) clearInterval(bookingRefreshInterval);
        bookingRefreshInterval = setInterval(() => {
            fetchAllBookingsTable();
        }, 30000); // 30 seconds
    }
    window.addEventListener('DOMContentLoaded', function() {
        startBookingAutoRefresh();
    });

    // Render previous user bookings
    function renderPreviousUserBookings(bookings) {
        const prevDiv = document.getElementById('previousUserBookings');
        if (!prevDiv) return;
        // Filter for current user
        const userBookings = bookings.filter(ev => ev.user_id == currentUserId || (ev.user && ev.user.trim().toLowerCase() === 'daly chea'));
        if (userBookings.length === 0) {
            prevDiv.innerHTML = '<div class="text-gray-400">No previous bookings found.</div>';
            return;
        }
        prevDiv.innerHTML = '<table class="min-w-full"><thead><tr><th class="px-2 py-1">Room</th><th class="px-2 py-1">Date</th><th class="px-2 py-1">Time</th><th class="px-2 py-1">Status</th></tr></thead><tbody>' +
            userBookings.map(ev => `<tr><td class="px-2 py-1">${ev.room_name}${ev.room_number ? ' ('+ev.room_number+')' : ''}</td><td class="px-2 py-1">${ev.start ? new Date(ev.start).toLocaleDateString() : '-'}</td><td class="px-2 py-1">${ev.start ? new Date(ev.start).toLocaleTimeString() : '-'} - ${ev.end ? new Date(ev.end).toLocaleTimeString() : '-'}</td><td class="px-2 py-1">${ev.status ? ev.status.charAt(0).toUpperCase() + ev.status.slice(1) : '-'}</td></tr>`).join('') + '</tbody></table>';
    }

});
