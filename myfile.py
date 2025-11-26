import streamlit as st
import pandas as pd
import altair as alt
import unidecode
import numpy as np

# --- Configuración y Datos ---
FILE_NAME = "datos_de_entrada.csv"

# Configuración de Pandas (práctica común)
pd.options.display.float_format = '{:,.2f}'.format

st.set_page_config(layout="wide")
st.title("Top 15 Distritos con Mayor Variación de GPC Domiciliaria 📈")
st.markdown("Análisis del *Incremento Porcentual* de la GPC Domiciliaria (GPC_DOM) entre dos años para los distritos del **Departamento seleccionado**.")


@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path, delimiter=';', encoding='latin1')
        
        # Estandarización
        df['DEPARTAMENTO'] = df['DEPARTAMENTO'].astype(str).apply(unidecode.unidecode).str.upper()
        df['DISTRITO'] = df['DISTRITO'].astype(str).apply(unidecode.unidecode).str.upper().str.strip()
        df['PERIODO'] = df['PERIODO'].astype(int)

        cols_to_convert = ['GPC_DOM', 'QRESIDUOS_DOM', 'QRESIDUOS_NO_DOM', 'QRESIDUOS_MUN']
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        return df
    except Exception as e:
        st.error(f"Error al cargar/procesar '{file_path}': {e}")
        return pd.DataFrame()

# --- Funciones de Utilidad y Gráficos ---

def get_eje_title(metric):
    """Retorna un título legible para la métrica del eje."""
    if metric == 'GPC_DOM': return 'GPC Domiciliaria (kg/hab/día)'
    if metric == 'QRESIDUOS_MUN': return 'Residuos Municipales (t)'
    if metric == 'QRESIDUOS_DOM': return 'Residuos Domiciliarios (t)'
    if metric == 'QRESIDUOS_NO_DOM': return 'Residuos No Domiciliarios (t)'
    return metric

def create_bar_chart(df, start_year, end_year, departamento):
    """Gráfico de Barras: Top 15 Variación."""
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
        title=f"Top 15 de {departamento}: Variación de GPC Domiciliaria ({start_year} a {end_year})"
    ).interactive()
    return chart

def create_scatter_chart(df_scatter, departamento, scatter_year, x_metric, y_metric):
    """Gráfico de Dispersión: Correlación entre métricas."""
    chart = alt.Chart(df_scatter).mark_circle().encode(
        x=alt.X(f'{x_metric}:Q', title=get_eje_title(x_metric)),
        y=alt.Y(f'{y_metric}:Q', title=get_eje_title(y_metric)),
        tooltip=['DISTRITO', x_metric, y_metric],
        color=alt.Color(f'{y_metric}:Q', scale=alt.Scale(range='heatmap'), title=get_eje_title(y_metric))
    ).properties(
        title=f'Dispersión: {get_eje_title(y_metric)} vs {get_eje_title(x_metric)} ({scatter_year})'
    ).interactive()
    return chart

def create_line_chart(df_line_plot, distrito_seleccionado, departamento):
    """Gráfico de Líneas: Tendencia de Residuos por Distrito."""
    chart = alt.Chart(df_line_plot).mark_line(point=True).encode(
        x=alt.X('PERIODO:N', title='Año', axis=alt.Axis(format='d')), 
        y=alt.Y('QRESIDUOS_MUN:Q', title='Cantidad de residuos (t)'),
        tooltip=[
            'PERIODO:N', 
            alt.Tooltip('QRESIDUOS_MUN:Q', title='Cantidad de residuos (t)', format=',.0f')
        ]
    ).properties(
        title=f"Evolución de Residuos en {distrito_seleccionado} ({departamento})"
    ).interactive()
    return chart

# --- Lógica Principal ---

df_all = load_data(FILE_NAME)

if not df_all.empty:
    available_departamentos = sorted(df_all['DEPARTAMENTO'].unique())

    st.sidebar.header("Selección de Parámetros")

    departamento_seleccionado = st.sidebar.selectbox(
        "Seleccione el Departamento a Analizar",
        options=available_departamentos,
        index=available_departamentos.index('LIMA') if 'LIMA' in available_departamentos else 0,
        key='sel_departamento'
    )
    
    df_filtrado_por_departamento = df_all[df_all['DEPARTAMENTO'] == departamento_seleccionado].copy()
    run_charts = False 

    if len(df_filtrado_por_departamento['PERIODO'].unique()) < 2:
        st.error(f"El departamento de **{departamento_seleccionado}** no tiene datos para al menos dos años. Seleccione otro departamento.")
    else:
        current_available_years = sorted(df_filtrado_por_departamento['PERIODO'].unique())
        
        # Selectores de Año (Para Barras)
        start_year = st.sidebar.selectbox("Seleccione el Año Inicial (Base)", options=current_available_years, index=0, key='sel_ano_inicial')
        end_year = st.sidebar.selectbox("Seleccione el Año Final (Comparación)", options=current_available_years, index=len(current_available_years) - 1, key='sel_ano_final')

        if start_year >= end_year:
            st.error("El Año Final debe ser *mayor* que el Año Inicial.")
        else:
            # --- CÁLCULO DE DATOS TOP 15 ---
            df_start = df_filtrado_por_departamento[df_filtrado_por_departamento['PERIODO'] == start_year][['DISTRITO', 'GPC_DOM']].rename(columns={'GPC_DOM': 'GPC_Start'})
            df_end = df_filtrado_por_departamento[df_filtrado_por_departamento['PERIODO'] == end_year][['DISTRITO', 'GPC_DOM']].rename(columns={'GPC_DOM': 'GPC_End'})
            
            df_merged = pd.merge(df_start, df_end, on='DISTRITO', how='inner')
            df_merged.replace(0, pd.NA, inplace=True)
            df_merged.dropna(subset=['GPC_Start', 'GPC_End'], inplace=True)

            df_merged['Incremento %'] = ((df_merged['GPC_End'] - df_merged['GPC_Start']) / df_merged['GPC_Start']) * 100

            df_plot_top15 = df_merged[['DISTRITO', 'Incremento %', 'GPC_Start', 'GPC_End']].sort_values('Incremento %', ascending=False).head(15).copy()
            df_plot_top15.columns = ['Distrito', 'Incremento Porcentual (%)', f'GPC Domiciliaria {start_year} (kg/hab/día)', f'GPC Domiciliaria {end_year} (kg/hab/día)']
            
            run_charts = True 

    if run_charts:
        
        # =======================================================
        # 1. GRÁFICO DE BARRAS (Top 15 Variación)
        # =======================================================
        st.subheader(f"Top 15 Distritos de {departamento_seleccionado} con Mayor Variación de GPC Domiciliaria: {start_year} vs {end_year}")
        st.info(f"El gráfico muestra los *15 distritos* de **{departamento_seleccionado}** con la mayor variación porcentual.")
        st.altair_chart(create_bar_chart(df_plot_top15, start_year, end_year, departamento_seleccionado), use_container_width=True)

        # ----------------------------------------------------------------------------------------------------------------------------------------------------
        # 2. GRÁFICO DE DISPERSIÓN (SCATTER PLOT)
        # ----------------------------------------------------------------------------------------------------------------------------------------------------
        st.markdown("---")
        st.subheader("Dispersión y Correlación entre Métricas 📊")

        metric_options = ['GPC_DOM', 'QRESIDUOS_MUN', 'QRESIDUOS_DOM', 'QRESIDUOS_NO_DOM']
        
        col_y, col_x, col_year = st.columns(3)

        with col_y:
            y_metric = st.selectbox("Eje Y (Métrica Principal)", options=metric_options, index=0, key=f'sel_eje_y_{departamento_seleccionado}')

        with col_x:
            x_metric = st.selectbox("Eje X (Métrica a Comparar)", options=metric_options, index=1, key=f'sel_eje_x_{departamento_seleccionado}')

        with col_year:
            scatter_year = st.selectbox("Año de Análisis (Dispersión)", options=current_available_years, index=len(current_available_years) - 1, key=f'sel_ano_disp_{departamento_seleccionado}')

        df_scatter = df_filtrado_por_departamento[df_filtrado_por_departamento['PERIODO'] == scatter_year].copy()
        
        st.altair_chart(create_scatter_chart(df_scatter, departamento_seleccionado, scatter_year, x_metric, y_metric), use_container_width=True)

        # ----------------------------------------------------------------------------------------------------------------------------------------------------
        # 3. GRÁFICO DE LÍNEAS (Tendencia Temporal de Residuos)
        # ----------------------------------------------------------------------------------------------------------------------------------------------------
        st.markdown("---")
        st.subheader("Tendencia de la Cantidad de Residuos a lo largo del tiempo")

        available_distritos_linea = sorted(df_filtrado_por_departamento['DISTRITO'].unique())

        distrito_linea_seleccionado = st.selectbox(
            "Seleccione el Distrito para ver su evolución anual",
            options=available_distritos_linea,
            index=0, 
            key=f'sel_distrito_linea_residuos_{departamento_seleccionado}' 
        )

        df_line_plot = df_filtrado_por_departamento[df_filtrado_por_departamento['DISTRITO'] == distrito_linea_seleccionado].copy()
        st.altair_chart(create_line_chart(df_line_plot, distrito_linea_seleccionado, departamento_seleccionado), use_container_width=True)
        
        # Nota Final
        st.markdown("---")
        st.caption(f"Nota: Se muestran los 15 distritos de {departamento_seleccionado} con la mayor variación porcentual entre los años seleccionados.")
        
else:
    st.error("No se pudieron cargar los datos. Verifique que el archivo 'datos_de_entrada.csv' exista y contenga datos.")
