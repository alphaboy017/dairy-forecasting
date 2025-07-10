import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
import lightgbm as lgb
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Dairy Supply & Demand Forecasting",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .forecast-section {
        background-color: #ffffff;
        padding: 2rem;
        border-radius: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Remove MongoDB imports
# import joblib
# from pymongo import MongoClient
# import io

# Move this to the top-level (main or before load_data is called)
# Remove Data Window selection from sidebar
# st.sidebar.markdown('### Data Window')
# time_options = {...}
# selected_window = st.sidebar.radio(...)

def load_data():
    """Load and preprocess the dairy dataset"""
    try:
        df = pd.read_csv('Dairy_Supply_Demand_2014_to_2024.csv')
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df = df.sort_values('Date')
        # No filtering by data window, use all data
        if df.empty:
            st.error('No data available in the dataset.')
            return None
        
        # Add derived features
        df['DayOfWeek'] = df['Date'].dt.dayofweek
        df['Month'] = df['Date'].dt.month
        df['Quarter'] = df['Date'].dt.quarter
        df['Year'] = df['Date'].dt.year
        
        # Calculate capacity utilization
        df['Total_Demand'] = (df['Milk_500ml_Demand'] + df['Milk_1L_Demand'] + 
                             df['Butter_Demand'] + df['Cheese_Demand'] + df['Yogurt_Demand'])
        df['Total_Inventory'] = (df['Milk_500ml_Inventory'] + df['Milk_1L_Inventory'] + 
                                df['Butter_Inventory'] + df['Cheese_Inventory'] + df['Yogurt_Inventory'])
        
        # Calculate efficiency metrics
        df['Demand_Supply_Ratio'] = df['Total_Demand'] / df['Milk_Supply_Liters']
        df['Inventory_Turnover'] = df['Total_Demand'] / df['Total_Inventory']
        df['Capacity_Utilization'] = (df['Total_Demand'] / (df['Total_Demand'] + df['Total_Inventory'])) * 100
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

def create_dashboard(df):
    """Create the main dashboard with key metrics"""
    st.markdown('<h1 class="main-header">🥛 Dairy Supply & Demand Forecasting</h1>', unsafe_allow_html=True)
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Records",
            value=f"{len(df):,}",
            delta=f"From {df['Date'].min().strftime('%Y-%m-%d')} to {df['Date'].max().strftime('%Y-%m-%d')}"
        )
    
    with col2:
        avg_supply = df['Milk_Supply_Liters'].mean()
        st.metric(
            label="Avg Daily Supply (L)",
            value=f"{avg_supply:,.0f}",
            delta=f"{df['Milk_Supply_Liters'].std():,.0f} std"
        )
    
    with col3:
        avg_demand = df['Total_Demand'].mean()
        st.metric(
            label="Avg Daily Demand",
            value=f"{avg_demand:,.0f}",
            delta=f"{df['Total_Demand'].std():,.0f} std"
        )
    
    with col4:
        avg_utilization = df['Capacity_Utilization'].mean()
        st.metric(
            label="Avg Capacity Utilization",
            value=f"{avg_utilization:.1f}%",
            delta=f"{df['Capacity_Utilization'].std():.1f}% std"
        )

def create_visualizations(df):
    """Create comprehensive visualizations"""
    st.markdown("## 📊 Data Analysis & Insights")
    
    # Time series analysis
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Time Series", "📊 Product Analysis", "🔍 Capacity Analysis", "📋 Statistical Summary"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Supply and demand over time
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Milk_Supply_Liters'], 
                                   name='Milk Supply', line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Total_Demand'], 
                                   name='Total Demand', line=dict(color='red')))
            fig.update_layout(title='Supply vs Demand Over Time', 
                            xaxis_title='Date', yaxis_title='Volume (L)',
                            height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Downtime analysis
            fig = px.line(df, x='Date', y='Downtime_Hours', 
                         title='Equipment Downtime Over Time')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Product demand comparison
            products = ['Milk_500ml_Demand', 'Milk_1L_Demand', 'Butter_Demand', 
                       'Cheese_Demand', 'Yogurt_Demand']
            product_data = df[products].mean().reset_index()
            product_data.columns = ['Product', 'Avg_Demand']
            
            fig = px.bar(product_data, x='Product', y='Avg_Demand',
                        title='Average Daily Demand by Product')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Inventory levels
            inventory_cols = ['Milk_500ml_Inventory', 'Milk_1L_Inventory', 
                             'Butter_Inventory', 'Cheese_Inventory', 'Yogurt_Inventory']
            inventory_data = df[inventory_cols].mean().reset_index()
            inventory_data.columns = ['Product', 'Avg_Inventory']
            
            fig = px.bar(inventory_data, x='Product', y='Avg_Inventory',
                        title='Average Inventory Levels by Product')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Capacity utilization over time
            fig = px.line(df, x='Date', y='Capacity_Utilization',
                         title='Capacity Utilization Over Time')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Demand-supply ratio
            fig = px.line(df, x='Date', y='Demand_Supply_Ratio',
                         title='Demand-Supply Ratio Over Time')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        # Statistical summary
        st.subheader("Statistical Summary")
        
        # Select columns for summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        summary_cols = st.multiselect("Select columns for summary:", numeric_cols, 
                                     default=['Milk_Supply_Liters', 'Total_Demand', 'Capacity_Utilization'])
        
        if summary_cols:
            st.table(df[summary_cols].describe())

def prepare_features(df, target_col, forecast_days=30):
    """Prepare features for forecasting"""
    # Create lag features
    for lag in [1, 7, 14, 30]:
        df[f'{target_col}_lag_{lag}'] = df[target_col].shift(lag)
    
    # Create rolling features
    for window in [7, 14, 30]:
        df[f'{target_col}_rolling_mean_{window}'] = df[target_col].rolling(window=window).mean()
        df[f'{target_col}_rolling_std_{window}'] = df[target_col].rolling(window=window).std()
    
    # Create seasonal features
    df['sin_day'] = np.sin(2 * np.pi * df['DayOfWeek'] / 7)
    df['cos_day'] = np.cos(2 * np.pi * df['DayOfWeek'] / 7)
    df['sin_month'] = np.sin(2 * np.pi * df['Month'] / 12)
    df['cos_month'] = np.cos(2 * np.pi * df['Month'] / 12)
    
    # Drop NaN values
    df = df.dropna()
    
    # Prepare features and target
    feature_cols = [col for col in df.columns if col not in ['Date', target_col]]
    X = df[feature_cols]
    y = df[target_col]
    
    return X, y, df

def train_models(X, y):
    """Train multiple forecasting models"""
    models = {
        'Random Forest': RandomForestRegressor(n_estimators=20, n_jobs=-1, random_state=42),
        'Gradient Boosting': GradientBoostingRegressor(n_estimators=20, random_state=42),
        'XGBoost': xgb.XGBRegressor(n_estimators=20, n_jobs=-1, random_state=42),
        'LightGBM': lgb.LGBMRegressor(n_estimators=20, n_jobs=-1, random_state=42),
        'Linear Regression': LinearRegression()
    }
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = {}
    
    for name, model in models.items():
        if name == 'Linear Regression':
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
        
        # Calculate metrics
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_test, y_pred)
        
        results[name] = {
            'model': model,
            'scaler': scaler if name == 'Linear Regression' else None,
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'r2': r2,
            'y_pred': y_pred,
            'y_test': y_test
        }
    
    return results, X_train, X_test, y_train, y_test

def create_forecasting_section(df):
    """Create the forecasting section"""
    st.markdown("## 🔮 Demand Forecasting")
    
    # Target selection
    target_options = {
        'Total Demand': 'Total_Demand',
        'Milk Supply': 'Milk_Supply_Liters',
        'Milk 500ml Demand': 'Milk_500ml_Demand',
        'Milk 1L Demand': 'Milk_1L_Demand',
        'Butter Demand': 'Butter_Demand',
        'Cheese Demand': 'Cheese_Demand',
        'Yogurt Demand': 'Yogurt_Demand'
    }
    
    selected_target = st.selectbox("Select target variable for forecasting:", list(target_options.keys()))
    target_col = target_options[selected_target]
    # Robust bug checks for all target variables
    if target_col not in df.columns:
        st.error(f"Selected target column '{target_col}' not found in data.")
        return
    if df[target_col].isnull().all():
        st.error(f"All values for '{selected_target}' are missing. Cannot forecast.")
        return
    if df[target_col].nunique() <= 1:
        st.error(f"Selected target '{selected_target}' has constant or zero values. Cannot forecast.")
        return
    # Prepare features
    X, y, df_processed = prepare_features(df.copy(), target_col)
    if len(X) < 30:
        st.error(f"Not enough data after feature engineering for '{selected_target}'. Try a different variable, a longer data window, or check your data.")
        return
    
    # Only retrain if user clicks button or target changes
    retrain = False
    if 'last_trained' not in st.session_state:
        st.session_state['last_trained'] = {}
    if st.button("🚀 Train Forecasting Models"):
        retrain = True
    if target_col not in st.session_state['last_trained']:
        retrain = True
    if retrain:
        with st.spinner("Training models..."):
            results, X_train, X_test, y_train, y_test = train_models(X, y)
        
        # Display results
        st.markdown("### 📊 Model Performance Comparison")
        table_placeholder = st.empty()
        import math
        performance_data = []
        for name, result in results.items():
            def safe_metric(val):
                if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                    return None
                return round(val, 2)
            row = {
                'Model': name,
                'RMSE': safe_metric(result['rmse']),
                'R²': safe_metric(result['r2'])
            }
            # Only add if both metrics are valid
            if row['RMSE'] is not None and row['R²'] is not None:
                performance_data.append(row)
        if performance_data:
            performance_df = pd.DataFrame(performance_data)
            # Highlight the best model (lowest RMSE)
            best_idx = performance_df['RMSE'].idxmin()
            best_rmse = performance_df.loc[best_idx, 'RMSE']
            # Add 'Best' badge
            performance_df['Best'] = ['✅ Best' if i == best_idx else '' for i in range(len(performance_df))]
            # Show relative performance improvement
            sorted_rmse = performance_df['RMSE'].sort_values().values
            if len(sorted_rmse) > 1:
                improvement = 100 * (sorted_rmse[1] - sorted_rmse[0]) / sorted_rmse[1]
                rel_perf_msg = f"The best model is {improvement:.1f}% better (lower RMSE) than the next best."
            else:
                rel_perf_msg = ""
            # Warn about suspicious results
            suspicious = performance_df[(performance_df['RMSE'] == 0) | (performance_df['R²'] == 1)]
            if not suspicious.empty:
                st.warning("Some models have RMSE=0 or R²=1. This may indicate overfitting or a bug.")
            # Show table with best row highlighted
            def highlight_best_row(row):
                return ['background-color: #d4edda' if row.name == best_idx else '' for _ in row]
            st.session_state['performance_df'] = performance_df
            table_placeholder.table(performance_df)
            # Model selection dropdown
            model_names = performance_df['Model'].tolist()
            default_model = performance_df.loc[best_idx, 'Model']
            selected_model = st.selectbox('Select model for forecasting:', model_names, index=best_idx)
            st.session_state['selected_model'] = selected_model
            # Explanations
            st.markdown("**RMSE:** Lower is better. Measures average prediction error.  ")
            st.markdown("**R²:** Closer to 1 is better. Measures how well the model explains the data.")
            if rel_perf_msg:
                st.info(rel_perf_msg)
        else:
            st.session_state['performance_df'] = None
            table_placeholder.warning('No valid model results to display. Please check your data or try a different target variable.')
            return  # Prevents use of best_model if no valid models
    else:
        # Not retraining, show cached table if available
        st.markdown("### 📊 Model Performance Comparison")
        table_placeholder = st.empty()
        if 'performance_df' in st.session_state and st.session_state['performance_df'] is not None:
            table_placeholder.table(st.session_state['performance_df'])
            model_names = st.session_state['performance_df']['Model'].tolist()
            best_idx = st.session_state['performance_df']['RMSE'].idxmin()
            selected_model = st.selectbox('Select model for forecasting:', model_names, index=best_idx, key='selectbox_cached')
            st.session_state['selected_model'] = selected_model
        else:
            table_placeholder.info("Train a model to see performance comparison.")
        
        # Find best model
        best_model_name = min(results.keys(), key=lambda x: results[x]['rmse'])
        best_model = results[best_model_name]['model']
        best_scaler = results[best_model_name]['scaler']
        
        st.success(f"🎯 Best Model: {best_model_name} (RMSE: {results[best_model_name]['rmse']:.2f})")
        
        # Create forecast
        st.markdown(f"## 📈 Forecast for {selected_target}")
        
        # Generate future dates
        last_date = df['Date'].max()
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30, freq='D')
        
        # Prepare future features
        future_df = pd.DataFrame({'Date': future_dates})
        future_df['DayOfWeek'] = future_df['Date'].dt.dayofweek
        future_df['Month'] = future_df['Date'].dt.month
        future_df['Quarter'] = future_df['Date'].dt.quarter
        future_df['Year'] = future_df['Date'].dt.year
        
        # Add seasonal features
        future_df['sin_day'] = np.sin(2 * np.pi * future_df['DayOfWeek'] / 7)
        future_df['cos_day'] = np.cos(2 * np.pi * future_df['DayOfWeek'] / 7)
        future_df['sin_month'] = np.sin(2 * np.pi * future_df['Month'] / 12)
        future_df['cos_month'] = np.cos(2 * np.pi * future_df['Month'] / 12)
        
        # Use last known values for lag features (improved approach)
        lag_features = [1, 7, 14, 30]
        rolling_windows = [7, 14, 30]
        last_known = df[[target_col]].copy()
        for lag in lag_features:
            last_known[f'{target_col}_lag_{lag}'] = last_known[target_col].shift(lag)
        for window in rolling_windows:
            last_known[f'{target_col}_rolling_mean_{window}'] = last_known[target_col].rolling(window=window).mean()
            last_known[f'{target_col}_rolling_std_{window}'] = last_known[target_col].rolling(window=window).std()
        last_known = last_known.dropna().tail(1)
        # For each future day, update lag/rolling features sequentially
        future_rows = []
        for i in range(len(future_df)):
            row = future_df.iloc[i].copy()
            # Use last forecast or last known for lag features
            for lag in lag_features:
                if i < lag:
                    row[f'{target_col}_lag_{lag}'] = last_known[target_col].values[0]
                else:
                    row[f'{target_col}_lag_{lag}'] = future_rows[i-lag]['Forecast']
            # Rolling features
            for window in rolling_windows:
                if i < window:
                    vals = list(last_known[target_col].values) + [r['Forecast'] for r in future_rows]
                    row[f'{target_col}_rolling_mean_{window}'] = np.mean(vals[-window:])
                    row[f'{target_col}_rolling_std_{window}'] = np.std(vals[-window:])
                else:
                    vals = [r['Forecast'] for r in future_rows]
                    row[f'{target_col}_rolling_mean_{window}'] = np.mean(vals[-window:])
                    row[f'{target_col}_rolling_std_{window}'] = np.std(vals[-window:])
            # Add placeholder for forecast
            row['Forecast'] = 0
            future_rows.append(row)
        # Prepare DataFrame for prediction
        future_pred_df = pd.DataFrame(future_rows)
        future_features = [col for col in future_pred_df.columns if col not in ['Date', 'Forecast']]
        X_future = future_pred_df[future_features]
        # Ensure X_future matches training features
        for col in X.columns:
            if col not in X_future.columns:
                X_future[col] = 0
        X_future = X_future[X.columns]
        # Make predictions sequentially (autoregressive)
        for i in range(len(future_pred_df)):
            row = X_future.iloc[i:i+1]
            if best_scaler:
                row_scaled = best_scaler.transform(row)
                pred = best_model.predict(row_scaled)[0]
            else:
                pred = best_model.predict(row)[0]
            future_pred_df.at[i, 'Forecast'] = pred
            # Update lag/rolling features for next step
            for lag in lag_features:
                if i+lag < len(future_pred_df):
                    future_pred_df.at[i+lag, f'{target_col}_lag_{lag}'] = pred
            for window in rolling_windows:
                if i+window < len(future_pred_df):
                    vals = list(last_known[target_col].values) + list(future_pred_df['Forecast'][:i+1])
                    mean = np.mean(vals[-window:])
                    std = np.std(vals[-window:])
                    future_pred_df.at[i+window, f'{target_col}_rolling_mean_{window}'] = mean
                    future_pred_df.at[i+window, f'{target_col}_rolling_std_{window}'] = std
        future_predictions = future_pred_df['Forecast'].values
        
        # Time range selector for historical data
        st.markdown('#### Select Historical Range')
        time_options = {
            '5D': 5,
            '1W': 7,
            '1M': 30,
            '6M': 182,
            '1Y': 365,
            '5Y': 1825,
            'All': None
        }
        selected_range = st.radio(
            label='Historical Range',
            options=list(time_options.keys()),
            index=2,  # Default to 1M
            horizontal=True
        )
        days = time_options[selected_range]
        if days is not None:
            historical_df = df[['Date', target_col]].sort_values('Date').tail(days)
        else:
            historical_df = df[['Date', target_col]].sort_values('Date')
        # Create forecast plot
        fig = go.Figure()
        # Historical data
        fig.add_trace(go.Scatter(
            x=historical_df['Date'],
            y=historical_df[target_col],
            name='Historical',
            line=dict(color='blue')
        ))
        # Forecast
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=future_predictions,
            name='Forecast',
            line=dict(color='red')
        ))
        fig.update_layout(
            title=f'{selected_target} Forecast (Next 30 Days)',
            xaxis_title='Date',
            yaxis_title=selected_target,
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Scenario analysis slider
        st.markdown('#### Scenario Analysis')
        scenario_pct = st.slider('Adjust demand by (%)', -50, 50, 0, 1)
        scenario_factor = 1 + scenario_pct / 100.0
        adjusted_forecast = future_predictions * scenario_factor

        # Customizable alert thresholds
        st.markdown('#### Alert Thresholds')
        threshold_type = st.radio('Threshold type:', ['Standard Deviation', 'Percentage', 'Absolute Value'], horizontal=True)
        if threshold_type == 'Standard Deviation':
            std_mult = st.slider('Std deviation multiplier', 0.5, 3.0, 1.0, 0.1)
            high_threshold = avg_forecast + std_mult * std_forecast
            low_threshold = avg_forecast - std_mult * std_forecast
        elif threshold_type == 'Percentage':
            pct = st.slider('Percent above/below average (%)', 1, 100, 20, 1)
            high_threshold = avg_forecast * (1 + pct / 100)
            low_threshold = avg_forecast * (1 - pct / 100)
        else:
            abs_val = st.number_input('Absolute value above/below average', min_value=0.0, value=std_forecast, step=1.0)
            high_threshold = avg_forecast + abs_val
            low_threshold = avg_forecast - abs_val

        # Operator notes/comments for forecast days
        st.markdown('#### Operator Notes')
        note_dates = st.multiselect('Select forecast dates to add notes:', [d.date() for d in future_dates])
        notes_dict = {}
        for d in note_dates:
            note = st.text_input(f'Note for {d}', key=f'note_{d}')
            notes_dict[str(d)] = note

        # Actionable recommendations and alerts (with notes)
        actions = []
        alerts = []
        notes_col = []
        for i, val in enumerate(adjusted_forecast):
            date_str = str(future_dates[i].date())
            note = notes_dict.get(date_str, '')
            notes_col.append(note)
            if val >= high_threshold:
                actions.append('Increase production')
                alerts.append('⚠️ High demand')
            elif val <= low_threshold:
                actions.append('Monitor inventory')
                alerts.append('⚠️ Low demand')
            else:
                actions.append('Normal')
                alerts.append('')

        # Capacity suggestions if available
        capacity_col = 'Capacity_Utilization' if 'Capacity_Utilization' in df.columns else None
        capacity_flags = []
        if capacity_col:
            avg_capacity = df[capacity_col].mean()
            for val in adjusted_forecast:
                if val > avg_capacity:
                    capacity_flags.append('⚠️ Exceeds avg capacity')
                else:
                    capacity_flags.append('')
        else:
            capacity_flags = [''] * len(adjusted_forecast)

        # Display forecast table with recommendations, alerts, and notes
        forecast_df = pd.DataFrame({
            'Date': future_dates,
            'Forecast': np.round(adjusted_forecast, 2),
            'Action': actions,
            'Alert': alerts,
            'Capacity Flag': capacity_flags,
            'Note': notes_col
        })
        st.markdown("### 📋 Forecast Details")
        st.table(forecast_df)
        # Download button for forecast table
        csv = forecast_df.to_csv(index=False).encode('utf-8')
        st.download_button('Download Forecast Table as CSV', csv, 'forecast.csv', 'text/csv')
        # Alerts summary
        st.markdown('### 🚨 Alerts Summary')
        for i, row in forecast_df.iterrows():
            if row['Alert'] or row['Capacity Flag'] or row['Note']:
                st.warning(f"{row['Date'].date()}: {row['Alert']} {row['Capacity Flag']} - {row['Action']} (Forecast: {row['Forecast']}) {row['Note']}")
        # Dashboard summary at the top
        n_high = sum(a == 'Increase production' for a in actions)
        n_low = sum(a == 'Monitor inventory' for a in actions)
        n_capacity = sum(bool(f) for f in capacity_flags)
        n_notes = sum(bool(n) for n in notes_col)
        st.markdown(f"### 📝 Operator Dashboard Summary\n- High demand days: {n_high}\n- Low demand days: {n_low}\n- Days exceeding capacity: {n_capacity}\n- Notes added: {n_notes}")
        # Summary statistics
        st.markdown('### 📊 Forecast Summary Statistics')
        st.info(f"Average: {avg_forecast:.2f} | Min: {np.min(adjusted_forecast):.2f} | Max: {np.max(adjusted_forecast):.2f} | Std Dev: {std_forecast:.2f}")
        # Download button for model performance table
        if 'performance_df' in st.session_state and st.session_state['performance_df'] is not None:
            perf_csv = st.session_state['performance_df'].to_csv(index=False).encode('utf-8')
            st.download_button('Download Model Performance Table as CSV', perf_csv, 'model_performance.csv', 'text/csv')

def create_capacity_optimization(df):
    """Create capacity optimization recommendations"""
    st.markdown("## ⚙️ Capacity Optimization Recommendations")
    
    # Calculate current capacity metrics
    avg_utilization = df['Capacity_Utilization'].mean()
    avg_downtime = df['Downtime_Hours'].mean()
    demand_variability = df['Total_Demand'].std() / df['Total_Demand'].mean()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Average Capacity Utilization", f"{avg_utilization:.1f}%")
    
    with col2:
        st.metric("Average Daily Downtime", f"{avg_downtime:.2f} hours")
    
    with col3:
        st.metric("Demand Variability (CV)", f"{demand_variability:.2f}")
    
    # Recommendations
    st.markdown("### 💡 Optimization Strategies")
    
    if avg_utilization < 70:
        st.warning("⚠️ **Low Capacity Utilization Detected**")
        st.markdown("""
        - **Issue**: Plant operating below optimal capacity
        - **Recommendations**:
            - Implement demand forecasting to better align production schedules
            - Consider flexible production lines for multiple products
            - Optimize batch sizes based on demand patterns
            - Implement just-in-time inventory management
        """)
    
    if avg_downtime > 2:
        st.error("🚨 **High Downtime Detected**")
        st.markdown("""
        - **Issue**: Excessive equipment downtime affecting production
        - **Recommendations**:
            - Implement preventive maintenance schedules
            - Train operators on equipment handling
            - Invest in backup equipment for critical processes
            - Monitor equipment health with IoT sensors
        """)
    
    if demand_variability > 0.3:
        st.info("📊 **High Demand Variability Detected**")
        st.markdown("""
        - **Issue**: Significant demand fluctuations making planning difficult
        - **Recommendations**:
            - Implement safety stock strategies
            - Use demand forecasting models for better planning
            - Consider flexible workforce scheduling
            - Develop multiple production scenarios
        """)
    
    # Seasonal analysis
    st.markdown("### 📈 Seasonal Analysis")
    
    monthly_demand = df.groupby('Month')['Total_Demand'].mean().reset_index()
    fig = px.bar(monthly_demand, x='Month', y='Total_Demand',
                title='Average Monthly Demand Pattern')
    st.plotly_chart(fig, use_container_width=True)

def main():
    """Main application function"""
    # Load data
    df = load_data()
    
    if df is None:
        st.error("Failed to load data. Please check the CSV file.")
        return
    
    # Sidebar
    st.sidebar.title("🥛 Dairy Forecasting")
    st.sidebar.markdown("---")
    
    page = st.sidebar.selectbox(
        "Select Page",
        ["📊 Dashboard", "🔮 Forecasting", "⚙️ Optimization", "📈 Analysis"]
    )
    
    if page == "📊 Dashboard":
        create_dashboard(df)
        create_visualizations(df)
    
    elif page == "🔮 Forecasting":
        create_forecasting_section(df)
    
    elif page == "⚙️ Optimization":
        create_capacity_optimization(df)
    
    elif page == "📈 Analysis":
        st.markdown("## 📈 Advanced Analytics")
        
        # Correlation analysis
        st.subheader("Correlation Analysis")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        correlation_cols = st.multiselect("Select columns for correlation:", numeric_cols,
                                         default=['Milk_Supply_Liters', 'Total_Demand', 'Capacity_Utilization', 'Downtime_Hours'])
        
        if len(correlation_cols) > 1:
            corr_matrix = df[correlation_cols].corr()
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
            st.pyplot(fig)
        
        # Distribution analysis
        st.subheader("Distribution Analysis")
        dist_col = st.selectbox("Select variable for distribution:", numeric_cols)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Histogram
        ax1.hist(df[dist_col].dropna(), bins=30, alpha=0.7, color='skyblue')
        ax1.set_title(f'Distribution of {dist_col}')
        ax1.set_xlabel(dist_col)
        ax1.set_ylabel('Frequency')
        
        # Box plot
        ax2.boxplot(df[dist_col].dropna())
        ax2.set_title(f'Box Plot of {dist_col}')
        ax2.set_ylabel(dist_col)
        
        st.pyplot(fig)

if __name__ == "__main__":
    main() 
