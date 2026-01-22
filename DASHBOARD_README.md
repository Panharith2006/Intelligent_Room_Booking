# 📊 Room Booking Analytics Dashboard

## Overview
A comprehensive analytics dashboard built with Streamlit to visualize room booking data with real-time insights.

## Features

### 1. 🏆 Top Room Occupancy Rate (Bar Chart)
- Shows percentage of total bookings each room receives
- Formula: `Occupancy Rate (%) = (Number of Bookings per Room / Total Bookings) × 100%`
- Visual: Horizontal bar chart with color gradient
- Includes detailed statistics table

### 2. ⏰ Peak Usage Time Analysis
- **Hourly Distribution**: Line graph showing busiest hours
- **Day of Week Analysis**: Bar chart showing busiest days
- **Heatmap**: Day × Hour visualization for comprehensive view
- Automatically identifies and highlights peak hours and days

### 3. 📊 Room Utilization Rate (Line Chart)
- Shows percentage of rooms being used over time
- Formula: `Utilization Rate (%) = (Number of Booked Rooms / Total Rooms) × 100%`
- Three views: Daily, Weekly, Monthly
- Includes average and peak utilization metrics

## Installation

### 1. Install Required Packages

```bash
pip install streamlit pandas plotly django
```

Or install from requirements:

```bash
pip install -r requirements.txt
```

### 2. Verify Django Setup
Ensure your Django project is properly configured and the database is set up:

```bash
python manage.py migrate
```

## Running the Dashboard

### Option 1: Command Line

```bash
streamlit run dashboard_analytics.py
```

### Option 2: With Custom Port

```bash
streamlit run dashboard_analytics.py --server.port 8501
```

### Option 3: In Production

```bash
streamlit run dashboard_analytics.py --server.address 0.0.0.0 --server.port 8501
```

## Usage

1. **Select Time Range**: Use the sidebar to filter data
   - Today
   - This Week
   - This Month
   - This Year
   - All Time
   - Custom Range

2. **View Key Metrics**: Dashboard shows:
   - Total Bookings
   - Total Rooms
   - Room Utilization %
   - Active Users

3. **Analyze Visualizations**:
   - Scroll through each section
   - Hover over charts for detailed information
   - Expand tables for more data
   - Switch between Daily/Weekly/Monthly views

4. **Refresh Data**: Click the "🔄 Refresh Dashboard" button to reload latest data

## Dashboard Sections

### Key Metrics (Top)
- 4 metric cards showing current statistics
- Updates based on selected time range

### Room Occupancy Rate
- Bar chart (horizontal)
- Color-coded by occupancy percentage
- Expandable detailed table
- Shows booking counts and percentages

### Peak Usage Time
- **Left**: Hourly line graph with peak hour annotation
- **Right**: Day of week bar chart with busiest day
- **Bottom**: Heatmap showing day × hour booking density

### Room Utilization Rate
- Toggle between Daily/Weekly/Monthly views
- Line chart showing trends over time
- Metrics showing average and peak utilization

## Technical Details

### Data Sources
- **Database**: Django ORM (PostgreSQL/SQLite/MySQL)
- **Models**: `Booking`, `Room`, `User`
- **Caching**: 5-minute TTL for performance

### Technologies
- **Frontend**: Streamlit
- **Visualizations**: Plotly
- **Data Processing**: Pandas
- **Backend**: Django ORM

### Performance Optimization
- `@st.cache_data` decorator for database queries
- 5-minute cache TTL (300 seconds)
- Efficient pandas operations
- Selective field loading from Django ORM

## Customization

### Changing Cache Duration
Edit the `ttl` parameter in cache decorators:

```python
@st.cache_data(ttl=600)  # 10 minutes instead of 5
```

### Modifying Color Schemes
Update the `colorscale` in Plotly figures:

```python
colorscale='Viridis'  # Options: Viridis, Plasma, RdYlGn, Blues, etc.
```

### Adding New Metrics
Add new queries in the data fetching functions and create new visualizations.

## Troubleshooting

### Issue: "Module not found" Error
**Solution**: Ensure all dependencies are installed
```bash
pip install -r requirements.txt
```

### Issue: Database Connection Error
**Solution**: Check Django settings and database configuration
```bash
python manage.py check
```

### Issue: Dashboard Not Loading
**Solution**: Verify port is not in use
```bash
# Try a different port
streamlit run dashboard_analytics.py --server.port 8502
```

### Issue: No Data Showing
**Solution**: 
1. Check if bookings exist in database
2. Verify time range filter
3. Check Django database connection

## Browser Access

Once running, access the dashboard at:
- **Local**: http://localhost:8501
- **Network**: http://YOUR_IP:8501

## Deployment

### Deploy on Streamlit Cloud
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect repository
4. Deploy!

### Deploy on Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run with nohup
nohup streamlit run dashboard_analytics.py --server.port 8501 &
```

## Future Enhancements
- [ ] Export reports to PDF
- [ ] Email scheduled reports
- [ ] Real-time data updates
- [ ] User-specific analytics
- [ ] Booking predictions
- [ ] Room recommendations

## Support
For issues or questions, contact the development team or check the project documentation.

---
**Built with ❤️ using Streamlit and Django**
