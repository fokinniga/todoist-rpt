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
        taskapi = api.get_tasks()
        for tasks_page in taskapi:
            for task in tasks_page:
                due_dict = {'date': task.due.date, 'timezone': task.due.timezone} if task.due else None
                            
                task_data.append({
                    'project_id': task.project_id,
                    'section_id': task.section_id,
                    'task_content': task.content,
                    'completed_at': task.completed_at,
                    'description': task.description,
                    'due': due_dict,
                    'duration': task.duration
                })
        df_tasks = pd.DataFrame(task_data)
        return df_tasks
    except Exception as e:
        print(f"❌ Error al obtener tareas: {e}")
        return pd.DataFrame()

def getProyectList():
    project_data = []
    try:
        # 1. Obtención de Datos y Creación del DataFrame General
        projects_paginator = api.get_projects()
        for project_page in projects_paginator:
            for project in project_page:
                # Se simplifica la lógica de obtención del parent_id
                parent_id_value = getattr(getattr(project, 'parent_id', None), 'id', project.parent_id)
                
                project_data.append({
                    'project_id': project.id,
                    'project_name': project.name,
                    'parent_id': parent_id_value
                })
        
        df_projects = pd.DataFrame(project_data)
        # 2. Reemplazar valores nulos (NaN) o vacíos por 'ROOT'
        df_projects['parent_id'] = df_projects['parent_id'].fillna('ROOT')
        
        # 3. Filtrar solo los proyectos de nivel superior (ROOT)
        df_root_pys = df_projects[df_projects['parent_id'] == 'ROOT']
        print("\n--- 📋 Proyectos de Nivel Superior (ROOT) ---")
        
        # --- NUEVA LÓGICA DE SELECCIÓN DEL USUARIO ---
        
        # 4. Mostrar opciones y preguntar al usuario
        
        # Se genera un diccionario para mapear la selección numérica al ID del proyecto
        opciones = {}
        print("Seleccione el proyecto 'ROOT' que contiene los reportes:")
        
        # Usamos enumerate para generar una numeración consecutiva (1, 2, 3...)
        for idx, (_, row) in enumerate(df_root_pys.iterrows(), start=1):
            opciones[idx] = row['project_id']
            print(f"{idx}. {row['project_name']} (ID: {row['project_id']})")
        
        # Bucle para capturar la selección
        seleccion_id = None
        while seleccion_id is None:
            try:
                seleccion_num = int(input(f"Ingrese el número del proyecto (1 a {len(opciones)}): "))
                if seleccion_num in opciones:
                    seleccion_id = opciones[seleccion_num]
                    print(f"\n✅ Ha seleccionado el proyecto: **{df_root_pys[df_root_pys['project_id'] == seleccion_id]['project_name'].iloc[0]}**")
                else:
                    print("❌ Número fuera de rango. Intente de nuevo.")
            except (ValueError, IndexError):
                print("❌ Entrada inválida. Por favor, ingrese un número.")

        # --- FILTRADO RECURSIVO DE PROYECTOS (Raíz + Hijos + Nietos...) ---
        
        # Inicializamos la lista de IDs válidos con el ID seleccionado (Raíz)
        ids_validos = [seleccion_id]
        nuevos_ids = [seleccion_id]
        
        # Bucle para encontrar descendientes en profundidad
        while nuevos_ids:
            # Buscamos proyectos cuyo parent_id esté en la lista de nuevos_ids encontrados
            hijos = df_projects[df_projects['parent_id'].isin(nuevos_ids)]['project_id'].tolist()
            
            # Si hay hijos, los agregamos a la lista de válidos y los usamos para buscar la siguiente generación
            if hijos:
                ids_validos.extend(hijos)
                nuevos_ids = hijos
            else:
                nuevos_ids = []
        
        # Filtramos el DataFrame original para quedarnos solo con el árbol del proyecto seleccionado
        df_arbol_proyecto = df_projects[df_projects['project_id'].isin(ids_validos)].copy()
        
        print(f"\n--- 📂 Estructura del Proyecto Seleccionado ({len(df_arbol_proyecto)} proyectos encontrados) ---")
        print(df_arbol_proyecto)
        
        # 6. Devolver el DataFrame Filtrado (Raíz + Descendientes)
        return df_arbol_proyecto 
    
    except Exception as e:
        print(f"❌ Error al obtener y filtrar la lista de proyectos: {e}")
        return pd.DataFrame()

def getSectionList():
    try:
        sections_paginator = api.get_sections()
        sections_data = []
        
        for sections_page in sections_paginator:
            for section in sections_page:
                sections_data.append({
                    'section_id': section.id,
                    'section_name': section.name,
                    'project_id': section.project_id
                })
        df_sections = pd.DataFrame(sections_data)
        return df_sections
    except Exception as e:
        print(f"❌ Error al obtener secciones: {e}")
        return pd.DataFrame()

# --- LÓGICA DE FECHAS Y PROCESAMIENTO ---

def get_week_range(use_previous_week):
    """Calcula el rango de la semana (Lunes a Domingo) usando la hora local (tz-naive)."""
    # Establece la fecha de inicio/fin de la semana como tz-naive
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
    
    # 2.1 Columna completed_at (FECHA Y HORA DE FINALIZACIÓN)
    df_tasks['completed_at'] = pd.to_datetime(df_tasks['completed_at'], errors='coerce', utc=True)
    # 💡 SOLUCIÓN 1: Normalizar a tz-naive para comparar con monday/sunday (tz-naive)
    df_tasks['completed_at_local_naive'] = df_tasks['completed_at'].dt.tz_localize(None)


    # 2.2 Columna due_date (FECHA DE VENCIMIENTO)
    df_tasks['due_date_str'] = df_tasks['due'].apply(
        lambda x: x.get('date') if isinstance(x, dict) and x else None
    )

    df_tasks['due_date'] = pd.to_datetime(
        df_tasks['due_date_str'], 
        errors='coerce', 
        utc=True # Asumimos UTC para parsear si hay formato ISO 
    )
    
    # 💡 SOLUCIÓN 2: Normalizar a tz-naive para eliminar la mezcla y comparar con monday.date()
    df_tasks['due_date'] = df_tasks['due_date'].dt.tz_localize(None)

    # 3. LÓGICA DE FILTRADO
    # ⚠️ Usamos la columna completed_at_local_naive
    completed_this_week = (df_tasks['completed_at_local_naive'] >= monday) & (df_tasks['completed_at_local_naive'] <= sunday)
    is_active = df_tasks['completed_at'].isna()
    
    # Usamos .dt.date para acceder a la parte de la fecha para la comparación
    due_this_week_or_next = (df_tasks['due_date'].dt.date >= monday.date()) & (df_tasks['due_date'].dt.date <= sunday_next_week.date())

    relevant_tasks_filter = completed_this_week | (is_active & due_this_week_or_next)
    df_filtered_tasks = df_tasks[relevant_tasks_filter].copy()

    # --- NUEVO: Filtrar tareas para que SOLO sean del árbol de proyectos seleccionado ---
    # Esto elimina las tareas de otros proyectos (Personal, etc.) que causarían "Sin Proyecto"
    df_filtered_tasks = df_filtered_tasks[df_filtered_tasks['project_id'].isin(df_projects['project_id'])]

    # 4. UNIÓN DE DATOS (Merge)
    print("3. Uniendo tareas filtradas con nombres de Proyecto/Sección...")
    df_report = df_filtered_tasks.merge(df_projects, on='project_id', how='left')
    df_report = df_report.merge(df_sections[['section_id', 'section_name']], on='section_id', how='left')

    # Limpieza Final
    df_report['section_name'].fillna('Sin Sección', inplace=True)
    df_report['project_name'].fillna('Sin Proyecto', inplace=True)
    df_report['status'] = df_report['completed_at'].apply(lambda x: 'Completada' if pd.notna(x) else 'Pendiente')
    
    # Mostrar solo tareas del proyecto ROOT para depuración (opcional)
    # df_root = df_report[df_report['parent_id'] == 'ROOT']
    # print(df_root)

    return df_report

# --- FUNCIÓN PRINCIPAL ---

def generate_todoist_report():
    
    print("Iniciando generación de reporte Todoist...")
    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    df_projects = getProyectList()
    df_sections = getSectionList()
    df_tasks = getTaskList()

    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Exportación CSV (usando el timestamp seguro)
    csv_name = os.path.join(reports_dir, f"tareas_todoist_detalle-{current_datetime}.csv")
    df_tasks.to_csv(csv_name, index=False)
    
    if df_tasks.empty:
        print("\n❌ No se puede generar el reporte. No se encontraron tareas activas.")
        return

    # 1. Procesar, Filtrar y Unir (Merge)
    df_report = process_and_filter_report(df_tasks, df_projects, df_sections)

    print(df_report)
    
    csv_pyrpt = os.path.join(reports_dir, f"proyecto-rpt-{current_datetime}.csv")
    df_report.to_csv(csv_pyrpt, index=False)
    
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
    
    file_name = os.path.join(reports_dir, f"reporte_todoist_semanal_{current_datetime}.xlsx")

    try:
        with pd.ExcelWriter(file_name) as writer:
            summary_report.to_excel(writer, sheet_name='Resumen_Proyectos', index=False)
            df_report[['project_name', 'section_name', 'task_content', 'status', 'due_date', 'completed_at_local_naive', 'description']].to_excel(writer, sheet_name='Detalle_Tareas', index=False)
            
        print(f"✅ Reporte generado exitosamente en {file_name}.")
    
    except Exception as e:
        print(f"❌ Error al exportar el archivo Excel: {e}")

# Ejecutar el script
if __name__ == "__main__":
    generate_todoist_report()