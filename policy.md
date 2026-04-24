# University Room Booking Policies

## 1. Booking Time Constraints

### Booking Window
- **When bookings are allowed:** 24/7 (any time)
- **Room availability:** Depends on admin configuration
- **Earliest booking:** Maximum 1 month in advance
- **Latest booking:** Minimum 1 hour before start time
  - **Penalty:** Late booking attempts are rejected; cannot proceed

### Booking Duration
- **Minimum duration:** 1 hour
- **Maximum duration per session:** 3 hours
- **Consecutive bookings rule:** Cannot exceed maximum time limit for the same room

---

## 2. Booking Limits per User

- **Maximum concurrent active bookings:** 5 active bookings at any time
- **After completion:** User can book one more once a previous booking is completed
- **Multiple rooms in same time slot:** NOT ALLOWED
  - Users cannot book multiple different rooms during overlapping time periods

---

## 3. Cancellation Policy

### Early/Normal Cancellations
- Users can cancel at any time
- **No penalty** for cancellations made ≥ 3 hours before start time

### Late Cancellations
- **Definition:** Cancellation less than 3 hours before scheduled start time
- **System tracking:** All late cancellations are recorded per user
- **Warning threshold:** At 2 late cancellations → system issues warning notification
- **Escalation:** Repeated late cancellations may result in:
  - Temporary booking restrictions
  - Administrative review
  - Further actions as deemed necessary

### Administrator Cancellations
- Administrators can cancel bookings at any time without penalty
- Valid reasons: maintenance, emergency, operational needs

---

## 4. Room Management

### Room Status Display
- Each room must display current status in real-time:
  - **Available:** Room can be booked
  - **Occupied:** Room is currently in use
  - **Unavailable for maintenance:** Room is under maintenance
- **Example:** 7-9am (Available) → 9am-12pm (Occupied) → 12pm-2pm (Maintenance)

### Room Capacity
- Each room has a specified capacity range based on design
- **Examples:**
  - Room Type A: 10-30 student capacity
  - Room Type B: 12-20 student capacity
- Users must select rooms matching their group size

### Room Usage Agreement
- Users must accept a term agreement that includes:
  - No property damage
  - Close AC/HVAC before leaving
  - General facility care

### Status Management
- Rooms change status **automatically** based on booking schedule
- **Admin override:** Administrators can manually control status changes

---

## 5. Conflict Prevention & Validation

- **Double booking prevention:** System prevents any room from being booked twice in overlapping time slots (automatic)
- **Overlapping time slots:** Not allowed - system validates before confirmation
- **Past bookings:** Cannot book rooms in the past (validation check)
- **Availability verification:** All validation checks are performed before booking confirmation

---

## Summary of Penalties

| Violation | Penalty |
|-----------|---------|
| Book too late (< 1 hour) | Booking rejected |
| 1st late cancellation | Recorded (no immediate action) |
| 2nd late cancellation | Warning notification issued |
| 3+ late cancellations | Restrictions/Administrative review |
| Double booking attempt | Booking rejected (auto-prevented) |
| Past booking attempt | Booking rejected (auto-prevented) |
