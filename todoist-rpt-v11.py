import os
import pandas as pd
import json
from datetime import datetime, timedelta
from todoist_api_python.api import TodoistAPI
from dotenv import load_dotenv 

# --- CONFIGURACIÓN Y CONEXIÓN ---

load_dotenv() 
API_TOKEN = os.getenv("TODOIST_API_TOKEN") 

if not API_TOKEN:
    print("❌ ERROR: La variable TODOIST_API_TOKEN no está definida en el entorno.")
    exit()

api = TodoistAPI(API_TOKEN)

# --- FUNCIONES DE OBTENCIÓN DE DATOS ---

def getTaskList():
    task_data = []
    try:
        # ⚠️ Cambiamos la estructura de doble bucle si solo devuelve objetos, pero
        # la API de Tareas tiende a usar paginación doble, mantendremos la estructura
        taskapi = api.get_tasks()
        
        for tasks_page in taskapi: # tasks_page es una lista de objetos Task
            for task in tasks_page:
                
                # --- EXTRACCIÓN SEGURA DE DATOS ---
                due_date = task.due.date if task.due and hasattr(task.due, 'date') else None
                due_tz = task.due.timezone if task.due and hasattr(task.due, 'timezone') else None
                
                # Para evitar problemas de serialización en el DataFrame, aseguramos que 'due' sea un diccionario
                due_dict = {'date': due_date, 'timezone': due_tz} if task.due else None
                
                task_data.append({
                    'project_id': task.project_id,
                    'section_id': task.section_id,
                    'task_content': task.content,
                    'completed_at': task.completed_at,
                    'description': task.description,
                    'due': due_dict, # Usamos el diccionario 'due' para procesar en Pandas
                    'duration': task.duration
                })
        df_tasks = pd.DataFrame(task_data)
        return df_tasks
    except Exception as e:
        print(f"❌ Error al obtener tareas: {e}")
        return pd.DataFrame()

def getProyectList():
    """Obtiene todos los proyectos y su jerarquía (parent_id) en un DataFrame."""
    project_data = []
    try:
        projects_paginator = api.get_projects()
        for project_page in projects_paginator:
            for project in project_page:
                parent_id_value = None
                if project.parent_id:
                    # 💡 SOLUCIÓN: Usamos hasattr para verificar el atributo 'id'
                    if hasattr(project.parent_id, 'id'):
                        parent_id_value = project.parent_id.id
                    else:
                        parent_id_value = project.parent_id
                        
                project_data.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'parent_id': parent_id_value
                })
        df_projects = pd.DataFrame(project_data)
        df_projects['parent_id'] = df_projects['parent_id'].fillna('ROOT') # Solución Warning Pandas
        return df_projects
    except Exception as e:
        print(f"❌ Error al obtener la lista de proyectos: {e}")
        return pd.DataFrame()

def getSectionList():
    """Obtiene todas las secciones con su project_id en un DataFrame."""
    try:
        # ⚠️ CORRECCIÓN: La API de secciones devuelve un paginador (lista de listas de objetos)
        sections_paginator = api.get_sections()
        sections_data = []
        
        for sections_page in sections_paginator: # sections_page es una lista de objetos Section
            for section in sections_page: # section es el objeto Section individual
                sections_data.append({
                    'section_id': section.id,
                    'section_name': section.name,
                    'project_id': section.project_id # Ya es el ID string
                })
        df_sections = pd.DataFrame(sections_data)
        return df_sections
    except Exception as e:
        print(f"❌ Error al obtener secciones: {e}")
        return pd.DataFrame()

# --- LÓGICA DE FECHAS Y PROCESAMIENTO ---

def get_week_range(use_previous_week):
    """Calcula el rango de la semana (Lunes a Domingo) para el filtrado."""
    # Usamos datetime.now() local (tz-naive) para la comparación
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    start_of_week = today - timedelta(days=today.weekday())
    
    if use_previous_week:
        start_of_week -= timedelta(weeks=1)
        
    monday = start_of_week
    sunday = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    
    monday_next_week = start_of_week + timedelta(weeks=1)
    sunday_next_week = monday_next_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    return monday, sunday, monday_next_week, sunday_next_week

def process_and_filter_report(df_tasks, df_projects, df_sections):
    """Procesa, une y filtra las tareas para el reporte semanal."""

    week_selection = input('¿Reporte para la *semana actual* (1) o la *semana anterior* (2)? (1/2): ')
    use_previous_week = week_selection.strip() == '2'
    
    monday, sunday, monday_next_week, sunday_next_week = get_week_range(use_previous_week)

    print(f"\n   -> Filtrando por completadas entre {monday.strftime('%Y-%m-%d')} y {sunday.strftime('%Y-%m-%d')}")
    
    # 2. PREPARACIÓN Y CONVERSIÓN DE FECHAS
    df_tasks['completed_at'] = pd.to_datetime(df_tasks['completed_at'], errors='coerce', utc=True)
    
    # Extraer la fecha de vencimiento (due date) del diccionario 'due' de la tarea
    # ⚠️ CORRECCIÓN: Usamos la columna 'due' (que ahora es un diccionario)
    df_tasks['due_date_str'] = df_tasks['due'].apply(
        lambda x: x.get('date') if isinstance(x, dict) and x else None
    )
    df_tasks['due_date'] = pd.to_datetime(df_tasks['due_date_str'], errors='coerce')


    # 3. LÓGICA DE FILTRADO
    
    # 💡 La columna completed_at es UTC (tz-aware) y monday/sunday es local (tz-naive).
    # Como la conversión compleja de zona horaria requiere librerías adicionales (pytz),
    # y ya que estás usando 'utc=True' en pd.to_datetime, asumiremos que UTC es suficiente
    # para la comparación, aunque no sea 100% preciso para el tiempo local.
    # Si sigue fallando por TypeError, necesitamos instalar pytz.
    
    completed_this_week = (df_tasks['completed_at'] >= monday) & (df_tasks['completed_at'] <= sunday)
    is_active = df_tasks['completed_at'].isna()
    
    # Usamos .dt.date para acceder a la parte de la fecha para la comparación
    due_this_week_or_next = (df_tasks['due_date'].dt.date >= monday.date()) & (df_tasks['due_date'].dt.date <= sunday_next_week.date())

    relevant_tasks_filter = completed_this_week | (is_active & due_this_week_or_next)
    df_filtered_tasks = df_tasks[relevant_tasks_filter].copy()

    # 4. UNIÓN DE DATOS (Merge)
    print("3. Uniendo tareas filtradas con nombres de Proyecto/Sección...")
    df_report = df_filtered_tasks.merge(df_projects, on='project_id', how='left')
    df_report = df_report.merge(df_sections[['section_id', 'section_name']], on='section_id', how='left')

    # Limpieza Final
    df_report['section_name'].fillna('Sin Sección', inplace=True)
    df_report['project_name'].fillna('Sin Proyecto', inplace=True)
    df_report['status'] = df_report['completed_at'].apply(lambda x: 'Completada' if pd.notna(x) else 'Pendiente')

    return df_report

# --- FUNCIÓN PRINCIPAL ---

def generate_todoist_report():
    """Ejecuta el flujo completo de obtención, procesamiento y reporte."""
    
    print("Iniciando generación de reporte Todoist...")
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Obtener los DataFrames base
    df_projects = getProyectList()
    df_sections = getSectionList()
    df_tasks = getTaskList()
    
    # ⚠️ Exportación CSV (corregida para usar el timestamp seguro)
    csv_name = f"tareas_todoist_detalle-{current_datetime}.csv"
    df_tasks.to_csv(csv_name, index=False)
    
    if df_tasks.empty:
        print("\n❌ No se puede generar el reporte. No se encontraron tareas activas.")
        return

    # 1. Procesar, Filtrar y Unir (Merge)
    df_report = process_and_filter_report(df_tasks, df_projects, df_sections)
    
    if df_report.empty:
        print("\nEl filtro semanal no encontró tareas relevantes. No se genera archivo.")
        return

    # 2. GENERACIÓN DEL REPORTE FINAL (Exportación a Excel)
    print("\n4. Calculando resumen y exportando...")

    summary_report = df_report.groupby(['project_name', 'section_name']).agg(
        Total_Tareas=('project_id', 'count'),
        Completadas=('status', lambda x: (x == 'Completada').sum()),
        Pendientes=('status', lambda x: (x == 'Pendiente').sum())
    ).reset_index()
    
    summary_report['Porcentaje_Completado'] = (summary_report['Completadas'] / summary_report['Total_Tareas']) * 100
    
    # Generar nombre del archivo
    file_name = f"reporte_todoist_semanal_{current_datetime}.xlsx"

    # Exportación
    try:
        with pd.ExcelWriter(file_name) as writer:
            summary_report.to_excel(writer, sheet_name='Resumen_Proyectos', index=False)
            df_report[['project_name', 'section_name', 'task_content', 'status', 'due_date', 'completed_at', 'description']].to_excel(writer, sheet_name='Detalle_Tareas', index=False)
            
        print(f"✅ Reporte generado exitosamente en {file_name}.")
    
    except Exception as e:
        print(f"❌ Error al exportar el archivo Excel: {e}")

# Ejecutar el script
if __name__ == "__main__":
    generate_todoist_report()