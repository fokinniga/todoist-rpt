from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

# --- 1. Configuración ---
API_TOKEN = "TU_API_TOKEN_PERSONAL" # Sustituye con tu token válido
api = TodoistAPI(API_TOKEN)

def fetch_all_tasks_to_list():
    """
    Obtiene todas las tareas del Todoist API y las convierte en una lista de diccionarios.
    """
    all_tasks_data = []
    try:
        # ⚠️ Paso 1: Obtener el objeto ResultsPaginator
        tasks_paginator = api.get_tasks()
        
        # 💡 Paso 2: Llamar al método .all() para obtener la lista completa de objetos Task
        all_tasks_objects = tasks_paginator.all()

        for task_obj in all_tasks_objects:
            # Serializa a JSON y luego a dict para unificar el formato (como en el ejemplo anterior)
            task_dict = json.loads(str(task_obj))
            all_tasks_data.append(task_dict)
            
    except Exception as error:
        # Esto atrapará los errores de la API (como token inválido) o de paginación
        print(f"Error al obtener las tareas: {error}")
        return None
    
    return all_tasks_data

# --- 2. Obtener y Convertir Datos ---
print("Obteniendo tareas de Todoist...")
tasks_list_of_dicts = fetch_all_tasks_to_list()

if tasks_list_of_dicts:
    df_tasks = pd.DataFrame(tasks_list_of_dicts)
    print(f"DataFrame creado con {len(df_tasks)} tareas.")
    print(df_tasks.head())
else:
    print("No se pudieron obtener o no hay tareas para procesar.")