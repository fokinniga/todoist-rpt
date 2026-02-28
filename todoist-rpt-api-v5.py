import os
import pandas as pd
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import requests
import logging
from typing import Tuple, Optional, Dict, List, Set
from xhtml2pdf import pisa

# --- CONFIGURACIÓN Y CONEXIÓN ---

# --- Cargar Variables de Entorno ---
load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
if not API_TOKEN:
    print("¡ERROR! La variable de entorno TODOIST_API_TOKEN no está configurada.")
    exit() 

# --- Configuración ---
API_URL = 'https://api.todoist.com/api/v1' 


# --- Funciones de Selección y Utilidad ---

def seleccionar_tipo_de_reporte() -> str:
    """Pregunta al usuario qué tipo de reporte de Todoist desea generar."""
    print("--- 📝 Generador de Reportes de Todoist ---")
    print("Por favor, selecciona el tipo de reporte a generar:")
    print("1. **Reporte semanal**")
    print("2. **Reporte por proyecto**")
    
    while True:
        try:
            opcion = input("Ingresa el número de la opción (1 o 2): ")
            opcion = int(opcion)
            
            if opcion == 1:
                return "semanal"
            elif opcion == 2:
                return "proyecto"
            else:
                print("⚠️ Opción no válida. Por favor, ingresa 1 o 2.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")


def seleccionar_rango_fechas() -> Tuple[date, date]:
    """Pregunta al usuario el rango de fechas a reportar. Retorna (since_date, until_date)."""
    today = datetime.now().date()
    lunes_actual = today - timedelta(days=today.weekday())
    domingo_actual = lunes_actual + timedelta(days=6)
    lunes_pasado = lunes_actual - timedelta(weeks=1)
    domingo_pasado = domingo_actual - timedelta(weeks=1)

    print("\n--- 📅 Rango de Fechas ---")
    print(f"1. Semana Actual (Lunes {lunes_actual} - Domingo {domingo_actual})")
    print(f"2. Semana Pasada (Lunes {lunes_pasado} - Domingo {domingo_pasado})")
    print("3. Últimos N días (a partir de hoy)")

    while True:
        opcion = input("Ingresa el número de la opción (1, 2 o 3): ")
        
        try:
            opcion_num = int(opcion)
            
            if opcion_num == 1:
                return lunes_actual, domingo_actual
            
            elif opcion_num == 2:
                return lunes_pasado, domingo_pasado
            
            elif opcion_num == 3:
                while True:
                    try:
                        n_dias = int(input("Ingresa el número de días a reportar (ej. 7): "))
                        if n_dias > 0:
                            since_date = today - timedelta(days=n_dias - 1)
                            until_date = today 
                            return since_date, until_date
                        else:
                            print("⚠️ Debes ingresar un número positivo de días.")
                    except ValueError:
                        print("⚠️ Entrada no válida. Ingresa un número entero.")
            else:
                print("⚠️ Opción no válida. Ingresa 1, 2 o 3.")
        except ValueError:
            print("⚠️ Entrada no válida. Ingresa un número.")


def seleccionar_proyecto_root(df_root_pys: pd.DataFrame) -> str:
    """Muestra los proyectos raíz y le pide al usuario que seleccione uno por número."""
    
    print("\n--- 🌳 Proyectos Raíz Disponibles ---")
    
    proyectos_disponibles = df_root_pys[['name']].copy()
    proyectos_disponibles.index += 1
    print(proyectos_disponibles.to_string(header=False))
    
    max_opcion = len(df_root_pys)
    
    while True:
        try:
            opcion = input(f"\nIngresa el número del proyecto (1 a {max_opcion}) a reportar: ")
            opcion = int(opcion)
            
            if 1 <= opcion <= max_opcion:
                nombre_proyecto = df_root_pys.loc[opcion - 1, 'name']
                return nombre_proyecto
            else:
                print(f"⚠️ Opción no válida. Por favor, ingresa un número entre 1 y {max_opcion}.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")


def seleccionar_cualquier_proyecto(df_pys: pd.DataFrame) -> str:
    """Muestra TODOS los proyectos y le pide al usuario que seleccione uno."""
    print("\n--- 📋 Todos los Proyectos Disponibles ---")
    
    df_temp = df_pys[['name']].copy().reset_index(drop=True)
    df_temp.index += 1
    print(df_temp.to_string(header=False))
    
    max_opcion = len(df_temp)
    
    while True:
        try:
            opcion = input(f"\nIngresa el número del proyecto (1 a {max_opcion}) a reportar: ")
            opcion = int(opcion)
            
            if 1 <= opcion <= max_opcion:
                nombre_proyecto = df_temp.loc[opcion, 'name']
                return nombre_proyecto
            else:
                print(f"⚠️ Opción no válida. Por favor, ingresa un número entre 1 y {max_opcion}.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")


def obtener_subproyectos(df_pys: pd.DataFrame, df_root_pys: pd.DataFrame, nombre_proyecto_raiz: str) -> Tuple[str, pd.DataFrame]:
    """Obtiene el ID del proyecto raíz y un DataFrame con sus subproyectos directos."""
    try:
        id_proyecto_raiz = df_root_pys.loc[df_root_pys['name'] == nombre_proyecto_raiz, 'id'].item()
    except ValueError:
        print(f"Error: No se pudo encontrar el ID del proyecto '{nombre_proyecto_raiz}'.")
        return "", pd.DataFrame()

    print(f"\nID del proyecto raíz: {id_proyecto_raiz}")
    
    df_subproyectos = df_pys[df_pys['parent_id'] == id_proyecto_raiz].copy()
    
    return id_proyecto_raiz, df_subproyectos


def get_all_related_project_ids(df_pys: pd.DataFrame, root_id: str) -> Set[str]:
    """Encuentra recursivamente todos los IDs de subproyectos anidados."""
    all_ids = {root_id}
    
    def find_children(parent_id):
        children = df_pys[df_pys['parent_id'] == parent_id]
        
        for child_id in children['id']:
            if child_id not in all_ids:
                all_ids.add(child_id)
                find_children(child_id)

    find_children(root_id)
    return all_ids


# --- Funciones de Conexión a API ---

def getProyectos() -> pd.DataFrame:
    """Obtiene la lista de proyectos de la cuenta de Todoist."""
    try:
        print("-> Conectando a la API para obtener proyectos...")
        response = requests.get(API_URL + '/projects', headers={'Authorization': f'Bearer {API_TOKEN}'})
        response.raise_for_status()
        answerJson = response.json()
        
        if isinstance(answerJson, list):
            pys_df = pd.DataFrame(answerJson)
        elif isinstance(answerJson, dict) and 'results' in answerJson:
            pys_df = pd.DataFrame(answerJson['results'])
        else:
            print("Formato de respuesta inesperado de la API de Todoist al obtener proyectos.")
            return pd.DataFrame()
            
        print(f"-> Proyectos obtenidos: {len(pys_df)}")
        return pys_df
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la lista de proyectos: {e}")
        return pd.DataFrame()


def get_sections() -> pd.DataFrame:
    """Obtiene la lista de secciones de la cuenta de Todoist."""
    try:
        print("-> Conectando a la API para obtener secciones...")
        response = requests.get(API_URL + '/sections', headers={'Authorization': f'Bearer {API_TOKEN}'})
        response.raise_for_status()
        answerJson = response.json()
        
        if isinstance(answerJson, list):
            sections_df = pd.DataFrame(answerJson)
        elif isinstance(answerJson, dict) and 'results' in answerJson:
            sections_df = pd.DataFrame(answerJson['results'])
        else:
            print("Formato de respuesta inesperado de la API de Todoist al obtener secciones.")
            return pd.DataFrame()
            
        print(f"-> Secciones obtenidas: {len(sections_df)}")
        return sections_df[['id', 'name']]
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la lista de secciones: {e}")
        return pd.DataFrame()


def get_tareas_activas(proyecto_id: str) -> pd.DataFrame:
    """Obtiene las tareas activas para un proyecto específico, manejando la clave 'results'."""
    try:
        response = requests.get(
            API_URL + '/tasks', 
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            params={'project_id': proyecto_id}
        )
        response.raise_for_status()
        answerJson = response.json()
        
        if isinstance(answerJson, dict) and 'results' in answerJson:
            return pd.DataFrame(answerJson['results'])
        elif isinstance(answerJson, list):
            return pd.DataFrame(answerJson)
        else:
            return pd.DataFrame()

    except requests.exceptions.RequestException:
        return pd.DataFrame()


def get_tareas_completadas(proyecto_id: str, since_date: date, until_date: date) -> pd.DataFrame:
    """Obtiene las tareas completadas para un proyecto en un rango de fechas."""
    since_str = since_date.strftime('%Y-%m-%dT00:00:00')
    until_str = until_date.strftime('%Y-%m-%dT23:59:59')
    
    try:
        response = requests.get(
            API_URL + '/tasks/completed/by_completion_date', 
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            params={
                'project_id': proyecto_id,
                'since': since_str,
                'until': until_str
            }
        )
        response.raise_for_status()
        tareas = response.json()
        
        if isinstance(tareas, dict) and 'items' in tareas:
            return pd.DataFrame(tareas['items'])
        elif isinstance(tareas, list):
             return pd.DataFrame(tareas)
        else:
            return pd.DataFrame()

    except requests.exceptions.RequestException:
        return pd.DataFrame()


# --- Lógica de Ejecución por Reporte ---

def run_reporte_semanal():
    """Ejecuta toda la lógica para generar el reporte semanal (solo hijos directos)."""
    print("\n--- 🛠️ Generando reporte semanal... ---")
    
    # 1. Obtener rango de fechas
    since_date, until_date = seleccionar_rango_fechas()
    print(f"\nReporte configurado para el rango: **{since_date}** al **{until_date}**")

    # 2. Obtener proyectos y validar
    df_pys = getProyectos()
    
    if df_pys.empty:
        print("No se pudieron obtener los proyectos o el DataFrame está vacío. Terminando.")
        return
    
    # 3. Seleccionar proyecto raíz
    df_root_pys = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)
    proyecto_seleccionado = seleccionar_proyecto_root(df_root_pys)
    print(f"\n✅ Has seleccionado el proyecto: **{proyecto_seleccionado}**") 
    
    # 4. Obtener ID del proyecto raíz y subproyectos (solo los directos)
    id_proyecto_raiz, df_subproyectos = obtener_subproyectos(df_pys, df_root_pys, proyecto_seleccionado)
    
    if not id_proyecto_raiz:
        return
        
    # 5. Obtener Tareas del Proyecto Raíz
    print("\n--- 📥 Extrayendo Tareas del Proyecto Raíz ---")
    
    df_tareas_activas_raiz = get_tareas_activas(id_proyecto_raiz)
    df_tareas_completadas_raiz = get_tareas_completadas(id_proyecto_raiz, since_date, until_date)
    
    # 6. Obtener Tareas de Subproyectos
    df_tareas_subproyectos_activas = pd.DataFrame()
    df_tareas_subproyectos_completadas = pd.DataFrame()
    
    if not df_subproyectos.empty:
        print("\n--- 📥 Extrayendo Tareas de Subproyectos Directos ---")
        
        for index, row in df_subproyectos.iterrows():
            sub_id = row['id']
            sub_name = row['name']
            print(f"Procesando subproyecto: {sub_name} (ID: {sub_id})")
            
            sub_activas = get_tareas_activas(sub_id)
            if not sub_activas.empty:
                df_tareas_subproyectos_activas = pd.concat([df_tareas_subproyectos_activas, sub_activas], ignore_index=True)
            
            sub_completadas = get_tareas_completadas(sub_id, since_date, until_date)
            if not sub_completadas.empty:
                df_tareas_subproyectos_completadas = pd.concat([df_tareas_subproyectos_completadas, sub_completadas], ignore_index=True)
        
    # 7. Consolidar DataFrames Finales
    df_final_activas = pd.concat([df_tareas_activas_raiz, df_tareas_subproyectos_activas], ignore_index=True)
    df_final_completadas = pd.concat([df_tareas_completadas_raiz, df_tareas_subproyectos_completadas], ignore_index=True)

    # 9. Obtener secciones (para mapeo posterior)
    df_sections = get_sections()
    section_map = dict(zip(df_sections['id'], df_sections['name']))

    # 10. Mapeo de nombres de sección
    if not df_sections.empty:
        if not df_final_activas.empty and 'section_id' in df_final_activas.columns:
            df_final_activas['section_name'] = df_final_activas['section_id'].map(section_map).fillna('Sin Sección')
        
        section_col = 'section_id' if 'section_id' in df_final_completadas.columns else 'sectionId'
        if not df_final_completadas.empty and section_col in df_final_completadas.columns:
            df_final_completadas['section_name'] = df_final_completadas[section_col].map(section_map).fillna('Sin Sección')

    # 11. Generar Archivos
    generar_archivos_reporte(df_final_activas, df_final_completadas, df_pys, proyecto_seleccionado, since_date, until_date)


def run_reporte_por_proyecto():
    """Ejecuta toda la lógica para generar el reporte basado en un proyecto seleccionado (recursivo)."""
    
    # 1. Obtener rango de fechas
    since_date, until_date = seleccionar_rango_fechas()
    print(f"\nReporte configurado para el rango: **{since_date}** al **{until_date}**")

    # 2. Obtener proyectos
    df_pys = getProyectos()
    if df_pys.empty:
        print("No se pudieron obtener los proyectos o el DataFrame está vacío. Terminando.")
        return

    # 3. Obtener secciones (para mapeo posterior)
    df_sections = get_sections()
    section_map = dict(zip(df_sections['id'], df_sections['name']))

    # 4. Seleccionar proyecto (de toda la lista)
    proyecto_seleccionado = seleccionar_cualquier_proyecto(df_pys)
    print(f"\n✅ Has seleccionado el proyecto: **{proyecto_seleccionado}**") 

    # 5. Obtener ID del proyecto raíz
    proyecto_raiz_info = df_pys[df_pys['name'] == proyecto_seleccionado]
    if proyecto_raiz_info.empty:
        print("Error: No se pudo encontrar el ID del proyecto seleccionado.")
        return
        
    id_proyecto_raiz = proyecto_raiz_info.iloc[0]['id']
    
    # 6. Obtener todos los IDs de proyectos relacionados (recursivamente)
    all_project_ids = get_all_related_project_ids(df_pys, id_proyecto_raiz)
    print(f"-> Se reportarán {len(all_project_ids)} proyectos relacionados (incluyendo el inicial).")

    # 7. Inicializar DataFrames para consolidación
    df_final_activas = pd.DataFrame()
    df_final_completadas = pd.DataFrame()
    
    # 8. Iterar y obtener tareas para todos los IDs
    print("\n--- 📥 Extrayendo Tareas de Proyectos Relacionados ---")
    for project_id in all_project_ids:
        project_name = df_pys[df_pys['id'] == project_id]['name'].iloc[0]
        print(f"  Procesando proyecto: {project_name} (ID: {project_id})...")

        activas = get_tareas_activas(project_id)
        if not activas.empty:
            df_final_activas = pd.concat([df_final_activas, activas], ignore_index=True)
        
        completadas = get_tareas_completadas(project_id, since_date, until_date)
        if not completadas.empty:
            df_final_completadas = pd.concat([df_final_completadas, completadas], ignore_index=True)

    # 9. Mapeo de nombres de sección
    if not df_sections.empty:
        if not df_final_activas.empty and 'section_id' in df_final_activas.columns:
            df_final_activas['section_name'] = df_final_activas['section_id'].map(section_map).fillna('Sin Sección')
            df_final_activas = df_final_activas.drop(columns=['section_id'])
        
        section_col = 'section_id' if 'section_id' in df_final_completadas.columns else 'sectionId'
        if not df_final_completadas.empty and section_col in df_final_completadas.columns:
            df_final_completadas['section_name'] = df_final_completadas[section_col].map(section_map).fillna('Sin Sección')
            df_final_completadas = df_final_completadas.drop(columns=[section_col])


    # 10. Mostrar resultados (Resumen del reporte)
    print("\n--- 📊 REPORTE POR PROYECTO FINAL ---")
    print(f"Total Tareas ACTIVAS consolidadas: {len(df_final_activas)}")
    print(f"Total Tareas COMPLETADAS consolidadas: {len(df_final_completadas)}")
    generar_archivos_reporte(df_final_activas, df_final_completadas, df_pys, proyecto_seleccionado, since_date, until_date)
    
def generar_archivos_reporte(df_activas: pd.DataFrame, df_completadas: pd.DataFrame, df_pys: pd.DataFrame, proyecto_seleccionado: str, since_date: date, until_date: date):
    """
    Orquesta la generación de reportes en HTML, PDF, Texto (WhatsApp) y CSV.
    """
    print("\n--- 💾 GUARDANDO REPORTES ---")
    
    # --- 0. Crear carpeta de reportes ---
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)

    # --- 1. Preparar Datos (Enriquecer con Nombres de Proyecto) ---
    project_map = dict(zip(df_pys['id'], df_pys['name']))

    # Activas
    if 'project_id' in df_activas.columns:
        df_activas['project_name'] = df_activas['project_id'].map(project_map).fillna('Desconocido')
    elif not df_activas.empty:
        df_activas['project_name'] = 'Proyecto'

    # Completadas
    project_col_comp = 'project_id' if 'project_id' in df_completadas.columns else 'projectId'
    if project_col_comp in df_completadas.columns:
        df_completadas['project_name'] = df_completadas[project_col_comp].map(project_map).fillna('Desconocido')
    elif not df_completadas.empty:
        df_completadas['project_name'] = 'Proyecto'

    # Asegurar section_name
    if 'section_name' not in df_activas.columns and not df_activas.empty:
        df_activas['section_name'] = 'General'
    if 'section_name' not in df_completadas.columns and not df_completadas.empty:
        df_completadas['section_name'] = 'General'

    # --- 2. Generar Nombres de Archivo ---
    base_name = f"reporte_{proyecto_seleccionado.replace(' ', '_').replace('/', '')}_{datetime.now().strftime('%Y%m%d')}"
    
    # --- 3. Generar HTML ---
    html_content = obtener_contenido_html(df_activas, df_completadas, proyecto_seleccionado, since_date, until_date)
    html_filename = os.path.join(output_dir, f"{base_name}.html")
    try:
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML: {html_filename}")
    except Exception as e:
        print(f"❌ Error HTML: {e}")

    # --- 4. Generar PDF ---
    pdf_filename = os.path.join(output_dir, f"{base_name}.pdf")
    generar_reporte_pdf(html_content, pdf_filename)

    # --- 5. Generar Texto WhatsApp ---
    txt_filename = os.path.join(output_dir, f"{base_name}_whatsapp.txt")
    generar_reporte_whatsapp(df_activas, df_completadas, proyecto_seleccionado, since_date, until_date, txt_filename)

    # --- 6. Generar CSV ---
    csv_filename = os.path.join(output_dir, f"{base_name}.csv")
    generar_reporte_csv(df_activas, df_completadas, csv_filename)


def obtener_contenido_html(df_activas: pd.DataFrame, df_completadas: pd.DataFrame, proyecto_seleccionado: str, since_date: date, until_date: date) -> str:
    """Genera el string HTML del reporte."""
    
    columnas_mostrar_activas = ['content', 'due_date', 'priority']
    columnas_mostrar_completadas = ['content', 'completed_date']
    
    def generar_html_agrupado(df: pd.DataFrame, columnas_mostrar: list) -> str:
        if df.empty:
            return "<p>No hay tareas en esta categoría.</p>"

        html_out = ""
        # Agrupar por Project Name y Section Name
        if 'project_name' not in df.columns: df['project_name'] = 'Desconocido'
        if 'section_name' not in df.columns: df['section_name'] = 'General'

        grouped = df.sort_values(by=['project_name', 'section_name']).groupby('project_name')

        for project_name, project_group in grouped:
            html_out += f"<h3>📂 Proyecto: {project_name}</h3>"
            section_grouped = project_group.groupby('section_name')
            
            for section_name, section_group in section_grouped:
                table_df = section_group.reindex(columns=[col for col in columnas_mostrar if col in section_group.columns])
                table_html = table_df.to_html(classes='table table-sm table-hover', index=False, escape=False)
                
                html_out += f"""
                <div class="section-group">
                    <h4>&nbsp;&nbsp;&nbsp;🏷️ Sección: {section_name} ({len(section_group)} tareas)</h4>
                    <div class="table-responsive" style="margin-left: 20px;">
                        {table_html}
                    </div>
                </div>
                """
        return html_out

    activas_html = generar_html_agrupado(df_activas, columnas_mostrar_activas)
    completadas_html = generar_html_agrupado(df_completadas, columnas_mostrar_completadas)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Reporte: {proyecto_seleccionado}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .header {{ background-color: #f8f9fa; padding: 20px; margin-bottom: 20px; border-bottom: 3px solid #dc4c3e; }}
            h1 {{ color: #dc4c3e; margin: 0; }}
            h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 30px; color: #333; }}
            h3 {{ color: #0056b3; margin-top: 20px; }}
            h4 {{ color: #666; font-size: 1em; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 {proyecto_seleccionado}</h1>
            <p><strong>Fechas:</strong> {since_date.strftime('%d/%m/%Y')} - {until_date.strftime('%d/%m/%Y')}</p>
        </div>
        <h2>✅ Tareas Completadas ({len(df_completadas)})</h2>
        {completadas_html}
        <h2>⏳ Tareas Activas ({len(df_activas)})</h2>
        {activas_html}
    </body>
    </html>
    """

def generar_reporte_pdf(html_content: str, filename: str):
    """Genera un PDF a partir del contenido HTML usando xhtml2pdf."""
    try:
        with open(filename, "wb") as result_file:
            pisa_status = pisa.CreatePDF(html_content, dest=result_file)
        
        if pisa_status.err:
            print(f"⚠️ Error generando PDF: {pisa_status.err}")
        else:
            print(f"✅ PDF: {filename}")
    except Exception as e:
        print(f"❌ Error al guardar PDF: {e}")

def generar_reporte_whatsapp(df_activas: pd.DataFrame, df_completadas: pd.DataFrame, proyecto_seleccionado: str, since_date: date, until_date: date, filename: str):
    """Genera un archivo de texto con formato optimizado para WhatsApp."""
    
    txt = f"*📊 REPORTE: {proyecto_seleccionado}*\n"
    txt += f"📅 {since_date.strftime('%d/%m')} - {until_date.strftime('%d/%m')}\n"
    
    # Completadas
    txt += f"\n*✅ COMPLETADAS ({len(df_completadas)})*"
    if df_completadas.empty:
        txt += "\n_(Ninguna)_"
    else:
        if 'project_name' not in df_completadas.columns: df_completadas['project_name'] = 'General'
        if 'section_name' not in df_completadas.columns: df_completadas['section_name'] = 'General'
        
        for proj, proj_group in df_completadas.groupby('project_name'):
            txt += f"\n\n📂 *{proj}*"
            for sect, sect_group in proj_group.groupby('section_name'):
                if sect != 'General' and sect != 'Sin Sección':
                    txt += f"\n  🏷️ _{sect}_"
                for _, row in sect_group.iterrows():
                    txt += f"\n    ▪ {row['content']}"

    # Activas
    txt += f"\n\n*⏳ PENDIENTES ({len(df_activas)})*"
    if df_activas.empty:
        txt += "\n_(Ninguna)_"
    else:
        if 'project_name' not in df_activas.columns: df_activas['project_name'] = 'General'
        if 'section_name' not in df_activas.columns: df_activas['section_name'] = 'General'
        
        for proj, proj_group in df_activas.groupby('project_name'):
            txt += f"\n\n📂 *{proj}*"
            for sect, sect_group in proj_group.groupby('section_name'):
                if sect != 'General' and sect != 'Sin Sección':
                    txt += f"\n  🏷️ _{sect}_"
                for _, row in sect_group.iterrows():
                    due_str = ""
                    if 'due' in row and isinstance(row['due'], dict) and 'date' in row['due']:
                        due_str = f" (📅 {row['due']['date']})"
                    elif 'due_date' in row and row['due_date']:
                        due_str = f" (📅 {row['due_date']})"
                    
                    txt += f"\n    ▫ {row['content']}{due_str}"

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f"✅ WhatsApp (TXT): {filename}")
    except Exception as e:
        print(f"❌ Error TXT: {e}")

def generar_reporte_csv(df_activas: pd.DataFrame, df_completadas: pd.DataFrame, filename: str):
    """Genera un archivo CSV consolidado con las tareas activas y completadas."""
    try:
        # Preparar copias para no afectar los originales
        df_a = df_activas.copy()
        df_c = df_completadas.copy()

        # Agregar columna de estado
        df_a['Estado'] = 'Activa'
        df_c['Estado'] = 'Completada'

        # Normalizar columnas de fecha
        if 'due_date' in df_a.columns:
            df_a['Fecha'] = df_a['due_date']
        elif 'due' in df_a.columns:
            df_a['Fecha'] = df_a['due'].apply(lambda x: x.get('date') if isinstance(x, dict) else None)
        else:
            df_a['Fecha'] = None

        if 'completed_date' in df_c.columns:
            df_c['Fecha'] = df_c['completed_date']
        else:
            df_c['Fecha'] = None

        # Seleccionar y renombrar columnas comunes
        cols_to_keep = {
            'Estado': 'Estado',
            'project_name': 'Proyecto',
            'section_name': 'Sección',
            'content': 'Tarea',
            'Fecha': 'Fecha',
            'priority': 'Prioridad'
        }

        # Filtrar columnas existentes
        df_a_final = df_a[[c for c in cols_to_keep.keys() if c in df_a.columns]]
        df_c_final = df_c[[c for c in cols_to_keep.keys() if c in df_c.columns]]

        # Combinar
        df_combined = pd.concat([df_a_final, df_c_final], ignore_index=True)
        
        # Renombrar para el CSV final
        df_combined = df_combined.rename(columns=cols_to_keep)

        # Guardar a CSV
        df_combined.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"✅ CSV: {filename}")
        
    except Exception as e:
        print(f"❌ Error CSV: {e}")

# --- Ejecución Principal ---

if __name__ == "__main__":
    tipo_reporte = seleccionar_tipo_de_reporte()

    if tipo_reporte == "semanal":
        run_reporte_semanal() 
        
    elif tipo_reporte == "proyecto":
        run_reporte_por_proyecto()