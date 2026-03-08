import os
import pandas as pd
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import requests
from typing import Tuple
from xhtml2pdf import pisa

# --- CONFIGURACIÓN ---
load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
API_URL = 'https://api.todoist.com/api/v1' 

def seleccionar_tipo_de_reporte() -> str:
    print("\n--- 📝 Generador de Reportes de Todoist ---")
    print("1. Reporte semanal\n2. Reporte por proyecto")
    while True:
        opcion = input("Selecciona (1 o 2): ")
        if opcion in ["1", "2"]: return "semanal" if opcion == "1" else "proyecto"

def seleccionar_rango_fechas() -> Tuple[date, date]:
    today = datetime.now().date()
    lunes_actual = today - timedelta(days=today.weekday())
    print("\n--- 📅 Rango de Fechas ---\n1. Semana Actual\n2. Semana Pasada\n3. Últimos N días")
    while True:
        opcion = input("Opción (1, 2 o 3): ")
        if opcion == "1": return lunes_actual, lunes_actual + timedelta(days=6)
        if opcion == "2": return lunes_actual - timedelta(weeks=1), lunes_actual - timedelta(days=1)
        if opcion == "3":
            try:
                n = int(input("¿Días?: "))
                return today - timedelta(days=n - 1), today
            except: print("Número no válido")

def get_api_data(endpoint: str, params: dict = None) -> pd.DataFrame:
    try:
        r = requests.get(f"{API_URL}/{endpoint}", headers={'Authorization': f'Bearer {API_TOKEN}'}, params=params)
        data = r.json()
        if isinstance(data, list): return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ['results', 'items']:
                if key in data: return pd.DataFrame(data[key])
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- DISEÑO DE LISTA TIPO CHECKLIST (SIN TABLAS) ---
def obtener_html_template(df_a, df_c, proyecto, since, until) -> str:
    
    def construir_lista_html(df, es_completada=False):
        if df.empty:
            return "<p style='color: #999; margin-left: 20px;'>No hay elementos.</p>"
        
        html_segmento = ""
        # Agrupamos por sección
        for sect, s_group in df.groupby('section_name'):
            html_segmento += f"<p style='color: #dc4c3e; font-weight: bold; font-size: 10pt; margin-top: 15px; margin-bottom: 5px; border-bottom: 0.5px solid #eee;'>{sect.upper()}</p>"
            html_segmento += "<ul style='list-style-type: none; margin-left: 0; padding-left: 0;'>"
            
            for _, row in s_group.iterrows():
                # Checkbox y estilo de texto
                box = "&#9745;" if es_completada else "&#9744;"
                estilo_texto = "text-decoration: line-through; color: #888;" if es_completada else "color: #333;"
                
                # Metadata (fecha)
                meta = ""
                if es_completada and 'completed_date' in row:
                    meta = f" <span style='font-size: 8pt; color: #aaa;'>(Ok: {row['completed_date'][:10]})</span>"
                
                html_segmento += f"""
                <li style='margin-bottom: 5px; border-bottom: 0.1px solid #f9f9f9; padding-bottom: 2px;'>
                    <span style='font-size: 14pt; font-family: DejaVu Sans, Arial;'>{box}</span>
                    <span style='{estilo_texto}'>{row['content']}</span>
                    {meta}
                </li>"""
            
            html_segmento += "</ul>"
        return html_segmento

    return f"""
    <html>
    <head>
        <style>
            @page {{ size: letter; margin: 2cm; }}
            body {{ font-family: Arial, sans-serif; font-size: 11pt; }}
            .title {{ text-align: center; font-size: 18pt; font-weight: bold; color: #dc4c3e; }}
            .info {{ text-align: center; font-size: 10pt; color: #666; margin-bottom: 20px; }}
            h2 {{ font-size: 14pt; border-left: 4px solid #333; padding-left: 8px; margin-top: 20px; background-color: #f4f4f4; }}
        </style>
    </head>
    <body>
        <div class="title">Lista de Súper / Actividades</div>
        <div class="info">Proyecto: {proyecto} | {since} al {until}</div>

        <h2>✅ COMPLETADAS ({len(df_c)})</h2>
        {construir_lista_html(df_c, es_completada=True)}

        <div style="page-break-before: always;"></div>

        <h2>⏳ PENDIENTES ({len(df_a)})</h2>
        {construir_lista_html(df_a, es_completada=False)}
    </body>
    </html>
    """

# --- EJECUCIÓN ---
def run():
    tipo = seleccionar_tipo_de_reporte()
    since, until = seleccionar_rango_fechas()
    df_pys = get_api_data('projects')
    if df_pys.empty: return print("❌ Error API")
    
    # Selección de proyecto
    df_display = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True) if tipo == "semanal" else df_pys.reset_index(drop=True)
    for i, name in enumerate(df_display['name'], 1): print(f"{i}. {name}")
    nombre = df_display.loc[int(input("\nNúmero de proyecto: ")) - 1, 'name']
    root_id = df_display.loc[df_display['name'] == nombre, 'id'].item()
    
    print(f"🚀 Generando Checklist Checklist...")
    df_a = get_api_data('tasks', {'project_id': root_id})
    df_c = get_api_data('tasks/completed/by_completion_date', 
                        {'project_id': root_id, 'since': since.strftime('%Y-%m-%dT00:00:00'), 'until': until.strftime('%Y-%m-%dT23:59:59')})

    # Secciones
    df_sec = get_api_data('sections')
    sec_map = dict(zip(df_sec['id'], df_sec['name'])) if not df_sec.empty else {}
    for df in [df_a, df_c]:
        if not df.empty:
            col = 'section_id' if 'section_id' in df.columns else 'sectionId'
            df['section_name'] = df[col].map(sec_map).fillna('General')

    output_dir = "reports"; os.makedirs(output_dir, exist_ok=True)
    base = f"checklist_{nombre.replace(' ', '_')}_{datetime.now().strftime('%H%M%S')}"
    html = obtener_html_template(df_a, df_c, nombre, since, until)

    try:
        with open(os.path.join(output_dir, f"{base}.pdf"), "wb") as f: pisa.CreatePDF(html, dest=f)
        with open(os.path.join(output_dir, f"{base}.html"), "w", encoding='utf-8') as f: f.write(html)
        print(f"✅ Archivo generado: {base}.pdf")
    except PermissionError:
        print("❌ Error: Cierra el archivo antes de ejecutar.")

if __name__ == "__main__": run()