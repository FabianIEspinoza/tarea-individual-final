import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
import unicodedata
import openpyxl


st.set_page_config(page_title="Dashboard FEspin", layout="wide", page_icon="🗺️")

st.title("🗺️ Inteligencia Logística y Territorial")
st.markdown("Análisis interactivo de la red de distribución y concentración territorial de ventas.")


@st.cache_data
def load_data():
    try:
        df = pd.read_excel('dataset_tarea_ind.xlsx',engine='openpyxl')
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()
        
    columnas_numericas = ['venta_neta', 'lat', 'lng', 'kms_dist', 'lat_cd', 'lng_cd']
    for col in columnas_numericas:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(',', '.').astype(float)
            
    df = df.dropna(subset=['lat', 'lng', 'lat_cd', 'lng_cd', 'comuna'])
    
    def limpiar_comuna(texto):
        if not isinstance(texto, str): return texto
        texto = texto.strip().title()
        texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
        return texto
        
    df['comuna_cruce'] = df['comuna'].apply(limpiar_comuna)
    return df

df = load_data()

if not df.empty:
    st.sidebar.header("Filtros Operativos")
    
    canal_seleccionado = st.sidebar.selectbox("Canal de Venta", ['Todos'] + list(df['canal'].unique()))
    cd_seleccionado = st.sidebar.selectbox("Centro de Distribución", ['Todos'] + list(df['centro_dist'].unique()))
    
    df_filtrado = df.copy()
    if canal_seleccionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['canal'] == canal_seleccionado]
    if cd_seleccionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['centro_dist'] == cd_seleccionado]

    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas Netas Totales", f"${df_filtrado['venta_neta'].sum():,.0f}")
    col2.metric("Volumen de Pedidos", f"{len(df_filtrado):,}")
    col3.metric("Distancia Promedio Despacho", f"{df_filtrado['kms_dist'].mean():.1f} km")
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["Red Logística Interactiva", "Intensidad de Ingresos (HeatMap)", "Desempeño Comunal (Coropleta)"])
    
    with tab1:
        st.subheader("Disposición Espacial de Demanda vs Oferta")
        m_logistica = folium.Map(location=[-33.45, -70.66], zoom_start=10, tiles='CartoDB positron')
        
        cds_unicos = df_filtrado.drop_duplicates(subset=['centro_dist'])
        for _, row in cds_unicos.iterrows():
            folium.Marker(
                location=[row['lat_cd'], row['lng_cd']],
                popup=f"<b>{row['centro_dist']}</b>",
                icon=folium.Icon(color='red', icon='industry', prefix='fa')
            ).add_to(m_logistica)
            
        marker_cluster = MarkerCluster(name="Pedidos").add_to(m_logistica)
        muestra = df_filtrado.sample(n=min(800, len(df_filtrado)), random_state=42)
        
        for _, row in muestra.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lng']],
                radius=4, color='#2b7bba', fill=True,
                popup=f"Canal: {row['canal']} <br> Venta: ${row['venta_neta']}"
            ).add_to(marker_cluster)
        st_folium(m_logistica, width=1200, height=500, returned_objects=[])

    with tab2:
        st.subheader("Mapa de Calor: Concentración de Capital")
        m_heat = folium.Map(location=[-33.45, -70.66], zoom_start=10, tiles='CartoDB dark_matter')
        heat_data = df_filtrado[['lat', 'lng', 'venta_neta']].dropna().values.tolist()
        
        if heat_data:
            HeatMap(heat_data, radius=15, blur=15, gradient={0.4: 'purple', 0.65: 'orange', 1: 'yellow'}).add_to(m_heat)
            
        st_folium(m_heat, width=1200, height=500, returned_objects=[])

    with tab3:
        st.subheader("Penetración Económica por Frontera Administrativa")
        m_coro = folium.Map(location=[-33.45, -70.66], zoom_start=10, tiles='CartoDB positron')
        ventas_comuna = df_filtrado.groupby('comuna_cruce')['venta_neta'].sum().reset_index()
        
        try:
            folium.Choropleth(
                geo_data='comunas_metropolitana-1.geojson',
                name='Ventas por Comuna',
                data=ventas_comuna,
                columns=['comuna_cruce', 'venta_neta'],
                key_on='feature.properties.name',
                fill_color='YlOrRd',
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name='Total Ventas Netas ($)',
                nan_fill_color='white'
            ).add_to(m_coro)
        except Exception as e:
            st.warning("Verifique la disponibilidad del archivo GeoJSON en el directorio de ejecución.")
            
        st_folium(m_coro, width=1200, height=500, returned_objects=[])