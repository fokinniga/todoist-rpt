from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

# --- 1. Configuración ---
# Coloca tu token real aquí (usando variables de entorno en producción)
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d"
api = TodoistAPI(API_TOKEN)

def fetch_all_tasks_to_list():
    """
    Obtiene todas las tareas del Todoist API, manejando el paginador.
    """
    all_tasks_data = []
    try:
        # get_tasks() devuelve un ResultsPaginator
        tasks_paginator = api.get_tasks()
        
        # Itera sobre el paginador para obtener las tareas de cada página
        for task_page in tasks_paginator:
            for task_obj in task_page:
                # El objeto de tarea es una clase Python. 
                # Debemos convertirlo a un diccionario para una fácil integración con Pandas.
                # Utilizamos .to_dict() o convertimos a JSON si está disponible en el objeto Task.
                
                # Una forma estándar de hacer esto en Python es convertir el objeto a JSON y luego a dict.
                # Como el SDK de Todoist no siempre expone un .to_dict(), serializamos y deserializamos.
                task_dict = json.loads(str(task_obj))
                all_tasks_data.append(task_dict)
                
    except Exception as error:
        print(f"Error al obtener las tareas: {error}")
        return None
    
    return all_tasks_data

# --- 2. Obtener y Convertir Datos ---
print("Obteniendo tareas de Todoist...")
tasks_list_of_dicts = fetch_all_tasks_to_list()

if tasks_list_of_dicts is not None and tasks_list_of_dicts:
    
    # Crea el DataFrame de Pandas
    df_tasks = pd.DataFrame(tasks_list_of_dicts)
    
    # --- 3. Limpieza y Preparación del DataFrame (Crucial para reportes) ---
    
    # Selecciona solo las columnas que necesitas para tu reporte
    df_tasks = df_tasks[[
        'id', 'project_id', 'section_id', 'content', 'description', 
        'due', 'created_at', 'completed_at', 'labels', 'priority'
    ]]
    
    # Convertir fechas (los campos de fecha de Todoist a menudo están en formato ISO 8601 o nulos)
    # Por ejemplo, la columna 'created_at' y 'completed_at'
    df_tasks['created_at'] = pd.to_datetime(df_tasks['created_at'], errors='coerce')
    df_tasks['completed_at'] = pd.to_datetime(df_tasks['completed_at'], errors='coerce')
    
    # Extraer la fecha de vencimiento del diccionario 'due' (si existe)
    df_tasks['due_date'] = df_tasks['due'].apply(
        lambda x: x.get('date') if isinstance(x, dict) and x else None
    )
    df_tasks['due_date'] = pd.to_datetime(df_tasks['due_date'], errors='coerce')
    
    # Agregar una columna de estado
    df_tasks['status'] = df_tasks['completed_at'].apply(
        lambda x: 'Completada' if pd.notna(x) else 'Pendiente'
    )
    
    # --- 4. Análisis Básico (El poder de Pandas) ---
    
    print("\n--- Vista Previa del DataFrame (Primeras 5 filas) ---")
    print(df_tasks.head())
    
    print("\n--- Agrupación por Proyecto (Ejemplo de Reporte) ---")
    
    # Requerirías obtener la lista de proyectos para nombrar los IDs
    # Aquí usamos directamente el ID del proyecto
    reporte_resumen = df_tasks.groupby('project_id').agg(
        total_tareas=('id', 'count'),
        tareas_completadas=('status', lambda x: (x == 'Completada').sum()),
        tareas_pendientes=('status', lambda x: (x == 'Pendiente').sum())
    )
    
    print(reporte_resumen)

    # --- 5. Exportar el Reporte ---
    # Para el reporte final, exportarías a un archivo Excel o CSV
    # reporte_resumen.to_excel('reporte_todoist_resumen.xlsx')
    
else:
    print("No se pudieron obtener o no hay tareas para procesar.")