"""
Room Booking Analytics Dashboard
Built with Streamlit for real-time analytics visualization
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.utils import timezone
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
django.setup()

from booking.models import Booking, Room
from django.contrib.auth import get_user_model

User = get_user_model()

# Page configuration
st.set_page_config(
    page_title="Room Booking Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .stMetric label {
        color: #31333F !important;
        font-weight: 600;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #0e1117 !important;
        font-size: 2rem;
        font-weight: 600;
    }
    .stMetric [data-testid="stMetricDelta"] {
        color: #31333F !important;
    }
    h1 {
        color: #667eea;
        font-weight: 700;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("📊 Room Booking Analytics Dashboard")
st.markdown("---")

# Sidebar filters
st.sidebar.header("🔍 Filters")
time_range = st.sidebar.selectbox(
    "Select Time Range",
    ["Today", "This Week", "This Month", "This Year", "All Time", "Custom Range"]
)

# Calculate date range
now = timezone.now()
if time_range == "Today":
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now
elif time_range == "This Week":
    start_date = now - timedelta(days=now.weekday())
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now
elif time_range == "This Month":
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = now
elif time_range == "This Year":
    start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = now
elif time_range == "Custom Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start Date", now - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", now)
    start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
else:  # All Time
    start_date = None
    end_date = None

# Fetch data
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_booking_data(start_date, end_date):
    """Fetch booking data from database"""
    if start_date and end_date:
        bookings = Booking.objects.filter(
            start_time__gte=start_date,
            start_time__lte=end_date
        ).select_related('room', 'user')
    else:
        bookings = Booking.objects.all().select_related('room', 'user')
    
    return list(bookings.values(
        'id', 'room__name', 'room__room_number', 'room__capacity',
        'start_time', 'end_time', 'status', 'user__email'
    ))

@st.cache_data(ttl=300)
def get_room_data():
    """Fetch all rooms"""
    rooms = Room.objects.all()
    return list(rooms.values('id', 'name', 'room_number', 'capacity', 'is_available'))

# Load data
with st.spinner("Loading data..."):
    bookings_data = get_booking_data(start_date, end_date)
    rooms_data = get_room_data()

df_bookings = pd.DataFrame(bookings_data)
df_rooms = pd.DataFrame(rooms_data)

# Convert datetime strings to datetime objects
if not df_bookings.empty:
    df_bookings['start_time'] = pd.to_datetime(df_bookings['start_time'])
    df_bookings['end_time'] = pd.to_datetime(df_bookings['end_time'])
    df_bookings['date'] = df_bookings['start_time'].dt.date
    df_bookings['hour'] = df_bookings['start_time'].dt.hour
    df_bookings['day_of_week'] = df_bookings['start_time'].dt.day_name()

# Key Metrics
st.header("📈 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

total_bookings = len(df_bookings) if not df_bookings.empty else 0
total_rooms = len(df_rooms)
active_rooms = df_rooms['is_available'].sum() if not df_rooms.empty else 0

with col1:
    st.metric(
        label="Total Bookings",
        value=f"{total_bookings:,}",
        delta=f"{time_range}"
    )

with col2:
    st.metric(
        label="Total Rooms",
        value=f"{total_rooms}",
        delta=f"{active_rooms} available"
    )

with col3:
    if not df_bookings.empty and total_rooms > 0:
        unique_booked_rooms = df_bookings['room__name'].nunique()
        utilization = (unique_booked_rooms / total_rooms) * 100
        st.metric(
            label="Room Utilization",
            value=f"{utilization:.1f}%",
            delta=f"{unique_booked_rooms}/{total_rooms} rooms"
        )
    else:
        st.metric(label="Room Utilization", value="0%")

with col4:
    if not df_bookings.empty:
        unique_users = df_bookings['user__email'].nunique()
        st.metric(
            label="Active Users",
            value=f"{unique_users:,}"
        )
    else:
        st.metric(label="Active Users", value="0")

st.markdown("---")

# ==========================================
# 1. TOP ROOM OCCUPANCY RATE - BAR CHART
# ==========================================
st.header("🏆 Top Room Occupancy Rate")
st.markdown("*Shows the percentage of total bookings each room receives*")

if not df_bookings.empty:
    # Calculate bookings per room
    room_bookings = df_bookings.groupby(['room__name', 'room__room_number']).size().reset_index(name='booking_count')
    room_bookings['room_label'] = room_bookings['room__name'] + ' (' + room_bookings['room__room_number'] + ')'
    
    # Calculate occupancy rate
    total_bookings_count = room_bookings['booking_count'].sum()
    room_bookings['occupancy_rate'] = (room_bookings['booking_count'] / total_bookings_count * 100).round(2)
    
    # Sort by occupancy rate
    room_bookings = room_bookings.sort_values('occupancy_rate', ascending=True)
    
    # Create bar chart
    fig_occupancy = go.Figure()
    
    fig_occupancy.add_trace(go.Bar(
        y=room_bookings['room_label'],
        x=room_bookings['occupancy_rate'],
        orientation='h',
        text=room_bookings.apply(lambda x: f"{x['occupancy_rate']:.1f}% ({x['booking_count']} bookings)", axis=1),
        textposition='auto',
        marker=dict(
            color=room_bookings['occupancy_rate'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Occupancy %")
        ),
        hovertemplate='<b>%{y}</b><br>Occupancy Rate: %{x:.1f}%<br><extra></extra>'
    ))
    
    fig_occupancy.update_layout(
        title=f"Room Occupancy Rate - {time_range}",
        xaxis_title="Occupancy Rate (%)",
        yaxis_title="Room",
        height=max(400, len(room_bookings) * 30),
        showlegend=False,
        hovermode='y unified'
    )
    
    st.plotly_chart(fig_occupancy, use_container_width=True)
    
    # Show detailed table
    with st.expander("📋 View Detailed Room Statistics"):
        display_df = room_bookings[['room_label', 'booking_count', 'occupancy_rate']].copy()
        display_df.columns = ['Room', 'Total Bookings', 'Occupancy Rate (%)']
        display_df = display_df.sort_values('Occupancy Rate (%)', ascending=False).reset_index(drop=True)
        st.dataframe(display_df, use_container_width=True)
else:
    st.info("No booking data available for the selected time range.")

st.markdown("---")

# ==========================================
# 2. PEAK USAGE TIME - LINE GRAPH & HEATMAP
# ==========================================
st.header("⏰ Peak Usage Time Analysis")
st.markdown("*Identifies the busiest hours of the day and days of the week*")

if not df_bookings.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Hourly Booking Distribution")
        # Hourly analysis
        hourly_bookings = df_bookings.groupby('hour').size().reset_index(name='booking_count')
        
        # Create line chart
        fig_hourly = go.Figure()
        
        fig_hourly.add_trace(go.Scatter(
            x=hourly_bookings['hour'],
            y=hourly_bookings['booking_count'],
            mode='lines+markers',
            name='Bookings',
            line=dict(color='#667eea', width=3),
            marker=dict(size=8, color='#764ba2'),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.2)',
            hovertemplate='<b>Hour: %{x}:00</b><br>Bookings: %{y}<extra></extra>'
        ))
        
        # Highlight peak hour
        peak_hour = hourly_bookings.loc[hourly_bookings['booking_count'].idxmax()]
        fig_hourly.add_annotation(
            x=peak_hour['hour'],
            y=peak_hour['booking_count'],
            text=f"Peak: {peak_hour['hour']}:00",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#ff6b6b",
            ax=0,
            ay=-40,
            bgcolor="#ff6b6b",
            font=dict(color="white", size=12)
        )
        
        fig_hourly.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Number of Bookings",
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_hourly, use_container_width=True)
        
        st.info(f"🔥 **Peak Hour:** {int(peak_hour['hour'])}:00 - {int(peak_hour['hour'])+1}:00 with **{int(peak_hour['booking_count'])}** bookings")
    
    with col2:
        st.subheader("Day of Week Distribution")
        # Day of week analysis
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_bookings = df_bookings.groupby('day_of_week').size().reset_index(name='booking_count')
        day_bookings['day_of_week'] = pd.Categorical(day_bookings['day_of_week'], categories=day_order, ordered=True)
        day_bookings = day_bookings.sort_values('day_of_week')
        
        fig_daily = go.Figure()
        
        fig_daily.add_trace(go.Bar(
            x=day_bookings['day_of_week'],
            y=day_bookings['booking_count'],
            marker=dict(
                color=day_bookings['booking_count'],
                colorscale='Plasma',
                showscale=False
            ),
            text=day_bookings['booking_count'],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Bookings: %{y}<extra></extra>'
        ))
        
        fig_daily.update_layout(
            xaxis_title="Day of Week",
            yaxis_title="Number of Bookings",
            height=400
        )
        
        st.plotly_chart(fig_daily, use_container_width=True)
        
        peak_day = day_bookings.loc[day_bookings['booking_count'].idxmax()]
        st.info(f"🔥 **Busiest Day:** {peak_day['day_of_week']} with **{int(peak_day['booking_count'])}** bookings")
    
    # Heatmap: Day of Week vs Hour
    st.subheader("📅 Booking Heatmap: Day × Hour")
    
    heatmap_data = df_bookings.groupby(['day_of_week', 'hour']).size().reset_index(name='booking_count')
    heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='booking_count').fillna(0)
    
    # Reorder days
    heatmap_pivot = heatmap_pivot.reindex(day_order)
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_pivot.values,
        x=heatmap_pivot.columns,
        y=heatmap_pivot.index,
        colorscale='RdYlGn',
        text=heatmap_pivot.values,
        texttemplate='%{text}',
        textfont={"size": 10},
        hovertemplate='<b>%{y}</b><br>Hour: %{x}:00<br>Bookings: %{z}<extra></extra>',
        colorbar=dict(title="Bookings")
    ))
    
    fig_heatmap.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week",
        height=400,
        xaxis=dict(tickmode='linear', tick0=0, dtick=1)
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
else:
    st.info("No booking data available for the selected time range.")

st.markdown("---")

# ==========================================
# 3. ROOM UTILIZATION RATE - LINE CHART
# ==========================================
st.header("📊 Room Utilization Rate Over Time")
st.markdown("*Shows the percentage of rooms being used over time*")

if not df_bookings.empty:
    view_type = st.radio(
        "Select View",
        ["Daily", "Weekly", "Monthly"],
        horizontal=True
    )
    
    if view_type == "Daily":
        # Daily utilization
        daily_util = df_bookings.groupby('date').agg({
            'room__name': 'nunique'  # Unique rooms booked per day
        }).reset_index()
        daily_util.columns = ['date', 'rooms_booked']
        daily_util['utilization_rate'] = (daily_util['rooms_booked'] / total_rooms * 100).round(2)
        
        fig_util = go.Figure()
        
        fig_util.add_trace(go.Scatter(
            x=daily_util['date'],
            y=daily_util['utilization_rate'],
            mode='lines+markers',
            name='Utilization Rate',
            line=dict(color='#10b981', width=3),
            marker=dict(size=8, color='#059669'),
            fill='tozeroy',
            fillcolor='rgba(16, 185, 129, 0.2)',
            hovertemplate='<b>%{x}</b><br>Utilization: %{y:.1f}%<br>Rooms Booked: ' + daily_util['rooms_booked'].astype(str) + f'/{total_rooms}<extra></extra>'
        ))
        
        fig_util.update_layout(
            title=f"Daily Room Utilization Rate",
            xaxis_title="Date",
            yaxis_title="Utilization Rate (%)",
            height=450,
            hovermode='x unified',
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig_util, use_container_width=True)
        
        avg_util = daily_util['utilization_rate'].mean()
        max_util = daily_util['utilization_rate'].max()
        max_util_date = daily_util.loc[daily_util['utilization_rate'].idxmax(), 'date']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Average Daily Utilization", f"{avg_util:.1f}%")
        with col2:
            st.metric("Peak Utilization", f"{max_util:.1f}%")
        with col3:
            st.metric("Peak Date", max_util_date.strftime('%Y-%m-%d'))
            
    elif view_type == "Weekly":
        # Weekly utilization
        df_bookings['week'] = df_bookings['start_time'].dt.to_period('W').astype(str)
        weekly_util = df_bookings.groupby('week').agg({
            'room__name': 'nunique'
        }).reset_index()
        weekly_util.columns = ['week', 'rooms_booked']
        weekly_util['utilization_rate'] = (weekly_util['rooms_booked'] / total_rooms * 100).round(2)
        
        fig_util = go.Figure()
        
        fig_util.add_trace(go.Bar(
            x=weekly_util['week'],
            y=weekly_util['utilization_rate'],
            marker=dict(
                color=weekly_util['utilization_rate'],
                colorscale='Greens',
                showscale=True,
                colorbar=dict(title="Utilization %")
            ),
            text=weekly_util['utilization_rate'].apply(lambda x: f"{x:.1f}%"),
            textposition='auto',
            hovertemplate='<b>Week: %{x}</b><br>Utilization: %{y:.1f}%<extra></extra>'
        ))
        
        fig_util.update_layout(
            title=f"Weekly Room Utilization Rate",
            xaxis_title="Week",
            yaxis_title="Utilization Rate (%)",
            height=450,
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig_util, use_container_width=True)
        
    else:  # Monthly
        # Monthly utilization
        df_bookings['month'] = df_bookings['start_time'].dt.to_period('M').astype(str)
        monthly_util = df_bookings.groupby('month').agg({
            'room__name': 'nunique'
        }).reset_index()
        monthly_util.columns = ['month', 'rooms_booked']
        monthly_util['utilization_rate'] = (monthly_util['rooms_booked'] / total_rooms * 100).round(2)
        
        fig_util = go.Figure()
        
        fig_util.add_trace(go.Scatter(
            x=monthly_util['month'],
            y=monthly_util['utilization_rate'],
            mode='lines+markers',
            name='Utilization Rate',
            line=dict(color='#8b5cf6', width=4),
            marker=dict(size=12, color='#7c3aed'),
            fill='tozeroy',
            fillcolor='rgba(139, 92, 246, 0.2)',
            hovertemplate='<b>%{x}</b><br>Utilization: %{y:.1f}%<extra></extra>'
        ))
        
        fig_util.update_layout(
            title=f"Monthly Room Utilization Rate",
            xaxis_title="Month",
            yaxis_title="Utilization Rate (%)",
            height=450,
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig_util, use_container_width=True)
        
else:
    st.info("No booking data available for the selected time range.")

st.markdown("---")

# Footer with refresh button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Room Booking Analytics Dashboard | Built with ❤️ using Streamlit</div>",
    unsafe_allow_html=True
)
