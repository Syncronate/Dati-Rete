import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import glob
from datetime import datetime, timedelta
import pytz
import time
import numpy as np
import folium
from streamlit_folium import folium_static

# Page configuration
st.set_page_config(
    page_title="Weather Monitoring Dashboard",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #0D47A1;
        margin-top: 1rem;
    }
    .data-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 0.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .metric-label {
        font-weight: bold;
        color: #555;
    }
    .success-value {
        color: #4CAF50;
        font-weight: bold;
    }
    .warning-value {
        color: #FF9800;
        font-weight: bold;
    }
    .danger-value {
        color: #F44336;
        font-weight: bold;
    }
    .info-text {
        color: #555;
        font-size: 0.85rem;
    }
    .last-updated {
        font-style: italic;
        font-size: 0.8rem;
        color: #777;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_latest_data():
    """Load the most recent weather data CSV file"""
    try:
        # Get list of CSV files with the specific naming pattern
        csv_files = glob.glob("dati_meteo_stazioni_selezionate_*.csv")

        if not csv_files:
            return None

        # Find the most recent file by sorting
        latest_file = max(csv_files)

        # Read the CSV file
        df = pd.read_csv(latest_file)

        # Convert timestamp to datetime
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])

        # Convert 'Valore' column to numeric, coercing errors to NaN and then drop NaN rows
        df['Valore'] = pd.to_numeric(df['Valore'], errors='coerce')
        df.dropna(subset=['Valore'], inplace=True)


        # Create a more readable sensor description by combining type and description
        df['Sensor'] = df['Descrizione Sensore'] + " (" + df['Sensore Tipo'].astype(str) + ")"

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def get_sensor_color(sensor_type):
    """Return consistent color for specific sensor types"""
    color_map = {
        0: "#1E88E5",  # Rain
        1: "#F44336",  # Temperature
        5: "#4CAF50",  # Humidity
        6: "#FF9800",  # Wind
        9: "#9C27B0",  # River level
        10: "#FFEB3B", # Pressure
        100: "#795548" # Other
    }
    return color_map.get(sensor_type, "#607D8B")

def get_station_coordinates():
    """Return coordinates for the weather stations (approximated for this example)"""
    # These are approximated coordinates - replace with actual coordinates
    return {
        "Misa": (43.6166, 13.1663),
        "Pianello di Ostra": (43.6066, 13.1498),
        "Nevola": (43.6497, 13.0716),
        "Barbara": (43.6216, 13.0588),
        "Serra dei Conti": (43.5498, 13.0475),
        "Arcevia": (43.5002, 12.9431)
    }

def get_sensor_description(sensor_type):
    """Return descriptive name for sensor type"""
    descriptions = {
        0: "Rainfall",
        1: "Temperature",
        5: "Humidity",
        6: "Wind",
        9: "River Level",
        10: "Pressure",
        100: "Other"
    }
    return descriptions.get(sensor_type, f"Sensor Type {sensor_type}")

def get_sensor_unit(df, sensor_type):
    """Get unit of measurement for a specific sensor type"""
    sensor_data = df[df['Sensore Tipo'] == sensor_type]
    if len(sensor_data) > 0:
        unit = sensor_data['Unità di Misura'].iloc[0]
        return unit
    return ""

def get_threshold_color(value, sensor_type):
    """Return color based on threshold for specific sensor types"""
    if sensor_type == 0:  # Rainfall
        if value > 10:
            return "danger-value"
        elif value > 5:
            return "warning-value"
        return "success-value"
    elif sensor_type == 1:  # Temperature
        if value > 30 or value < 0:
            return "danger-value"
        elif value > 25 or value < 5:
            return "warning-value"
        return "success-value"
    elif sensor_type == 9:  # River level
        if value > 3:
            return "danger-value"
        elif value > 2:
            return "warning-value"
        return "success-value"
    else:
        return "success-value"

# Sidebar section
st.sidebar.markdown("<div class='sub-header'>Dashboard Controls</div>", unsafe_allow_html=True)

# Load data
df = load_latest_data()

if df is not None:
    # Get unique stations and sensor types for filtering
    all_stations = sorted(df['Stazione'].unique())
    all_sensor_types = sorted(df['Sensore Tipo'].unique())

    # Sidebar filters
    selected_stations = st.sidebar.multiselect(
        "Select Stations",
        all_stations,
        default=all_stations
    )

    selected_sensor_types = st.sidebar.multiselect(
        "Select Sensor Types",
        all_sensor_types,
        default=all_sensor_types,
        format_func=get_sensor_description
    )

    # Time range selector
    min_date = df['Timestamp'].min().date()
    max_date = df['Timestamp'].max().date()

    date_range = st.sidebar.slider(
        "Select Date Range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date)
    )

    # Convert dates to datetime for filtering
    start_date = datetime.combine(date_range[0], datetime.min.time())
    end_date = datetime.combine(date_range[1], datetime.max.time())

    # Filter data
    filtered_df = df[
        (df['Stazione'].isin(selected_stations)) &
        (df['Sensore Tipo'].isin(selected_sensor_types)) &
        (df['Timestamp'] >= start_date) &
        (df['Timestamp'] <= end_date)
    ]

    # Refresh rate
    refresh_interval = st.sidebar.slider(
        "Auto-refresh interval (seconds)",
        min_value=15,
        max_value=300,
        value=60,
        step=15
    )

    # Display options
    display_mode = st.sidebar.radio(
        "Display Mode",
        ["Combined View", "Station View", "Sensor View"]
    )

    # Add auto-refresh checkbox
    auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh", value=True)

    # About section
    st.sidebar.markdown("---")
    st.sidebar.markdown("<div class='sub-header'>About</div>", unsafe_allow_html=True)
    st.sidebar.info(
        """
        This dashboard visualizes weather data from multiple stations in the Marche region.
        Data is collected every 5 minutes and includes rainfall, temperature, humidity, wind,
        and river levels.
        """
    )

    # Main content
    st.markdown("<div class='main-header'>Weather Monitoring Dashboard</div>", unsafe_allow_html=True)

    # Display last updated time
    last_updated = df['Timestamp'].max()
    st.markdown(
        f"<div class='last-updated'>Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}</div>",
        unsafe_allow_html=True
    )

    # Current conditions section
    st.markdown("<div class='sub-header'>Current Conditions</div>", unsafe_allow_html=True)

    if display_mode == "Combined View":
        # Display current conditions across all stations
        latest_data = filtered_df.sort_values('Timestamp').groupby(['Stazione', 'Sensore Tipo']).last().reset_index()

        current_metrics = st.columns(len(selected_stations))

        for i, station in enumerate(selected_stations):
            if station in latest_data['Stazione'].values:
                station_data = latest_data[latest_data['Stazione'] == station]

                with current_metrics[i]:
                    st.markdown(f"<div class='metric-container'><h3>{station}</h3>", unsafe_allow_html=True)

                    for sensor_type in selected_sensor_types:
                        sensor_rows = station_data[station_data['Sensore Tipo'] == sensor_type]

                        if not sensor_rows.empty:
                            sensor_row = sensor_rows.iloc[0]
                            value = sensor_row['Valore']
                            unit = sensor_row['Unità di Misura']
                            description = sensor_row['Descrizione Sensore']

                            color_class = get_threshold_color(value, sensor_type)

                            st.markdown(
                                f"""
                                <div>
                                    <span class='metric-label'>{description}:</span>
                                    <span class='{color_class}'>{value} {unit}</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    st.markdown("</div>", unsafe_allow_html=True)

    # Map section
    st.markdown("<div class='sub-header'>Station Locations</div>", unsafe_allow_html=True)

    station_coords = get_station_coordinates()

    # Create a base map
    m = folium.Map(location=[43.55, 13.05], zoom_start=11)

    # Add markers for each station
    for station in selected_stations:
        if station in station_coords:
            lat, lon = station_coords[station]

            # Get latest data for this station to display in popup
            station_data = filtered_df[filtered_df['Stazione'] == station].sort_values('Timestamp').groupby('Sensore Tipo').last()

            popup_html = f"<b>{station}</b><br>"

            for _, row in station_data.iterrows():
                popup_html += f"{row['Descrizione Sensore']}: {row['Valore']} {row['Unità di Misura']}<br>"

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=station,
                icon=folium.Icon(color="blue", icon="cloud")
            ).add_to(m)

    # Display the map
    folium_static(m)

    # Trend charts section
    st.markdown("<div class='sub-header'>Weather Trends</div>", unsafe_allow_html=True)

    chart_tabs = st.tabs([get_sensor_description(sensor_type) for sensor_type in selected_sensor_types])

    for i, sensor_type in enumerate(selected_sensor_types):
        with chart_tabs[i]:
            sensor_df = filtered_df[filtered_df['Sensore Tipo'] == sensor_type]

            if not sensor_df.empty:
                unit = get_sensor_unit(sensor_df, sensor_type)

                # Line chart for this sensor type across all selected stations
                fig = px.line(
                    sensor_df,
                    x='Timestamp',
                    y='Valore',
                    color='Stazione',
                    title=f"{get_sensor_description(sensor_type)} over time",
                    labels={'Valore': f'Value ({unit})', 'Timestamp': 'Time'}
                )

                # Improve chart appearance
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title=f"Value ({unit})",
                    legend_title="Station",
                    height=500,
                    hovermode="x unified"
                )

                st.plotly_chart(fig, use_container_width=True)

                # Statistics for this sensor type
                stats_cols = st.columns(4)

                # Group by station and calculate statistics
                stats = sensor_df.groupby('Stazione')['Valore'].agg(['min', 'max', 'mean', 'std']).reset_index()
                stats['mean'] = stats['mean'].round(2)
                stats['std'] = stats['std'].round(2)

                with stats_cols[0]:
                    st.metric("Average", f"{stats['mean'].mean():.2f} {unit}")

                with stats_cols[1]:
                    st.metric("Min", f"{stats['min'].min():.2f} {unit}")

                with stats_cols[2]:
                    st.metric("Max", f"{stats['max'].max():.2f} {unit}")

                with stats_cols[3]:
                    # Find station with highest value
                    max_idx = stats['max'].idxmax()
                    max_station = stats.loc[max_idx, 'Stazione']
                    st.metric("Peak Station", max_station)

                # Table with statistics by station
                st.dataframe(
                    stats.rename(columns={
                        'min': 'Minimum',
                        'max': 'Maximum',
                        'mean': 'Average',
                        'std': 'Std Dev'
                    })
                )
            else:
                st.warning(f"No data available for {get_sensor_description(sensor_type)}")

    # Station-specific analysis (if selected)
    if display_mode == "Station View":
        st.markdown("<div class='sub-header'>Station Analysis</div>", unsafe_allow_html=True)

        station_tabs = st.tabs(selected_stations)

        for i, station in enumerate(selected_stations):
            with station_tabs[i]:
                station_df = filtered_df[filtered_df['Stazione'] == station]

                if not station_df.empty:
                    # Create a grid of small metrics for this station
                    metrics = {}

                    for sensor_type in selected_sensor_types:
                        sensor_data = station_df[station_df['Sensore Tipo'] == sensor_type]

                        if not sensor_data.empty:
                            latest = sensor_data.sort_values('Timestamp').iloc[-1]
                            metrics[sensor_type] = {
                                'value': latest['Valore'],
                                'unit': latest['Unità di Misura'],
                                'description': latest['Descrizione Sensore']
                            }

                    # Display metrics in columns
                    metric_cols = st.columns(min(3, len(metrics)))

                    for i, (sensor_type, data) in enumerate(metrics.items()):
                        col_idx = i % 3

                        with metric_cols[col_idx]:
                            st.metric(
                                data['description'],
                                f"{data['value']} {data['unit']}"
                            )

                    # Time series for all sensors for this station
                    pivot_df = station_df.pivot_table(
                        index='Timestamp',
                        columns='Descrizione Sensore',
                        values='Valore'
                    )

                    # Create composite chart
                    fig = go.Figure()

                    for sensor_type in selected_sensor_types:
                        sensor_data = station_df[station_df['Sensore Tipo'] == sensor_type]

                        if not sensor_data.empty:
                            description = sensor_data['Descrizione Sensore'].iloc[0]

                            fig.add_trace(
                                go.Scatter(
                                    x=sensor_data['Timestamp'],
                                    y=sensor_data['Valore'],
                                    mode='lines',
                                    name=description,
                                    line=dict(color=get_sensor_color(sensor_type))
                                )
                            )

                    fig.update_layout(
                        title=f"All Measurements for {station}",
                        xaxis_title="Time",
                        height=500,
                        hovermode="x unified"
                    )

                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"No data available for {station}")

    # Sensor-specific analysis (if selected)
    if display_mode == "Sensor View":
        st.markdown("<div class='sub-header'>Sensor Analysis</div>", unsafe_allow_html=True)

        for sensor_type in selected_sensor_types:
            st.markdown(f"<div class='sub-header'>{get_sensor_description(sensor_type)}</div>", unsafe_allow_html=True)

            sensor_df = filtered_df[filtered_df['Sensore Tipo'] == sensor_type]

            if not sensor_df.empty:
                # Latest values across stations
                latest_vals = sensor_df.sort_values('Timestamp').groupby('Stazione').last().reset_index()

                unit = latest_vals['Unità di Misura'].iloc[0]

                # Bar chart of current values
                fig = px.bar(
                    latest_vals,
                    x='Stazione',
                    y='Valore',
                    title=f"Current {get_sensor_description(sensor_type)} Values",
                    labels={'Valore': f'Value ({unit})', 'Stazione': 'Station'},
                    color='Valore',
                    color_continuous_scale=px.colors.sequential.Blues
                )

                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

                # Heatmap of values over time if we have enough data
                if len(sensor_df) > 10:
                    # Create pivot table for heatmap (Station × Time)
                    heatmap_df = sensor_df.copy()
                    # Round timestamps to nearest hour for better visualization
                    heatmap_df['hour'] = heatmap_df['Timestamp'].dt.floor('H')

                    pivot = heatmap_df.pivot_table(
                        index='Stazione',
                        columns='hour',
                        values='Valore',
                        aggfunc='mean'
                    )

                    fig = px.imshow(
                        pivot,
                        title=f"{get_sensor_description(sensor_type)} Heatmap",
                        labels=dict(x="Time", y="Station", color=f"Value ({unit})"),
                        color_continuous_scale="Blues"
                    )

                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No data available for {get_sensor_description(sensor_type)}")

    # Setup auto-refresh mechanism
    if auto_refresh:
        time_placeholder = st.empty()
        counter = refresh_interval

        # Only show the countdown if we're on the app page (not being rendered statically)
        if not st.session_state.get('rendering_docs', False):
            time_placeholder.markdown(f"Auto-refreshing in {counter} seconds...")

            # Schedule rerun
            time.sleep(1)
            counter -= 1

            if counter <= 0:
                st.experimental_rerun()
else:
    st.error("No data files found. Please make sure the data extraction script has generated at least one CSV file.")

    if st.button("Retry"):
        st.experimental_rerun()
