import streamlit as st
import pandas as pd
import altair as alt

# --- Configuración y Carga de Datos ---
FILE_NAME = "datos_de_entrada.csv"

st.set_page_config(layout="wide")
st.title("Top 15 Distritos con Mayor Variación de GPC Domiciliaria 📈")
st.markdown(
    "Análisis del *Incremento Porcentual* de la Generación Per Cápita Domiciliaria (GPC_DOM) entre dos años para los distritos del **Departamento seleccionado**.")



def load_data(file_path):
    """Carga, limpia y prepara el DataFrame."""
    try:
        df = pd.read_csv(file_path, delimiter=';', encoding='latin1')

        df['PERIODO'] = df['PERIODO'].astype(int)

        cols_to_convert = ['GPC_DOM', 'QRESIDUOS_DOM', 'QRESIDUOS_NO_DOM', 'QRESIDUOS_MUN']
        for col in cols_to_convert:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Retorna el DataFrame completo sin filtrar por departamento.
        return df
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo '{file_path}'. Asegúrese de que el archivo esté en la misma carpeta.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")
        return pd.DataFrame()


df_all = load_data(FILE_NAME)

if not df_all.empty:
    available_years = sorted(df_all['PERIODO'].unique())
    available_departamentos = sorted(df_all['DEPARTAMENTO'].unique())

    # --- Opciones de Filtrado en la Barra Lateral ---
    st.sidebar.header("Selección de Parámetros")

    # Selector de Departamento
    departamento_seleccionado = st.sidebar.selectbox(
        "Seleccione el Departamento a Analizar",
        options=available_departamentos,
        index=available_departamentos.index('LIMA') if 'LIMA' in available_departamentos else 0
    )
    
    # Aplica filtro por Departamento
    df_filtrado_por_departamento = df_all[df_all['DEPARTAMENTO'] == departamento_seleccionado].copy()

    # Validación de datos para el departamento seleccionado
    if len(df_filtrado_por_departamento['PERIODO'].unique()) < 2:
        st.error(f"El departamento de **{departamento_seleccionado}** no tiene datos para al menos dos años. Seleccione otro departamento.")
    else:
        current_available_years = sorted(df_filtrado_por_departamento['PERIODO'].unique())
        
        # Selector de Año Inicial (Base)
        start_year = st.sidebar.selectbox(
            "Seleccione el Año Inicial (Base)",
            options=current_available_years,
            index=0
        )

        # Selector de Año Final (Comparación)
        end_year = st.sidebar.selectbox(
            "Seleccione el Año Final (Comparación)",
            options=current_available_years,
            index=len(current_available_years) - 1
        )

        # Validación de años
        if start_year >= end_year:
            st.error(
                "El Año Final debe ser *mayor* que el Año Inicial para calcular un incremento positivo en el tiempo.")
        else:
            # --- Cálculo del Incremento Porcentual ---

            df_start = df_filtrado_por_departamento[df_filtrado_por_departamento['PERIODO'] == start_year][['DISTRITO', 'GPC_DOM']]
            df_start.rename(columns={'GPC_DOM': 'GPC_Start'}, inplace=True)

            df_end = df_filtrado_por_departamento[df_filtrado_por_departamento['PERIODO'] == end_year][['DISTRITO', 'GPC_DOM']]
            df_end.rename(columns={'GPC_DOM': 'GPC_End'}, inplace=True)

            df_merged = pd.merge(df_start, df_end, on='DISTRITO', how='inner')

            df_merged.replace(0, pd.NA, inplace=True)
            df_merged.dropna(subset=['GPC_Start', 'GPC_End'], inplace=True)

            df_merged['Incremento %'] = (
                (df_merged['GPC_End'] - df_merged['GPC_Start']) / df_merged['GPC_Start']
            ) * 100

            # --- Filtrado y Preparación para el Plot ---

            df_plot = df_merged[['DISTRITO', 'Incremento %', 'GPC_Start', 'GPC_End']].sort_values(
                'Incremento %', ascending=False
            )

            df_plot_top15 = df_plot.head(15).copy()

            df_plot_top15.columns = [
                'Distrito',
                'Incremento Porcentual (%)',
                f'GPC Domiciliaria {start_year} (kg/hab/día)',
                f'GPC Domiciliaria {end_year} (kg/hab/día)'
            ]

            # --- Generación y Despliegue del Gráfico ---
            st.subheader(f"Top 15 Distritos de {departamento_seleccionado} con Mayor Variación de GPC Domiciliaria: {start_year} vs {end_year}")
            st.info(
                f"El gráfico muestra los *15 distritos* de **{departamento_seleccionado}** con la mayor variación porcentual (barras verdes para incremento, rojas para decremento) del GPC Domiciliaria.")

            # Gráfico de barras con Altair
            chart = alt.Chart(df_plot_top15).mark_bar().encode(
                x=alt.X('Distrito:N', title='Distrito', sort='-y'),
                y=alt.Y('Incremento Porcentual (%):Q', title='Incremento GPC Domiciliaria (%)'),
                color=alt.condition(
                    alt.datum['Incremento Porcentual (%)'] > 0,
                    alt.value("#2ecc71"),
                    alt.value("#e74c3c")
                ),
                tooltip=[
                    'Distrito:N',
                    alt.Tooltip('Incremento Porcentual (%):Q', format='.2f'),
                    alt.Tooltip(f'GPC Domiciliaria {start_year} (kg/hab/día):Q', format='.3f'),
                    alt.Tooltip(f'GPC Domiciliaria {end_year} (kg/hab/día):Q', format='.3f'),
                ]
            ).properties(
                title=f"Top 15 de {departamento_seleccionado}: Variación de GPC Domiciliaria ({start_year} a {end_year})"
            ).interactive()

            # Mostrar el gráfico en Streamlit
            st.altair_chart(chart, use_container_width=True)

            st.markdown("---")
            st.caption(f"Nota: Se muestran los 15 distritos de {departamento_seleccionado} con la mayor variación porcentual entre los años seleccionados.")
else:
    st.error("No se pudieron cargar los datos. Verifique que el archivo 'datos_de_entrada.csv' exista y contenga datos.")
