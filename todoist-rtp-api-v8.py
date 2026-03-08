import os
import pandas as pd
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import requests
from typing import Tuple, Set
from xhtml2pdf import pisa

# --- CONFIGURACIÓN ---
load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
API_URL = 'https://api.todoist.com/api/v1' 

if not API_TOKEN:
    print("¡ERROR! La variable TODOIST_API_TOKEN no está configurada.")
    exit()

# --- FUNCIONES DE SELECCIÓN ---

def seleccionar_tipo_de_reporte() -> str:
    print("\n--- 📝 GENERADOR DE REPORTES TODOIST ---")
    print("1. Reporte semanal (Proyectos Raíz)")
    print("2. Reporte por proyecto (Cualquier proyecto)")
    while True:
        opcion = input("Selecciona (1 o 2): ")
        if opcion == "1": return "semanal"
        if opcion == "2": return "proyecto"

def seleccionar_rango_fechas() -> Tuple[date, date]:
    today = datetime.now().date()
    lunes_actual = today - timedelta(days=today.weekday())
    print("\n--- 📅 RANGO DE FECHAS ---")
    print(f"1. Semana Actual ({lunes_actual} - {lunes_actual + timedelta(days=6)})")
    print(f"2. Semana Pasada ({lunes_actual - timedelta(weeks=1)} - {lunes_actual - timedelta(days=1)})")
    print("3. Últimos N días")
    while True:
        opcion = input("Opción (1, 2 o 3): ")
        if opcion == "1": return lunes_actual, lunes_actual + timedelta(days=6)
        if opcion == "2": return lunes_actual - timedelta(weeks=1), lunes_actual - timedelta(days=1)
        if opcion == "3":
            try:
                n = int(input("¿Cuántos días hacia atrás?: "))
                return today - timedelta(days=n - 1), today
            except: print("Número no válido.")

def seleccionar_proyecto_interactivo(df_pys: pd.DataFrame, solo_root: bool) -> Tuple[str, str]:
    if solo_root and 'parent_id' in df_pys.columns:
        df_display = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)
    else:
        df_display = df_pys.reset_index(drop=True)
    
    print(f"\n--- 📋 SELECCIONA EL PROYECTO ---")
    for i, name in enumerate(df_display['name'], 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            idx = int(input("\nNúmero del proyecto: ")) - 1
            if 0 <= idx < len(df_display):
                return df_display.loc[idx, 'name'], df_display.loc[idx, 'id']
        except: print("Selección no válida.")

# --- CONEXIÓN API ---

def get_api_data(endpoint: str, params: dict = None) -> pd.DataFrame:
    try:
        r = requests.get(f"{API_URL}/{endpoint}", headers={'Authorization': f'Bearer {API_TOKEN}'}, params=params)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list): return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ['items', 'results']:
                if key in data: return pd.DataFrame(data[key])
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- PLANTILLA HTML (ESTILO MONOSPACE CON [X] y [ ]) ---

def obtener_html_template(df_a, df_c, proyecto, since, until) -> str:
    total_a = len(df_a)
    total_c = len(df_c)
    total_tareas = total_a + total_c
    porcentaje = round((total_c / total_tareas * 100), 2) if total_tareas > 0 else 0

    html_report = f"""
    <style>
      body {{ font-family: monospace; font-size: 10pt; line-height: 1.4; color: #000; }}
      h1, h2, h3, h4, li, p, ul {{ font-family: monospace; }}
      .project-name-header {{ margin-bottom: 5px; border-bottom: 1px solid #000; padding-bottom: 2px; margin-top: 20px; }}
      .task-list {{ margin-bottom: 15px; list-style-type: none; padding-left: 0; }}
      .task-item {{ margin-bottom: 3px; white-space: pre-wrap; }}
      .section-header {{ font-weight: bold; text-decoration: underline; margin-top: 10px; margin-bottom: 5px; }}
      .project-summary-item {{ font-size: 9.5pt; margin-top: 5px; margin-bottom: 5px; }}
      hr {{ border: 0; border-top: 1px dashed #ccc; margin: 20px 0; }}
    </style>
    <h1>Reporte de tareas: {proyecto}</h1>
    <h2>Periodo de Relevancia: {since.strftime('%y/%m/%d')} - {until.strftime('%y/%m/%d')}</h2>
    <h4 class="project-name-header">Estatus Global: ({total_c}/{total_tareas} tareas - {porcentaje}%)</h4>
    """

    # --- Tareas Completadas ---
    if not df_c.empty:
        html_report += "<h3>Tareas Completadas:</h3>"
        for sect, s_group in df_c.groupby('section_name'):
            html_report += f"<div class='section-header'>Sección: {sect}</div><ul class='task-list'>"
            for _, row in s_group.iterrows():
                fecha_venc = row['due']['date'] if (isinstance(row.get('due'), dict) and row['due']) else 'N/A'
                fecha_fin = row['completed_date'][:10] if 'completed_date' in row else 'N/A'
                html_report += f"<li class='task-item'>[X] {row['content']} (Venc.: {fecha_venc}) (Fin.: {fecha_fin})</li>"
            html_report += "</ul>"

    # --- Tareas Pendientes ---
    if not df_a.empty:
        html_report += "<hr><h3>Tareas Pendientes:</h3>"
        for sect, s_group in df_a.groupby('section_name'):
            html_report += f"<div class='section-header'>Sección: {sect}</div><ul class='task-list'>"
            for _, row in s_group.iterrows():
                fecha_venc = row['due']['date'] if (isinstance(row.get('due'), dict) and row['due']) else 'N/A'
                html_report += f"<li class='task-item'>[ ] {row['content']} (Venc.: {fecha_venc})</li>"
            html_report += "</ul>"

    html_report += f"""
    <hr>
    <h2>Resumen de Tareas Relevantes:</h2>
    <div class="project-summary-item"><strong>Total Tareas Completadas:</strong> {total_c}</div>
    <div class="project-summary-item"><strong>Total Tareas Relevantes:</strong> {total_tareas}</div>
    <div class="project-summary-item"><strong>Porcentaje de Completado:</strong> {porcentaje}%</div>
    """
    return html_report

# --- FLUJO PRINCIPAL ---

def run():
    tipo = seleccionar_tipo_de_reporte()
    since, until = seleccionar_rango_fechas()
    
    df_pys = get_api_data('projects')
    if df_pys.empty:
        print("❌ No se pudieron cargar los proyectos."); return

    nombre_p, id_p = seleccionar_proyecto_interactivo(df_pys, solo_root=(tipo == "semanal"))

    print(f"\n🚀 Generando reportes para '{nombre_p}'...")
    
    df_a = get_api_data('tasks', {'project_id': id_p})
    df_c = get_api_data('tasks/completed/by_completion_date', 
                        {'project_id': id_p, 'since': since.strftime('%Y-%m-%dT00:00:00'), 'until': until.strftime('%Y-%m-%dT23:59:59')})

    # Mapeo de Secciones
    df_sec = get_api_data('sections')
    sec_map = dict(zip(df_sec['id'], df_sec['name'])) if not df_sec.empty else {}
    for df in [df_a, df_c]:
        if not df.empty:
            col = 'section_id' if 'section_id' in df.columns else 'sectionId'
            df['section_name'] = df[col].map(sec_map).fillna('General') if col in df.columns else 'General'

    output_dir = "reports"; os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f"reporte_{nombre_p.replace(' ', '_')}_{timestamp}"

    html_content = obtener_html_template(df_a, df_c, nombre_p, since, until)

    try:
        # PDF
        with open(os.path.join(output_dir, f"{base_name}.pdf"), "wb") as f:
            pisa.CreatePDF(html_content, dest=f)
        # HTML
        with open(os.path.join(output_dir, f"{base_name}.html"), "w", encoding='utf-8') as f:
            f.write(html_content)
        # WhatsApp (TXT)
        with open(os.path.join(output_dir, f"{base_name}_whatsapp.txt"), "w", encoding='utf-8') as f:
            f.write(f"*REPORTE {nombre_p}*\n")
            f.write(f"📅 {since.strftime('%d/%m')} - {until.strftime('%d/%m')}\n\n")
            f.write(f"✅ *COMPLETADAS ({len(df_c)})*\n")
            if not df_c.empty:
                for _, row in df_c.iterrows(): f.write(f"[X] {row['content']}\n")
            else: f.write("Ninguna\n")
            f.write(f"\n⏳ *PENDIENTES ({len(df_a)})*\n")
            if not df_a.empty:
                for _, row in df_a.iterrows(): f.write(f"[ ] {row['content']}\n")
            else: f.write("Ninguna\n")

        print(f"\n✅ Archivos generados con éxito en la carpeta /{output_dir}")
    except PermissionError:
        print("❌ Error: Cierra el archivo si lo tienes abierto antes de ejecutar.")

if __name__ == "__main__":
    run()