# pages/14_Tendencia.py - Análisis de Tendencias Epidemiológicas
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.common import query_duckdb, get_distinct_events
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Modelos estadísticos
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_squared_error, mean_absolute_error

st.set_page_config(page_title="Tendencias", page_icon="📈", layout="wide")
st.title("📈 Análisis de Tendencias Epidemiológicas")
st.markdown("Predicción con modelos estadísticos considerando estacionalidad del hemisferio sur")

# Función para tests de estacionaridad
def test_stationarity(timeseries):
    results = {}
    adf_result = adfuller(timeseries.dropna(), autolag='AIC')
    results['adf'] = {
        'statistic': adf_result[0],
        'p_value': adf_result[1],
        'is_stationary': adf_result[1] < 0.05
    }

    kpss_result = kpss(timeseries.dropna(), regression='ct', nlags='auto')
    results['kpss'] = {
        'statistic': kpss_result[0],
        'p_value': kpss_result[1],
        'is_stationary': kpss_result[1] > 0.05
    }
    return results

# Función para convertir semana epidemiológica a fecha
def epiweek_to_date(year, week):
    jan_1 = datetime(year, 1, 1)
    days_to_sunday = (6 - jan_1.weekday()) % 7
    first_sunday = jan_1 + timedelta(days=days_to_sunday)
    target_date = first_sunday + timedelta(weeks=(week - 1))
    return target_date

# Cargar datos desde Parquet
query = """
SELECT ANIO, SEMANA, NOMBREEVENTOAGRP, CANTIDAD
FROM {parquet}
WHERE ANIO >= 2018 AND SEMANA != 53
"""
df = query_duckdb(query)
if df.empty:
    st.error("⚠️ No hay datos. Ejecuta el ETL: `python etl_semanal.py`")
    st.stop()

# FILTROS HORIZONTALES
st.markdown("### 🎯 Configuración")
col1, col2, col3 = st.columns(3)
with col1:
    events = get_distinct_events()
    evento = st.selectbox("🦠 Patología", events)
with col2:
    año_actual = datetime.now().year
    año_futuro = st.selectbox(
        "📅 Año a Predecir",
        [año_actual + 1],  # Solo permite seleccionar el año siguiente
        help="Año futuro a proyectar usando todos los datos históricos"
    )
with col3:
    modelo_seleccionado = st.selectbox(
        "🔬 Modelo",
        ["Prophet", "SARIMA", "ETS"] if PROPHET_AVAILABLE else ["SARIMA", "ETS"]
    )
st.markdown("---")

# Preparar datos
df_evento = df[df["NOMBREEVENTOAGRP"] == evento].copy()
if df_evento.empty:
    st.warning(f"No hay datos para {evento}")
    st.stop()

df_ts = df_evento.groupby(["ANIO", "SEMANA"])["CANTIDAD"].sum().reset_index()
df_ts['fecha'] = df_ts.apply(lambda x: epiweek_to_date(int(x['ANIO']), int(x['SEMANA'])), axis=1)
df_ts = df_ts.sort_values('fecha').reset_index(drop=True)

# Calcular semanas a predecir
último_año = df_ts['ANIO'].max()
última_semana = df_ts[df_ts['ANIO'] == último_año]['SEMANA'].max()
años_diff = año_futuro - último_año
semanas_restantes = 52 - última_semana
periodos_prediccion = semanas_restantes + (años_diff - 1) * 52 + 52

# Info
st.info(f"""
**Configuración**: {evento} | Histórico: {df_ts['ANIO'].min()}-{último_año} ({len(df_ts)} semanas) |
Prediciendo: {periodos_prediccion} semanas hasta {año_futuro} | Modelo: {modelo_seleccionado}
""")

# TABS
tab1, tab2, tab3 = st.tabs(["📊 Serie & Descomposición", "🔍 Diagnóstico", "🎯 Predicción"])

# TAB 1: EXPLORACIÓN
with tab1:
    st.subheader("Serie Temporal Histórica")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_ts['fecha'], y=df_ts['CANTIDAD'],
        mode='lines', name='Casos',
        line=dict(color='#1f77b4', width=2)
    ))
    fig.update_layout(
        xaxis_title="Fecha (Semana Epidemiológica)",
        yaxis_title="Casos",
        hovermode='x unified',
        height=350
    )
    st.plotly_chart(fig, use_container_width=True)

    # Descomposición STL
    if len(df_ts) >= 104:
        st.subheader("Descomposición STL")
        try:
            stl = STL(df_ts.set_index('fecha')['CANTIDAD'], seasonal=53, period=52)
            result = stl.fit()

            fig_stl = make_subplots(
                rows=4, cols=1,
                subplot_titles=('Original', 'Tendencia', 'Estacionalidad', 'Residuos'),
                vertical_spacing=0.08
            )
            fig_stl.add_trace(go.Scatter(x=df_ts['fecha'], y=df_ts['CANTIDAD'], line=dict(color='blue')), row=1, col=1)
            fig_stl.add_trace(go.Scatter(x=df_ts['fecha'], y=result.trend, line=dict(color='red')), row=2, col=1)
            fig_stl.add_trace(go.Scatter(x=df_ts['fecha'], y=result.seasonal, line=dict(color='green')), row=3, col=1)
            fig_stl.add_trace(go.Scatter(x=df_ts['fecha'], y=result.resid, line=dict(color='orange')), row=4, col=1)
            fig_stl.update_layout(height=700, showlegend=False)
            st.plotly_chart(fig_stl, use_container_width=True)
        except Exception as e:
            st.warning(f"STL falló: {e}")

# TAB 2: DIAGNÓSTICO
with tab2:
    st.subheader("Tests de Estacionaridad")
    stat_results = test_stationarity(df_ts['CANTIDAD'])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**ADF** (H0: NO estacionaria)")
        adf_ok = stat_results['adf']['is_stationary']
        st.markdown(f"- p-value: {stat_results['adf']['p_value']:.4f}")
        st.markdown(f"- {'✅ Estacionaria' if adf_ok else '❌ No Estacionaria'}")

    with col2:
        st.markdown("**KPSS** (H0: ES estacionaria)")
        kpss_ok = stat_results['kpss']['is_stationary']
        st.markdown(f"- p-value: {stat_results['kpss']['p_value']:.4f}")
        st.markdown(f"- {'✅ Estacionaria' if kpss_ok else '❌ No Estacionaria'}")

    st.subheader("Patrón Estacional (Hemisferio Sur)")
    df_ts['semana_año'] = df_ts['SEMANA']
    seasonal = df_ts.groupby('semana_año')['CANTIDAD'].mean().reset_index()

    fig_s = go.Figure()
    fig_s.add_trace(go.Bar(x=seasonal['semana_año'], y=seasonal['CANTIDAD'], marker_color='lightblue'))
    fig_s.add_vrect(x0=48, x1=52, fillcolor="red", opacity=0.1, annotation_text="Verano", annotation_position="top left")
    fig_s.add_vrect(x0=1, x1=13, fillcolor="red", opacity=0.1)
    fig_s.add_vrect(x0=26, x1=35, fillcolor="blue", opacity=0.1, annotation_text="Invierno", annotation_position="top left")
    fig_s.update_layout(xaxis_title="Semana del Año", yaxis_title="Casos Promedio", height=350)
    st.plotly_chart(fig_s, use_container_width=True)

# TAB 3: PREDICCIÓN
with tab3:
    st.subheader(f"Predicción hasta {año_futuro}")

    df_train = df_ts.copy()  # Usar TODOS los datos históricos

    if modelo_seleccionado == "Prophet" and PROPHET_AVAILABLE:
        df_prophet = df_train[['fecha', 'CANTIDAD']].rename(columns={'fecha': 'ds', 'CANTIDAD': 'y'})

        with st.spinner('Entrenando Prophet...'):
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                seasonality_mode='multiplicative',
                changepoint_prior_scale=0.05
            )
            model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
            model.fit(df_prophet)

            future = model.make_future_dataframe(periods=periodos_prediccion, freq='W')
            forecast = model.predict(future)

            # Forzar valores no negativos y redondear a enteros
            forecast['yhat'] = np.round(np.maximum(forecast['yhat'], 0)).astype(int)
            forecast['yhat_upper'] = np.round(np.maximum(forecast['yhat_upper'], 0)).astype(int)
            forecast['yhat_lower'] = np.round(np.maximum(forecast['yhat_lower'], 0)).astype(int)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_ts['fecha'], y=df_ts['CANTIDAD'], mode='lines', name='Histórico', line=dict(color='blue', width=2)))

            future_forecast = forecast[forecast['ds'] > df_ts['fecha'].max()]
            fig.add_trace(go.Scatter(x=future_forecast['ds'], y=future_forecast['yhat'], mode='lines', name=f'Predicción {año_futuro}', line=dict(color='red', width=2, dash='dash')))
            fig.add_trace(go.Scatter(x=future_forecast['ds'], y=future_forecast['yhat_upper'], mode='lines', line=dict(width=0), showlegend=False))
            fig.add_trace(go.Scatter(x=future_forecast['ds'], y=future_forecast['yhat_lower'], mode='lines', fill='tonexty', fillcolor='rgba(255,0,0,0.2)', line=dict(width=0), name='IC'))

            fig.add_vline(x=df_ts['fecha'].max(), line_dash="dot", line_color="gray", annotation_text="Inicio Predicción")
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Casos", height=500, hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

            # Tabla pivot de predicciones por semana (1-52)
            forecast_df = pd.DataFrame({
                'Semana': range(1, 53),
                'Casos Predichos': future_forecast['yhat'].values[:52]
            })
            st.subheader(f"Predicción detallada para {año_futuro}")
            st.dataframe(forecast_df.set_index('Semana').T, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Promedio Predicho", f"{int(future_forecast['yhat'].mean())}")
            col2.metric("📈 Pico Predicho", f"{int(future_forecast['yhat'].max())}")
            col3.metric("📉 Mínimo Predicho", f"{int(future_forecast['yhat'].min())}")

    elif modelo_seleccionado == "SARIMA":
        with st.spinner('Entrenando SARIMA...'):
            try:
                steps = int(periodos_prediccion)
                y_train = df_train['CANTIDAD'].reset_index(drop=True)

                model = SARIMAX(y_train, order=(1,1,1), seasonal_order=(1,1,1,52))
                results = model.fit(disp=False)

                forecast_sarima = results.forecast(steps=steps)
                # Forzar valores no negativos y redondear a enteros
                forecast_sarima = np.round(np.maximum(forecast_sarima, 0)).astype(int)

                forecast_dates = pd.date_range(start=df_train['fecha'].iloc[-1] + timedelta(weeks=1), periods=len(forecast_sarima), freq='W')

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_ts['fecha'], y=df_ts['CANTIDAD'], mode='lines', name='Histórico', line=dict(color='blue', width=2)))
                fig.add_trace(go.Scatter(x=forecast_dates, y=forecast_sarima, mode='lines', name=f'Predicción {año_futuro}', line=dict(color='red', width=2, dash='dash')))
                fig.add_vline(x=df_ts['fecha'].max(), line_dash="dot", line_color="gray")
                fig.update_layout(xaxis_title="Fecha", yaxis_title="Casos", height=500)
                st.plotly_chart(fig, use_container_width=True)

                # Tabla pivot de predicciones por semana (1-52)
                forecast_df = pd.DataFrame({
                    'Semana': range(1, 53),
                    'Casos Predichos': forecast_sarima[:52]
                })
                st.subheader(f"Predicción detallada para {año_futuro}")
                st.dataframe(forecast_df.set_index('Semana').T, use_container_width=True)

                col1, col2 = st.columns(2)
                col1.metric("📊 Promedio Predicho", f"{int(forecast_sarima.mean())}")
                col2.metric("📈 Pico Predicho", f"{int(forecast_sarima.max())}")
            except Exception as e:
                st.error(f"SARIMA falló: {e}")

    elif modelo_seleccionado == "ETS":
        try:
            model = ExponentialSmoothing(df_train['CANTIDAD'], seasonal_periods=52, trend='add', seasonal='add')
            results = model.fit()

            forecast_ets = results.forecast(steps=periodos_prediccion)
            # Forzar valores no negativos y redondear a enteros
            forecast_ets = np.round(np.maximum(forecast_ets, 0)).astype(int)

            forecast_dates = pd.date_range(start=df_train['fecha'].iloc[-1] + timedelta(weeks=1), periods=len(forecast_ets), freq='W')

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_ts['fecha'], y=df_ts['CANTIDAD'], mode='lines', name='Histórico', line=dict(color='blue', width=2)))
            fig.add_trace(go.Scatter(x=forecast_dates, y=forecast_ets, mode='lines', name=f'Predicción {año_futuro}', line=dict(color='green', width=2, dash='dash')))
            fig.add_vline(x=df_ts['fecha'].max(), line_dash="dot", line_color="gray")
            fig.update_layout(xaxis_title="Fecha", yaxis_title="Casos", height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Tabla pivot de predicciones por semana (1-52)
            forecast_df = pd.DataFrame({
                'Semana': range(1, 53),
                'Casos Predichos': forecast_ets[:52]
            })
            st.subheader(f"Predicción detallada para {año_futuro}")
            st.dataframe(forecast_df.set_index('Semana').T, use_container_width=True)

            col1, col2 = st.columns(2)
            col1.metric("📊 Promedio Predicho", f"{int(forecast_ets.mean())}")
            col2.metric("📈 Pico Predicho", f"{int(forecast_ets.max())}")
        except Exception as e:
            st.error(f"ETS falló: {e}")

st.markdown("---")
st.markdown("<div style='text-align: center; color: gray;'>📅 Semanas Epidemiológicas | 🌎 Hemisferio Sur</div>", unsafe_allow_html=True)
