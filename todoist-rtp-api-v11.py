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
    print("3. Reporte solo tareas activas (Proyectos Raíz)")
    print("4. Reporte solo tareas activas (Cualquier proyecto)")
    while True:
        opcion = input("Selecciona (1, 2, 3 o 4): ")
        if opcion == "1": return "semanal"
        if opcion == "2": return "proyecto"
        if opcion == "3": return "activas_raiz"
        if opcion == "4": return "activas_proyecto"

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

def seleccionar_incluir_comentarios() -> bool:
    print("\n--- 💬 COMENTARIOS ---")
    while True:
        opcion = input("¿Deseas incluir los comentarios de las tareas en el reporte? (s/n): ").strip().lower()
        if opcion in ['s', 'si', 'sí']:
            return True
        if opcion in ['n', 'no']:
            return False
        print("Opción no válida. Ingresa 's' o 'n'.")

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
    except Exception as e:
        print(f"❌ Error al consultar la API ({endpoint}): {e}")
        if 'r' in locals() and hasattr(r, 'text'):
            print(f"Detalle: {r.text}")
        return pd.DataFrame()

# --- FUNCION AUXILIAR FECHA DE VENCIMIENTO Y ORDENAMIENTO ---

def obtener_fecha_vencimiento(row) -> str:
    due = row.get('due') if isinstance(row, dict) else row.get('due') if 'due' in row else None
    if isinstance(due, dict) and due and 'date' in due and due['date']:
        return str(due['date'])[:10]
    if isinstance(row, dict):
        if 'due_date' in row and row['due_date'] and str(row['due_date']).strip() and str(row['due_date']) != 'nan':
            return str(row['due_date'])[:10]
    else:
        if 'due_date' in row and row['due_date'] and str(row['due_date']).strip() and str(row['due_date']) != 'nan':
            return str(row['due_date'])[:10]
    return 'N/A'

def obtener_sort_key_completadas(row) -> tuple:
    c_date = ''
    comp = row.get('completed_date')
    if comp and str(comp) != 'nan':
        c_date = str(comp)[:10]
    if c_date:
        return (0, c_date, str(row.get('content', '')))
    v_date = obtener_fecha_vencimiento(row)
    if v_date != 'N/A':
        return (0, v_date, str(row.get('content', '')))
    return (1, '9999-99-99', str(row.get('content', '')))

def obtener_sort_key_pendientes(row) -> tuple:
    v_date = obtener_fecha_vencimiento(row)
    if v_date != 'N/A':
        return (0, v_date, str(row.get('content', '')))
    return (1, '9999-99-99', str(row.get('content', '')))

# --- PLANTILLA HTML (ESTILO MONOSPACE CON [X] y [ ]) ---

def obtener_html_template(df_a, df_c, proyecto, since, until, tipo) -> str:
    total_a = len(df_a)
    total_c = len(df_c)
    total_tareas = total_a + total_c
    porcentaje = round((total_c / total_tareas * 100), 2) if total_tareas > 0 else 0

    if "activas" in tipo:
        periodo_texto = f"Al día de hoy: {datetime.now().strftime('%y/%m/%d')}"
        estatus_global = f"({total_a} tareas activas)"
    else:
        periodo_texto = f"Periodo de Relevancia: {since.strftime('%y/%m/%d')} - {until.strftime('%y/%m/%d')}"
        estatus_global = f"({total_c}/{total_tareas} tareas - {porcentaje}%)"

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
    <h2>{periodo_texto}</h2>
    <h4 class="project-name-header">Estatus Global: {estatus_global}</h4>
    """

    # --- Tareas Completadas ---
    if not df_c.empty:
        html_report += "<h3>Tareas Completadas:</h3>"
        # CAMBIO: sort=True para orden alfabético
        for proj, p_group in df_c.groupby('project_name', sort=True):
            html_report += f"<h4 style='color: #0056b3; margin-top: 15px;'>📂 Proyecto: {proj}</h4>"
            # CAMBIO: sort=True para orden alfabético
            for sect, s_group in p_group.groupby('section_name', sort=True):
                html_report += f"<div class='section-header'>&nbsp;&nbsp;🏷️ Sección: {sect}</div><ul class='task-list' style='margin-left: 20px;'>"
                s_group_sorted = sorted(s_group.to_dict('records'), key=obtener_sort_key_completadas)
                for row in s_group_sorted:
                    fecha_venc = obtener_fecha_vencimiento(row)
                    fecha_fin = str(row['completed_date'])[:10] if ('completed_date' in row and row['completed_date'] and str(row['completed_date']) != 'nan') else 'N/A'
                    desc = row.get('description', '') if 'description' in row else ''
                    comentarios = row.get('comments', []) if 'comments' in row else []
                    desc_text = []
                    if isinstance(desc, str) and desc.strip():
                        desc_text.append(f"Nota: {desc}")
                    if isinstance(comentarios, list) and comentarios:
                        if len(comentarios) == 1:
                            desc_text.append(f"Comentario: {comentarios[0]}")
                        else:
                            desc_text.append("Comentarios:")
                            for c in comentarios:
                                desc_text.append(f"&nbsp;&nbsp;- {c}")
                    elif isinstance(comentarios, str) and comentarios.strip():
                        desc_text.append(f"Comentarios: {comentarios}")
                    desc_html = ""
                    if desc_text:
                        desc_html = "<br>&nbsp;&nbsp;&nbsp;&nbsp;" + "<br>&nbsp;&nbsp;&nbsp;&nbsp;".join(desc_text)
                    html_report += f"<li class='task-item'>[X] {row['content']} (Venc.: {fecha_venc}) (Fin.: {fecha_fin}){desc_html}</li>"
                html_report += "</ul>"

    # --- Tareas Pendientes ---
    if not df_a.empty:
        html_report += "<hr><h3>Tareas Pendientes:</h3>"
        # CAMBIO: sort=True para orden alfabético
        for proj, p_group in df_a.groupby('project_name', sort=True):
            html_report += f"<h4 style='color: #0056b3; margin-top: 15px;'>📂 Proyecto: {proj}</h4>"
            # CAMBIO: sort=True para orden alfabético
            for sect, s_group in p_group.groupby('section_name', sort=True):
                html_report += f"<div class='section-header'>&nbsp;&nbsp;🏷️ Sección: {sect}</div><ul class='task-list' style='margin-left: 20px;'>"
                s_group_sorted = sorted(s_group.to_dict('records'), key=obtener_sort_key_pendientes)
                for row in s_group_sorted:
                    fecha_venc = obtener_fecha_vencimiento(row)
                    desc = row.get('description', '') if 'description' in row else ''
                    comentarios = row.get('comments', []) if 'comments' in row else []
                    desc_text = []
                    if isinstance(desc, str) and desc.strip():
                        desc_text.append(f"Nota: {desc}")
                    if isinstance(comentarios, list) and comentarios:
                        if len(comentarios) == 1:
                            desc_text.append(f"Comentario: {comentarios[0]}")
                        else:
                            desc_text.append("Comentarios:")
                            for c in comentarios:
                                desc_text.append(f"&nbsp;&nbsp;- {c}")
                    elif isinstance(comentarios, str) and comentarios.strip():
                        desc_text.append(f"Comentarios: {comentarios}")
                    desc_html = ""
                    if desc_text:
                        desc_html = "<br>&nbsp;&nbsp;&nbsp;&nbsp;" + "<br>&nbsp;&nbsp;&nbsp;&nbsp;".join(desc_text)
                    html_report += f"<li class='task-item'>[ ] {row['content']} (Venc.: {fecha_venc}){desc_html}</li>"
                html_report += "</ul>"

    html_report += f"""
    <hr>
    <h2>Resumen de Tareas Relevantes:</h2>
    """
    
    if "activas" in tipo:
        html_report += f"""
        <div class="project-summary-item"><strong>Total Tareas Activas:</strong> {total_a}</div>
        """
    else:
        html_report += f"""
        <div class="project-summary-item"><strong>Total Tareas Completadas:</strong> {total_c}</div>
        <div class="project-summary-item"><strong>Total Tareas Relevantes:</strong> {total_tareas}</div>
        <div class="project-summary-item"><strong>Porcentaje de Completado:</strong> {porcentaje}%</div>
        """
        
    return html_report

# --- FLUJO PRINCIPAL ---

def run():
    tipo = seleccionar_tipo_de_reporte()
    incluir_comentarios = seleccionar_incluir_comentarios()
    if "activas" not in tipo:
        since, until = seleccionar_rango_fechas()
    else:
        since = until = datetime.now().date()
    
    df_pys = get_api_data('projects')
    if df_pys.empty:
        print("❌ No se pudieron cargar los proyectos."); return

    nombre_p, id_p = seleccionar_proyecto_interactivo(df_pys, solo_root=(tipo in ["semanal", "activas_raiz"]))

    # Obtener IDs de proyectos relacionados (subproyectos)
    project_ids = {id_p}
    if 'parent_id' in df_pys.columns:
        if tipo in ["semanal", "activas_raiz"]:
            # Hijos directos (como en v5)
            hijos = df_pys[df_pys['parent_id'] == id_p]['id'].tolist()
            project_ids.update(hijos)
        else:
            # Todos los descendientes (recursivo)
            def get_all_descendants(parent_id):
                desc = df_pys[df_pys['parent_id'] == parent_id]['id'].tolist()
                for d_id in desc:
                    if d_id not in project_ids:
                        project_ids.add(d_id)
                        get_all_descendants(d_id)
            get_all_descendants(id_p)

    print(f"\n🚀 Generando reportes para '{nombre_p}' ({len(project_ids)} proyectos)...")
    
    df_a = pd.DataFrame()
    df_c = pd.DataFrame()
    
    for p_id in project_ids:
        a = get_api_data('tasks', {'project_id': p_id})
        if "activas" not in tipo:
            c = get_api_data('tasks/completed/by_completion_date', 
                             {'project_id': p_id, 'since': since.strftime('%Y-%m-%dT00:00:00'), 'until': until.strftime('%Y-%m-%dT23:59:59')})
            if not c.empty: df_c = pd.concat([df_c, c], ignore_index=True)
            
        if not a.empty: df_a = pd.concat([df_a, a], ignore_index=True)

    if incluir_comentarios:
        print("\n⏳ Obteniendo comentarios de las tareas...")
        def fetch_comments_for_df(df):
            if df.empty: return df
            comments_col = []
            id_col = 'id' if 'id' in df.columns else 'task_id' if 'task_id' in df.columns else None
            if not id_col:
                df['comments'] = ''
                return df
            for _, row in df.iterrows():
                comms = get_api_data('comments', {'task_id': row[id_col]})
                if not comms.empty and 'content' in comms.columns:
                    c_texts = comms['content'].dropna().tolist()
                    comments_col.append([str(ct).replace('\n', ' ') for ct in c_texts if str(ct).strip()])
                else:
                    comments_col.append([])
            df['comments'] = comments_col
            return df

        df_a = fetch_comments_for_df(df_a)
        df_c = fetch_comments_for_df(df_c)

    output_dir = "reports"; os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = f"reporte_{nombre_p.replace(' ', '_')}_{timestamp}"
    # Mapeo de Secciones
    df_sec = get_api_data('sections')
    sec_map = dict(zip(df_sec['id'], df_sec['name'])) if not df_sec.empty else {}
    for df in [df_a, df_c]:
        if not df.empty:
            col = 'section_id' if 'section_id' in df.columns else 'sectionId'
            df['section_name'] = df[col].map(sec_map).fillna('General') if col in df.columns else 'General'

    # Enriquecer con nombres de proyecto
    p_map = dict(zip(df_pys['id'], df_pys['name']))
    if not df_a.empty:
        df_a['project_name'] = df_a['project_id'].map(p_map).fillna('Desconocido')
    if not df_c.empty:
        p_col_c = 'project_id' if 'project_id' in df_c.columns else 'projectId'
        df_c['project_name'] = df_c[p_col_c].map(p_map).fillna('Desconocido')

    html_content = obtener_html_template(df_a, df_c, nombre_p, since, until, tipo)

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
            if "activas" in tipo:
                f.write(f"📅 Al día de hoy: {datetime.now().strftime('%d/%m/%Y')}\n\n")
            else:
                f.write(f"📅 {since.strftime('%d/%m')} - {until.strftime('%d/%m')}\n\n")
            
            if "activas" not in tipo:
                # Completadas
                f.write(f"✅ *COMPLETADAS ({len(df_c)})*\n")
                if not df_c.empty:
                    # CAMBIO: sort=True para orden alfabético
                    for proj, p_group in df_c.groupby('project_name', sort=True):
                        f.write(f"\n📂 *{proj}*")
                        # CAMBIO: sort=True para orden alfabético
                        for sect, s_group in p_group.groupby('section_name', sort=True):
                            if sect != 'General': f.write(f"\n  🏷️ _{sect}_")
                            s_group_sorted = sorted(s_group.to_dict('records'), key=obtener_sort_key_completadas)
                            for row in s_group_sorted:
                                fecha_venc = obtener_fecha_vencimiento(row)
                                fecha_fin = str(row['completed_date'])[:10] if ('completed_date' in row and row['completed_date'] and str(row['completed_date']) != 'nan') else 'N/A'
                                f.write(f"\n    [X] {row['content']} (Venc.: {fecha_venc}) (Fin.: {fecha_fin})")
                                desc = row.get('description', '') if 'description' in row else ''
                                if isinstance(desc, str) and desc.strip():
                                    f.write(f"\n        Nota: {desc.replace('\n', ' ')[:150]}")
                                comentarios = row.get('comments', []) if 'comments' in row else []
                                if isinstance(comentarios, list) and comentarios:
                                    if len(comentarios) == 1:
                                        f.write(f"\n        Comentario: {comentarios[0]}")
                                    else:
                                        f.write(f"\n        Comentarios:")
                                        for c in comentarios:
                                            f.write(f"\n          - {c}")
                                elif isinstance(comentarios, str) and comentarios.strip():
                                    f.write(f"\n        Comentarios: {comentarios.replace('\n', ' ')}")
                    f.write("\n")
                else:
                    f.write("Ninguna\n")
            
            # Pendientes
            f.write(f"\n⏳ *PENDIENTES ({len(df_a)})*\n")
            if not df_a.empty:
                # CAMBIO: sort=True para orden alfabético
                for proj, p_group in df_a.groupby('project_name', sort=True):
                    f.write(f"\n📂 *{proj}*")
                    # CAMBIO: sort=True para orden alfabético
                    for sect, s_group in p_group.groupby('section_name', sort=True):
                        if sect != 'General': f.write(f"\n  🏷️ _{sect}_")
                        s_group_sorted = sorted(s_group.to_dict('records'), key=obtener_sort_key_pendientes)
                        for row in s_group_sorted:
                            fecha_venc = obtener_fecha_vencimiento(row)
                            f.write(f"\n    [ ] {row['content']} (Venc.: {fecha_venc})")
                            desc = row.get('description', '') if 'description' in row else ''
                            if isinstance(desc, str) and desc.strip():
                                f.write(f"\n        Nota: {desc.replace('\n', ' ')[:150]}")
                            comentarios = row.get('comments', []) if 'comments' in row else []
                            if isinstance(comentarios, list) and comentarios:
                                if len(comentarios) == 1:
                                    f.write(f"\n        Comentario: {comentarios[0]}")
                                else:
                                    f.write(f"\n        Comentarios:")
                                    for c in comentarios:
                                        f.write(f"\n          - {c}")
                            elif isinstance(comentarios, str) and comentarios.strip():
                                f.write(f"\n        Comentarios: {comentarios.replace('\n', ' ')}")
                f.write("\n")
            else:
                f.write("Ninguna\n")

        print(f"\n✅ Archivos generados con éxito en la carpeta /{output_dir}")
    except PermissionError:
        print("❌ Error: Cierra el archivo si lo tienes abierto antes de ejecutar.")

if __name__ == "__main__":
    run()
