import os
import pandas as pd
import json
from datetime import datetime, timedelta
from todoist_api_python.api import TodoistAPI
from dotenv import load_dotenv

# --- CONFIGURACIÓN Y CONEXIÓN ---

# Carga la variable de entorno desde el archivo .env
load_dotenv() 
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d"

if not API_TOKEN:
    # Este mensaje se verá si la variable no está en .env o en el entorno de Cloud Run
    print("❌ ERROR: La variable TODOIST_API_TOKEN no está definida. Por favor, revisa el archivo .env.")
    exit()

api = TodoistAPI(API_TOKEN)


# --- FUNCIONES DE OBTENCIÓN DE DATOS (Optimizadas y Robustas) ---

def to_dict_list(paginator):
    """
    Convierte el ResultsPaginator a una lista plana de diccionarios, 
    manejando las diferentes estructuras de los objetos de la API.
    """
    data_list = []
    # Iteramos directamente sobre el Paginator
    for item in paginator:
        # Si item es una lista de objetos (patrón Iterator[list[T]]), iteramos otra vez
        if isinstance(item, list):
            for sub_item in item:
                try:
                    # Extracción simple para las tareas/proyectos que no requieren todo el JSON
                    # Para simplificar, usamos la serialización/deserialización para obtener todos los campos de la Tarea
                    data_list.append(json.loads(str(sub_item)))
                except json.JSONDecodeError:
                    continue
        else:
            # Si item es un objeto individual (patrón de iteración simple), lo procesamos
            try:
                data_list.append(json.loads(str(item)))
            except json.JSONDecodeError:
                continue
    return data_list

def fetch_all_data(api):
    """Obtiene y limpia Proyectos, Secciones y Tareas de la API."""
    try:
        print("1. Obteniendo datos de Proyectos, Secciones y Tareas...")
        
        # 1.1 Proyectos
        projects_list = to_dict_list(api.get_projects())
        df_projects = pd.DataFrame(projects_list)[['id', 'name']]
        df_projects.rename(columns={'name': 'project_name', 'id': 'project_id'}, inplace=True)
        
        # 1.2 Secciones (Extrayendo el crucial project_id)
        sections_list = to_dict_list(api.get_sections())
        sections_data = []
        for section_dict in sections_list:
             sections_data.append({
                'section_id': section_dict['id'],
                'section_name': section_dict['name'],
                'project_id': section_dict.get('project_id') 
            })
        df_sections = pd.DataFrame(sections_data)
        
        # 1.3 Tareas
        tasks_list = to_dict_list(api.get_tasks())
        df_tasks = pd.DataFrame(tasks_list)
        
        print(f"   -> Tareas obtenidas: {len(df_tasks)}")
        
        return df_tasks, df_projects, df_sections
        
    except Exception as e:
        print(f"❌ Error crítico al obtener datos iniciales: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


# --- LÓGICA DE FECHAS Y FILTRADO ---

def get_week_range(use_previous_week):
    """Calcula el rango de la semana (Lunes a Domingo) para el filtrado."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calcular el Lunes de la semana de referencia (Lunes=0)
    start_of_week = today - timedelta(days=today.weekday())
    
    if use_previous_week:
        start_of_week -= timedelta(weeks=1)
        
    monday = start_of_week
    # Establecer el límite del Domingo al final del día
    sunday = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    
    # Rango de la semana siguiente (para tareas pendientes)
    monday_next_week = start_of_week + timedelta(weeks=1)
    sunday_next_week = monday_next_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    return monday, sunday, monday_next_week, sunday_next_week

def process_and_filter_report(df_tasks, df_projects, df_sections):
    """Procesa, une y filtra las tareas para el reporte semanal."""

    # 1. SELECCIÓN DE SEMANA (Usando input() nativo de Python)
    week_selection = input('¿Reporte para la *semana actual* (1) o la *semana anterior* (2)? (1/2): ')
    use_previous_week = week_selection.strip() == '2'
    
    monday, sunday, monday_next_week, sunday_next_week = get_week_range(use_previous_week)

    print(f"\n   -> Filtrando por completadas entre {monday.strftime('%Y-%m-%d')} y {sunday.strftime('%Y-%m-%d')}")
    print(f"   -> Y pendientes hasta {sunday_next_week.strftime('%Y-%m-%d')}")


    # 2. PREPARACIÓN Y CONVERSIÓN DE FECHAS
    df_tasks['completed_at'] = pd.to_datetime(df_tasks['completed_at'], errors='coerce', utc=True)
    
    # Extraer la fecha de vencimiento (due date) del diccionario 'due' de Todoist
    df_tasks['due_date'] = df_tasks['due'].apply(
        lambda x: x.get('date') if isinstance(x, dict) and x else None
    )
    df_tasks['due_date'] = pd.to_datetime(df_tasks['due_date'], errors='coerce')


    # 3. LÓGICA DE FILTRADO
    
    # Criterio A: Tareas completadas DENTRO de la semana seleccionada
    completed_this_week = (df_tasks['completed_at'] >= monday) & (df_tasks['completed_at'] <= sunday)

    # Criterio B: Tareas activas (no completadas) que vencen en la semana seleccionada o la siguiente
    is_active = df_tasks['completed_at'].isna()
    # Usamos .date() en la comparación de fechas porque 'due_date' es solo la fecha (día)
    due_this_week_or_next = (df_tasks['due_date'] >= monday.date()) & (df_tasks['due_date'] <= sunday_next_week.date())


    # Filtro Final (OR): A ó B
    relevant_tasks_filter = completed_this_week | (is_active & due_this_week_or_next)

    df_filtered_tasks = df_tasks[relevant_tasks_filter].copy()


    # 4. UNIÓN DE DATOS (Merge)
    
    print("3. Uniendo tareas filtradas con nombres de Proyecto/Sección...")
    
    # 4.1 Unir Tareas con Proyectos por 'project_id'
    df_report = df_filtered_tasks.merge(
        df_projects, 
        on='project_id', 
        how='left'
    )

    # 4.2 Unir Tareas con Secciones por 'section_id'
    df_report = df_report.merge(
        df_sections[['section_id', 'section_name']], # Solo necesitamos estas dos columnas para el merge
        on='section_id', 
        how='left'
    )

    # 4.3 Limpieza Final y Columna de Estado
    df_report['section_name'].fillna('Sin Sección', inplace=True)
    df_report['project_name'].fillna('Sin Proyecto', inplace=True)
    df_report['status'] = df_report['completed_at'].apply(lambda x: 'Completada' if pd.notna(x) else 'Pendiente')

    return df_report

# --- FUNCIÓN PRINCIPAL ---

def generate_todoist_report():
    """Ejecuta el flujo completo de obtención, procesamiento y reporte."""
    
    df_tasks, df_projects, df_sections = fetch_all_data(api)
    
    if df_tasks.empty:
        print("El reporte no se puede generar sin tareas.")
        return

    df_report = process_and_filter_report(df_tasks, df_projects, df_sections)
    
    if df_report.empty:
        print("\nEl filtro semanal no encontró tareas relevantes. No se genera archivo.")
        return

    # --- 4. GENERACIÓN DEL REPORTE FINAL ---
    
    # 4.1 Cálculo de Métricas (Resumen por Proyecto/Sección)
    summary_report = df_report.groupby(['project_name', 'section_name']).agg(
        Total_Tareas=('id', 'count'),
        Completadas=('status', lambda x: (x == 'Completada').sum()),
        Pendientes=('status', lambda x: (x == 'Pendiente').sum())
    ).reset_index()
    
    summary_report['Porcentaje_Completado'] = (summary_report['Completadas'] / summary_report['Total_Tareas']) * 100
    
    # 4.2 Exportación a Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"reporte_todoist_semanal_{timestamp}.xlsx"

    print(f"\n4. Reporte listo. Exportando a {file_name}...")
    
    # Uso de ExcelWriter para crear múltiples pestañas en el mismo archivo
    with pd.ExcelWriter(file_name) as writer:
        summary_report.to_excel(writer, sheet_name='Resumen_Proyectos', index=False)
        df_report[['project_name', 'section_name', 'content', 'status', 'due_date', 'completed_at', 'priority', 'description']].to_excel(writer, sheet_name='Detalle_Tareas', index=False)
        
    print(f"✅ Reporte generado exitosamente en {file_name}.")
    print("\n--- Vista Previa del Resumen ---\n", summary_report.to_string())


# Ejecutar el script
if __name__ == "__main__":
    generate_todoist_report()