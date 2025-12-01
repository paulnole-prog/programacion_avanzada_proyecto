import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import unidecode
import numpy as np

# --- Configuración y Constantes Globales ---
FILE_NAME = "datos_de_entrada.csv"
pd.options.display.float_format = '{:,.2f}'.format

st.set_page_config(layout="wide", page_title="Análisis de Residuos")
st.title("Análisis de Residuos Municipales y Variación de GPC Domiciliaria")
st.markdown("---")

# --- Funciones de Carga y Preprocesamiento ---

@st.cache_data
def load_data(file_path):
    """Carga, estandariza y limpia los datos del CSV."""
    try:
        df = pd.read_csv(file_path, delimiter=';', encoding='latin1')
        
        # 1. Renombrar columnas clave para consistencia
        df = df.rename(columns={
            'PERIODO': 'AÑO',
            'QRESIDUOS_MUN': 'RESIDUOS_MUNICIPALES'
        }, errors='ignore')

        # 2. Estandarización de texto y tipo de datos
        df['DEPARTAMENTO'] = df['DEPARTAMENTO'].astype(str).apply(unidecode.unidecode).str.upper()
        df['DISTRITO'] = df['DISTRITO'].astype(str).apply(unidecode.unidecode).str.upper().str.strip()
        df['AÑO'] = df['AÑO'].astype(int)

        # 3. Limpieza y conversión de columnas numéricas
        cols_to_convert = ['GPC_DOM', 'QRESIDUOS_DOM', 'QRESIDUOS_NO_DOM', 'RESIDUOS_MUNICIPALES']
        for col in cols_to_convert:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False).str.replace(' ', '', regex=False)
                # Coercer errores a NaN y luego rellenar con 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Error al cargar/procesar '{file_path}': {e}")
        return pd.DataFrame()

# --- Funciones de Cálculo ---

def calculate_top_15_gpc_variation(df, start_year, end_year):
    """Calcula la variación porcentual de GPC_DOM entre dos años y retorna el Top 15."""
    
    df_start = df[df['AÑO'] == start_year][['DISTRITO', 'GPC_DOM']].rename(columns={'GPC_DOM': 'GPC_Start'})
    df_end = df[df['AÑO'] == end_year][['DISTRITO', 'GPC_DOM']].rename(columns={'GPC_DOM': 'GPC_End'})
    
    df_merged = pd.merge(df_start, df_end, on='DISTRITO', how='inner')
    
    # Manejar posibles ceros o NaNs
    df_merged.replace(0, np.nan, inplace=True)
    df_merged.dropna(subset=['GPC_Start', 'GPC_End'], inplace=True)

    df_merged['Incremento %'] = ((df_merged['GPC_End'] - df_merged['GPC_Start']) / df_merged['GPC_Start']) * 100

    df_plot_top15 = df_merged[['DISTRITO', 'Incremento %', 'GPC_Start', 'GPC_End']].sort_values('Incremento %', ascending=False).head(15).copy()
    df_plot_top15.columns = [
        'Distrito', 
        'Incremento Porcentual (%)', 
        f'GPC Domiciliaria {start_year} (kg/hab/día)', 
        f'GPC Domiciliaria {end_year} (kg/hab/día)'
    ]
    return df_plot_top15

# --- Funciones de Gráficos (Altair) ---

def get_eje_title(metric):
    """Retorna un título legible para la métrica del eje."""
    titles = {
        'GPC_DOM': 'GPC Domiciliaria (kg/hab/día)',
        'RESIDUOS_MUNICIPALES': 'Residuos Municipales (t)',
        'QRESIDUOS_DOM': 'Residuos Domiciliarios (t)',
        'QRESIDUOS_NO_DOM': 'Residuos No Domiciliarios (t)'
    }
    return titles.get(metric, metric)

def create_bar_chart(df, start_year, end_year, departamento):
    """Genera el Gráfico de Barras: Top 15 Variación."""
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Distrito:N', title='Distrito', sort='-y'),
        y=alt.Y('Incremento Porcentual (%):Q', title='Incremento GPC Domiciliaria (%)'),
        color=alt.condition(alt.datum['Incremento Porcentual (%)'] > 0, alt.value("#2ecc71"), alt.value("#e74c3c")),
        tooltip=[
            'Distrito:N',
            alt.Tooltip('Incremento Porcentual (%):Q', format='.2f'),
            alt.Tooltip(f'GPC Domiciliaria {start_year} (kg/hab/día):Q', format='.3f'),
            alt.Tooltip(f'GPC Domiciliaria {end_year} (kg/hab/día):Q', format='.3f'),
        ]
    ).properties(
        title=f"Top 15 de {departamento}: Variación GPC Domiciliaria ({start_year} vs {end_year})"
    ).interactive()
    return chart

def create_scatter_chart(df_scatter, x_metric, y_metric, scatter_year):
    """Genera el Gráfico de Dispersión: Correlación entre métricas."""
    chart = alt.Chart(df_scatter).mark_circle(size=60).encode(
        x=alt.X(f'{x_metric}:Q', title=get_eje_title(x_metric)),
        y=alt.Y(f'{y_metric}:Q', title=get_eje_title(y_metric)),
        tooltip=['DISTRITO', x_metric, y_metric],
        color=alt.Color(f'{y_metric}:Q', scale=alt.Scale(range='heatmap'), title=get_eje_title(y_metric))
    ).properties(
        title=f'Correlación: {get_eje_title(y_metric)} vs {get_eje_title(x_metric)} ({scatter_year})'
    ).interactive()
    return chart

def create_line_chart(df_line_plot, distrito_seleccionado, departamento):
    """Genera el Gráfico de Líneas: Tendencia de Residuos por Distrito."""
    chart = alt.Chart(df_line_plot).mark_line(point=True).encode(
        x=alt.X('AÑO:N', title='Año', axis=alt.Axis(format='d')), 
        y=alt.Y('RESIDUOS_MUNICIPALES:Q', title='Cantidad de residuos (t)'),
        tooltip=[
            'AÑO:N', 
            alt.Tooltip('RESIDUOS_MUNICIPALES:Q', title='Cantidad de residuos (t)', format=',.0f')
        ]
    ).properties(
        title=f"Evolución de Residuos en {distrito_seleccionado} ({departamento})"
    ).interactive()
    return chart

# --- Función de Gráfico de Pastel y Métricas (Plotly) ---

def create_pie_chart_and_metrics(df_data, departamento_sel, distrito_sel, año_sel):
    """Crea el gráfico de pastel y las métricas de resumen para un distrito/año."""
    
    st.subheader(f"Análisis Detallado de Residuos: {distrito_sel}, {departamento_sel} - {año_sel}")
    
    datos_filtrados = df_data[
        (df_data['DEPARTAMENTO'] == departamento_sel) &
        (df_data['DISTRITO'] == distrito_sel) &
        (df_data['AÑO'] == año_sel)
    ]

    if datos_filtrados.empty:
        st.warning(f"No se encontraron datos para los filtros: Distrito: {distrito_sel}, Año: {año_sel}.")
        return

    fila = datos_filtrados.iloc[0]
    residuos_dom = float(fila['QRESIDUOS_DOM'])
    residuos_no_dom = float(fila['QRESIDUOS_NO_DOM'])
    
    labels = ['Residuos Domésticos', 'Residuos No Domésticos']
    values = [residuos_dom, residuos_no_dom]
    
    # Creación y configuración del gráfico de pastel
    fig = px.pie(
        names=labels,
        values=values,
        title='Distribución de Residuos Municipales',
        color=labels,
        color_discrete_map={
            'Residuos Domésticos': '#FF6B6B',
            'Residuos No Domésticos': '#4ECDC4'
        }
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label+value',
        hovertemplate='<b>%{label}</b><br>Cantidad: %{value:.2f} ton<br>Porcentaje: %{percent}'
    )

    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"))

    st.plotly_chart(fig, use_container_width=True)

    # Mostrar métricas
    col1, col2, col3 = st.columns(3)
    total = residuos_dom + residuos_no_dom
    
    with col1:
        st.metric("Residuos Domésticos", f"{residuos_dom:,.2f} ton")
    with col2:
        st.metric("Residuos No Domésticos", f"{residuos_no_dom:,.2f} ton")
    with col3:
        st.metric("Total Residuos", f"{total:,.2f} ton")


# --- Lógica Principal de la Aplicación (Main) ---

df_all = load_data(FILE_NAME)

if df_all.empty:
    st.error("No se pudieron cargar los datos.")
else:
    available_departamentos = sorted(df_all['DEPARTAMENTO'].unique())

    # --- Sidebar (Filtros Globales) ---
    st.sidebar.header("Opciones de Análisis")

    departamento_seleccionado = st.sidebar.selectbox(
        "Departamento Principal",
        options=available_departamentos,
        index=available_departamentos.index('LIMA') if 'LIMA' in available_departamentos else 0,
    )
    
    df_filtrado_por_departamento = df_all[df_all['DEPARTAMENTO'] == departamento_seleccionado].copy()

    current_available_years = sorted(df_filtrado_por_departamento['AÑO'].unique())

    if len(current_available_years) < 2:
        st.error(f"El departamento de **{departamento_seleccionado}** no tiene datos para al menos dos años para el análisis de variación.")
        st.stop()

    # --- Parámetros de Variación (Top 15) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Parámetros Top 15 (GPC)")
    start_year = st.sidebar.selectbox("Año Base", options=current_available_years, index=0)
    end_year = st.sidebar.selectbox("Año Comparación", options=current_available_years, index=len(current_available_years) - 1)

    if start_year >= end_year:
        st.error("El Año de Comparación debe ser *posterior* al Año Base.")
    else:
        # --- Generar TOP 15 ---
        df_plot_top15 = calculate_top_15_gpc_variation(df_filtrado_por_departamento, start_year, end_year)


        # 1. GRÁFICO DE BARRAS (Top 15 Variación)
        st.header("Variación de la Generación Per Cápita Domiciliaria (GPC)")
        st.info(f"Top 15 distritos de **{departamento_seleccionado}** con mayor variación de GPC Domiciliaria entre {start_year} y {end_year}.")
        st.altair_chart(create_bar_chart(df_plot_top15, start_year, end_year, departamento_seleccionado), use_container_width=True)

        
        # 2. ANÁLISIS DETALLADO (Gráfico de Pastel)
        st.markdown("---")
        
        available_distritos = sorted(df_filtrado_por_departamento['DISTRITO'].unique())

        col_distrito_pie, col_year_pie = st.columns(2)

        with col_distrito_pie:
            distrito_analisis_seleccionado = st.selectbox(
                "Distrito para Análisis Detallado",
                options=available_distritos,
                index=0, 
                key='sel_distrito_analisis' 
            )

        with col_year_pie:
            año_analisis_seleccionado = st.selectbox(
                "Año del Análisis Detallado",
                options=current_available_years,
                index=len(current_available_years) - 1,
                key='sel_ano_analisis' 
            )
        
        create_pie_chart_and_metrics(df_filtrado_por_departamento, departamento_seleccionado, distrito_analisis_seleccionado, año_analisis_seleccionado)
        
    
        # 3. GRÁFICO DE DISPERSIÓN (Correlación)
        st.markdown("---")
        st.header("Correlación entre Métricas")

        metric_options = ['GPC_DOM', 'RESIDUOS_MUNICIPALES', 'QRESIDUOS_DOM', 'QRESIDUOS_NO_DOM']
        
        col_y, col_x, col_year = st.columns(3)

        with col_y:
            y_metric = st.selectbox("Eje Y (Métrica Principal)", options=metric_options, index=0)
        with col_x:
            x_metric = st.selectbox("Eje X (Métrica a Comparar)", options=metric_options, index=1)
        with col_year:
            scatter_year = st.selectbox("Año de Correlación", options=current_available_years, index=len(current_available_years) - 1)

        df_scatter = df_filtrado_por_departamento[df_filtrado_por_departamento['AÑO'] == scatter_year].copy()
        
        st.altair_chart(create_scatter_chart(df_scatter, x_metric, y_metric, scatter_year), use_container_width=True)

        
      
        # 4. GRÁFICO DE LÍNEAS 
        st.markdown("---")
        st.header("Tendencia Histórica de Residuos")

        # Usamos el distrito seleccionado en el análisis detallado como valor inicial
        available_distritos_linea = sorted(df_filtrado_por_departamento['DISTRITO'].unique())

        distrito_linea_seleccionado = st.selectbox(
            "Seleccione el Distrito para ver su evolución anual",
            options=available_distritos_linea,
            index=available_distritos_linea.index(distrito_analisis_seleccionado) if distrito_analisis_seleccionado in available_distritos_linea else 0,
        )

        df_line_plot = df_filtrado_por_departamento[df_filtrado_por_departamento['DISTRITO'] == distrito_linea_seleccionado].copy()
        st.altair_chart(create_line_chart(df_line_plot, distrito_linea_seleccionado, departamento_seleccionado), use_container_width=True)
        
        
        # --- Pie de página ---
        st.markdown("---")
        st.caption(f"Análisis realizado para el departamento de **{departamento_seleccionado}**.")
