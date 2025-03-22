import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Set page configuration
st.set_page_config(
    page_title="Monitoraggio Stazioni Meteo",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 36px;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 24px;
        font-weight: bold;
        color: #0D47A1;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .card {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8f9fa;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .metric-container {
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
    }
    .metric-card {
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 14px;
        color: #616161;
    }
    .footer {
        text-align: center;
        margin-top: 40px;
        color: #9E9E9E;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    """Load data from the CSV file"""
    file_path = "dati_meteo_stazioni.csv"
    
    if not os.path.exists(file_path):
        st.error(f"File {file_path} non trovato. Assicurati che lo script di raccolta dati sia in esecuzione.")
        return None
    
    try:
        df = pd.read_csv(file_path)
        # Convert Data_Ora to datetime
        df['Data_Ora'] = pd.to_datetime(df['Data_Ora'], format='%d/%m/%Y %H:%M')
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati: {e}")
        return None

def create_time_filter(df):
    """Create time filter widgets"""
    st.sidebar.markdown("### Filtro Temporale")
    
    # Get min and max dates from data
    min_date = df['Data_Ora'].min().date()
    max_date = df['Data_Ora'].max().date()
    
    # Date range selector
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Data Inizio", 
                                  value=max_date - timedelta(days=1),
                                  min_value=min_date,
                                  max_value=max_date)
    with col2:
        end_date = st.date_input("Data Fine", 
                               value=max_date,
                               min_value=min_date,
                               max_value=max_date)
    
    # Convert back to datetime for filtering
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Filter data based on selected date range
    filtered_df = df[(df['Data_Ora'] >= start_datetime) & (df['Data_Ora'] <= end_datetime)]
    
    return filtered_df

def identify_data_columns(df):
    """Identify different types of data columns"""
    columns = df.columns.tolist()
    
    # Remove 'Data_Ora' from columns
    if 'Data_Ora' in columns:
        columns.remove('Data_Ora')
    
    # Group columns by type
    temperature_cols = [col for col in columns if 'Temperatura' in col or 'temp' in col.lower()]
    precipitation_cols = [col for col in columns if 'Precipitazione' in col or 'pioggia' in col.lower() or 'mm' in col.lower()]
    wind_cols = [col for col in columns if 'Vento' in col or 'vento' in col.lower()]
    humidity_cols = [col for col in columns if 'Umidità' in col or 'umid' in col.lower()]
    pressure_cols = [col for col in columns if 'Pressione' in col or 'press' in col.lower()]
    
    # Other columns
    other_cols = [col for col in columns if col not in temperature_cols + precipitation_cols + 
                 wind_cols + humidity_cols + pressure_cols]
    
    return {
        'temperature': temperature_cols,
        'precipitation': precipitation_cols,
        'wind': wind_cols,
        'humidity': humidity_cols,
        'pressure': pressure_cols,
        'other': other_cols
    }

def plot_time_series(df, columns, title, y_axis_title, color_sequence=None):
    """Create a time series plot for selected columns"""
    if not columns:
        return None
    
    fig = go.Figure()
    
    for i, col in enumerate(columns):
        color = color_sequence[i % len(color_sequence)] if color_sequence else None
        
        # Replace 'N/A' with None for plotting
        valid_data = df.copy()
        valid_data.loc[valid_data[col] == 'N/A', col] = None
        valid_data[col] = pd.to_numeric(valid_data[col], errors='coerce')
        
        fig.add_trace(
            go.Scatter(
                x=valid_data['Data_Ora'],
                y=valid_data[col],
                name=col,
                line=dict(color=color),
                mode='lines+markers'
            )
        )
    
    fig.update_layout(
        title=title,
        xaxis_title='Data e Ora',
        yaxis_title=y_axis_title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(l=10, r=10, t=50, b=30),
        hovermode="x unified"
    )
    
    return fig

def display_latest_metrics(df, data_cols):
    """Display the latest metrics in cards"""
    if df.empty:
        return
    
    latest_data = df.iloc[-1].to_dict()
    
    # Get the latest timestamp
    latest_time = latest_data['Data_Ora']
    st.markdown(f"### Ultimo aggiornamento: {latest_time.strftime('%d/%m/%Y %H:%M')}")
    
    # Create metric cards for different data types
    categories = {
        'Temperatura': data_cols['temperature'],
        'Precipitazioni': data_cols['precipitation'],
        'Vento': data_cols['wind'],
        'Umidità': data_cols['humidity'],
        'Pressione': data_cols['pressure']
    }
    
    for category, cols in categories.items():
        if cols:
            st.markdown(f"#### {category}")
            cols_per_row = 3
            for i in range(0, len(cols), cols_per_row):
                curr_cols = cols[i:i+cols_per_row]
                cols_for_ui = st.columns(len(curr_cols))
                
                for j, col in enumerate(curr_cols):
                    value = latest_data.get(col)
                    if value == 'N/A':
                        value = "N/A"
                    elif isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
                        try:
                            value = float(value)
                            value = f"{value:.1f}"
                        except:
                            pass
                    
                    # Extract unit from column name if present
                    unit = ""
                    if "(" in col and ")" in col:
                        unit = col.split("(")[1].split(")")[0]
                    
                    # Pretty display name
                    display_name = col.split(" (")[0] if " (" in col else col
                    
                    with cols_for_ui[j]:
                        st.markdown(
                            f"""
                            <div class="metric-card">
                                <div class="metric-value">{value} {unit}</div>
                                <div class="metric-label">{display_name}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

def create_dashboard():
    """Create the Streamlit dashboard"""
    # Title
    st.markdown('<div class="main-header">Dashboard Monitoraggio Stazioni Meteo</div>', unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Sidebar
    st.sidebar.markdown("## Opzioni Dashboard")
    
    # Auto refresh option
    refresh_interval = st.sidebar.selectbox(
        "Aggiornamento automatico",
        [None, 1, 5, 15, 30, 60],
        format_func=lambda x: "Disattivato" if x is None else f"Ogni {x} minuti"
    )
    
    if refresh_interval:
        st.sidebar.markdown(f"La dashboard si aggiornerà ogni {refresh_interval} minuti.")
        st.experimental_memo.clear()
        
    # Time filter
    filtered_df = create_time_filter(df)
    
    # Identify data columns
    data_cols = identify_data_columns(filtered_df)
    
    # Overview section - Latest metrics
    st.markdown('<div class="sub-header">Panoramica Attuale</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    display_latest_metrics(filtered_df, data_cols)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Create charts section
    st.markdown('<div class="sub-header">Grafici Temporali</div>', unsafe_allow_html=True)
    
    # Define color sequences for different chart types
    color_sequences = {
        'temperature': px.colors.sequential.Reds,
        'precipitation': px.colors.sequential.Blues,
        'wind': px.colors.sequential.Greens,
        'humidity': px.colors.sequential.Purples,
        'pressure': px.colors.sequential.Oranges,
        'other': px.colors.qualitative.Plotly
    }
    
    # Plot temperature data
    if data_cols['temperature']:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        temp_fig = plot_time_series(
            filtered_df, 
            data_cols['temperature'], 
            'Andamento della Temperatura', 
            'Temperatura (°C)',
            color_sequences['temperature']
        )
        st.plotly_chart(temp_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Plot precipitation data
    if data_cols['precipitation']:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        precip_fig = plot_time_series(
            filtered_df, 
            data_cols['precipitation'], 
            'Andamento delle Precipitazioni', 
            'Precipitazioni (mm)',
            color_sequences['precipitation']
        )
        st.plotly_chart(precip_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Plot other data types
    other_data_types = [
        ('wind', 'Andamento del Vento', 'Velocità del Vento (km/h)'),
        ('humidity', 'Andamento dell\'Umidità', 'Umidità (%)'),
        ('pressure', 'Andamento della Pressione Atmosferica', 'Pressione (hPa)'),
    ]
    
    for data_type, title, y_axis in other_data_types:
        if data_cols[data_type]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fig = plot_time_series(
                filtered_df, 
                data_cols[data_type], 
                title, 
                y_axis,
                color_sequences[data_type]
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Plot other columns if any
    if data_cols['other']:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Altri Dati")
        
        # Allow selection of columns to display
        selected_cols = st.multiselect(
            "Seleziona parametri da visualizzare",
            data_cols['other'],
            default=data_cols['other'][:min(3, len(data_cols['other']))]
        )
        
        if selected_cols:
            other_fig = plot_time_series(
                filtered_df, 
                selected_cols, 
                'Altri Parametri', 
                'Valore',
                color_sequences['other']
            )
            st.plotly_chart(other_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Add a data table section
    with st.expander("Visualizza Dati Grezzi"):
        st.dataframe(
            filtered_df.sort_values('Data_Ora', ascending=False),
            use_container_width=True
        )
        
        # Add download button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Scarica CSV",
            csv,
            "dati_meteo_filtrati.csv",
            "text/csv",
            key='download-csv'
        )
    
    # Footer
    st.markdown(
        '<div class="footer">Dashboard creata per il monitoraggio delle stazioni meteo. '
        'Ultimo aggiornamento: ' + datetime.now().strftime('%d/%m/%Y %H:%M') + '</div>',
        unsafe_allow_html=True
    )
    
    # Set up auto-refresh if enabled
    if refresh_interval:
        st.experimental_rerun()

if __name__ == "__main__":
    create_dashboard()
