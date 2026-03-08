import os
import pandas as pd
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import requests
from typing import Tuple, Optional, Dict, List, Set
from xhtml2pdf import pisa

# --- CONFIGURACIÓN Y CONEXIÓN ---

load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
if not API_TOKEN:
    print("¡ERROR! La variable de entorno TODOIST_API_TOKEN no está configurada.")
    exit() 

API_URL = 'https://api.todoist.com/api/v1' 

# --- FUNCIONES DE UTILIDAD Y SELECCIÓN ---

def seleccionar_tipo_de_reporte() -> str:
    print("\n--- 📝 Generador de Reportes de Todoist ---")
    print("1. Reporte semanal")
    print("2. Reporte por proyecto")
    while True:
        opcion = input("Selecciona (1 o 2): ")
        if opcion == "1": return "semanal"
        if opcion == "2": return "proyecto"
        print("⚠️ Opción no válida.")

def seleccionar_rango_fechas() -> Tuple[date, date]:
    today = datetime.now().date()
    lunes_actual = today - timedelta(days=today.weekday())
    domingo_actual = lunes_actual + timedelta(days=6)
    lunes_pasado = lunes_actual - timedelta(weeks=1)
    domingo_pasado = domingo_actual - timedelta(weeks=1)

    print("\n--- 📅 Rango de Fechas ---")
    print(f"1. Semana Actual ({lunes_actual} - {domingo_actual})")
    print(f"2. Semana Pasada ({lunes_pasado} - {domingo_pasado})")
    print("3. Últimos N días")

    while True:
        opcion = input("Opción (1, 2 o 3): ")
        if opcion == "1": return lunes_actual, domingo_actual
        if opcion == "2": return lunes_pasado, domingo_pasado
        if opcion == "3":
            try:
                n = int(input("¿Cuántos días?: "))
                return today - timedelta(days=n - 1), today
            except ValueError: print("⚠️ Ingresa un número válido.")

def seleccionar_proyecto(df_pys: pd.DataFrame, solo_root: bool = False) -> str:
    if solo_root and 'parent_id' in df_pys.columns:
        df_display = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)
    else:
        df_display = df_pys.reset_index(drop=True)
    
    print(f"\n--- 📋 Proyectos Disponibles ---")
    for i, name in enumerate(df_display['name'], 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            idx = int(input("\nNúmero del proyecto: ")) - 1
            if 0 <= idx < len(df_display): return df_display.loc[idx, 'name']
        except ValueError: print("⚠️ Ingresa un número.")

# --- CONEXIÓN API ---

def normalizar_respuesta(data) -> pd.DataFrame:
    if isinstance(data, list): return pd.DataFrame(data)
    if isinstance(data, dict):
        for key in ['results', 'items']:
            if key in data: return pd.DataFrame(data[key])
    return pd.DataFrame()

def get_api_data(endpoint: str, params: dict = None) -> pd.DataFrame:
    try:
        r = requests.get(f"{API_URL}/{endpoint}", 
                         headers={'Authorization': f'Bearer {API_TOKEN}'}, 
                         params=params)
        r.raise_for_status()
        return normalizar_respuesta(r.json())
    except Exception as e:
        print(f"Error en {endpoint}: {e}")
        return pd.DataFrame()

# --- FUNCIONES DE GENERACIÓN DE ARCHIVOS ---

def generar_whatsapp_txt(df_a, df_c, proyecto, since, until, path):
    txt = f"*📊 REPORTE: {proyecto}*\n📅 {since.strftime('%d/%m')} - {until.strftime('%d/%m')}\n"
    for titulo, df in [("✅ COMPLETADAS", df_c), ("⏳ PENDIENTES", df_a)]:
        txt += f"\n*{titulo} ({len(df)})*"
        if df.empty: txt += "\n_(Ninguna)_"
        else:
            for _, row in df.iterrows():
                txt += f"\n ▪ {row['content']}"
    with open(path, 'w', encoding='utf-8') as f: f.write(txt)

def generar_csv(df_a, df_c, path):
    df_a, df_c = df_a.copy(), df_c.copy()
    df_a['Estado'], df_c['Estado'] = 'Activa', 'Completada'
    combined = pd.concat([df_a, df_c], ignore_index=True)
    cols = {'Estado': 'Estado', 'project_name': 'Proyecto', 'section_name': 'Sección', 'content': 'Actividad'}
    combined = combined[[c for c in cols.keys() if c in combined.columns]].rename(columns=cols)
    combined.to_csv(path, index=False, encoding='utf-8-sig')

def obtener_html_template(df_a, df_c, proyecto, since, until) -> str:
    mapeo_a = {'content': 'Actividad', 'due_date': 'Vencimiento'}
    mapeo_c = {'content': 'Actividad', 'completed_date': 'Completado'}
    
    def tabla_html(df, mapeo):
        if df.empty: return "<p style='color: #666;'>Sin registros.</p>"
        html = ""
        for proj, p_group in df.groupby('project_name'):
            html += f"<div class='project-header'>📂 {proj}</div>"
            for sect, s_group in p_group.groupby('section_name'):
                cols = [c for c in mapeo.keys() if c in s_group.columns]
                html += f"<div class='section-title'>🏷️ {sect}</div>"
                html += s_group[cols].rename(columns=mapeo).to_html(classes='task-table', index=False)
        return html

    return f"""
    <html>
    <head>
        <style>
            @page {{ size: letter; margin: 2cm; }}
            body {{ font-family: Arial, sans-serif; font-size: 11pt; color: #333; }}
            .header {{ text-align: center; border-bottom: 2px solid #dc4c3e; padding-bottom: 10px; }}
            h1 {{ color: #dc4c3e; font-size: 18pt; }}
            h2 {{ background-color: #f2f2f2; border-left: 5px solid #dc4c3e; padding: 5px; font-size: 13pt; margin-top: 20px; }}
            .project-header {{ color: #0056b3; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; }}
            .section-title {{ font-weight: bold; color: #666; font-size: 10pt; margin: 5px 0; }}
            .task-table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
            .task-table th {{ background-color: #f8f9fa; text-align: left; padding: 5px; border-bottom: 1px solid #ccc; font-size: 10pt; }}
            .task-table td {{ padding: 5px; border-bottom: 0.5px solid #eee; font-size: 10pt; }}
            .task-table tr:nth-child(even) {{ background-color: #fafafa; }}
        </style>
    </head>
    <body>
        <div class="header"><h1>Reporte Todoist</h1><p>{proyecto} | {since} - {until}</p></div>
        <h2>✅ Completadas ({len(df_c)})</h2> {tabla_html(df_c, mapeo_c)}
        <div style="page-break-before: always;"></div>
        <h2>⏳ Activas ({len(df_a)})</h2> {tabla_html(df_a, mapeo_a)}
    </body>
    </html>"""

# --- FLUJO PRINCIPAL ---

def run():
    tipo = seleccionar_tipo_de_reporte()
    since, until = seleccionar_rango_fechas()
    df_pys = get_api_data('projects')
    
    if df_pys.empty: return print("❌ Error: No se cargaron proyectos.")
    
    nombre = seleccionar_proyecto(df_pys, solo_root=(tipo=="semanal"))
    root_id = df_pys.loc[df_pys['name'] == nombre, 'id'].item()
    
    print(f"🚀 Extrayendo datos...")
    df_a = get_api_data('tasks', {'project_id': root_id})
    df_c = get_api_data('tasks/completed/by_completion_date', 
                        {'project_id': root_id, 'since': since.strftime('%Y-%m-%dT00:00:00'), 'until': until.strftime('%Y-%m-%dT23:59:59')})

    # Enriquecer datos (Secciones y Proyectos)
    df_sec = get_api_data('sections')
    sec_map = dict(zip(df_sec['id'], df_sec['name'])) if not df_sec.empty else {}
    proj_map = dict(zip(df_pys['id'], df_pys['name']))

    for df in [df_a, df_c]:
        if not df.empty:
            df['project_name'] = df['project_id'].map(proj_map) if 'project_id' in df.columns else nombre
            s_col = 'section_id' if 'section_id' in df.columns else 'sectionId'
            df['section_name'] = df[s_col].map(sec_map).fillna('General') if s_col in df.columns else 'General'

    # Guardar Reportes
    output_dir = "reports"; os.makedirs(output_dir, exist_ok=True)
    base = f"reporte_{nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
    
    html_content = obtener_html_template(df_a, df_c, nombre, since, until)
    
    # PDF
    with open(os.path.join(output_dir, f"{base}.pdf"), "wb") as f: pisa.CreatePDF(html_content, dest=f)
    # HTML
    with open(os.path.join(output_dir, f"{base}.html"), "w", encoding='utf-8') as f: f.write(html_content)
    # WhatsApp (TXT)
    generar_whatsapp_txt(df_a, df_c, nombre, since, until, os.path.join(output_dir, f"{base}_whatsapp.txt"))
    # CSV
    generar_csv(df_a, df_c, os.path.join(output_dir, f"{base}.csv"))

    print(f"\n✅ ¡Listo! Archivos generados en /{output_dir}:")
    print(f"- PDF, HTML, CSV y WhatsApp TXT")

if __name__ == "__main__": run()