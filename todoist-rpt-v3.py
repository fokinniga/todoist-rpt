from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

# --- 1. Configuración ---
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d" # Usa tu token válido
api = TodoistAPI(API_TOKEN)

def fetch_all_tasks_to_list():
    """
    Obtiene todas las tareas del Todoist API iterando directamente sobre el Paginator.
    """
    all_tasks_data = []
    try:
        # Paso 1: Obtener el objeto ResultsPaginator
        tasks_paginator = api.get_tasks()
        
        # 💡 Paso 2: Iterar directamente sobre el Paginator. 
        # Cada iteración devuelve un objeto Task.
        for task_obj in tasks_paginator:
            # Serializa a JSON y luego a dict (método que ya estabas usando)
            # Esto es necesario porque el objeto Task de Python no es un dict puro
            task_dict = json.loads(str(task_obj))
            all_tasks_data.append(task_dict)
            
    except Exception as error:
        # Esto atrapará el error de autenticación si el token es inválido
        print(f"Error al obtener las tareas: {error}")
        return None
    
    return all_tasks_data

# --- 2. Obtener y Convertir Datos ---
print("Obteniendo tareas de Todoist...")
tasks_list_of_dicts = fetch_all_tasks_to_list()

if tasks_list_of_dicts:
    df_tasks = pd.DataFrame(tasks_list_of_dicts)
    print(f"\nDataFrame creado con {len(df_tasks)} tareas.")
    print("\n--- Vista Previa ---")
    print(df_tasks.head())
else:
    print("No se pudieron obtener o no hay tareas para procesar.")