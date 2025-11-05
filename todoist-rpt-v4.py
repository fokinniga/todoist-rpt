from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

# --- 1. Configuración ---
# Si este token funciona, lo mantendremos para las pruebas.
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d" 
api = TodoistAPI(API_TOKEN)

def fetch_all_tasks_to_list():
    """
    Obtiene todas las tareas iterando directamente sobre el Paginator
    y convirtiéndolas a una lista de diccionarios.
    """
    all_tasks_data = []
    try:
        # Obtener el objeto ResultsPaginator
        tasks_paginator = api.get_tasks()
        
        # 💡 Solución: Iterar directamente sobre el Paginator. 
        # Si esto funciona, tu token es válido.
        for task_obj in tasks_paginator:
            
            # Convierte el objeto Task a dict. Evitaremos la serialización a string
            # si el SDK ofrece una forma mejor (aunque la conversión a str(obj) es común).
            
            # Para mayor compatibilidad, seguiremos usando la conversión, pero 
            # asumiendo que el token es correcto y que el objeto no está vacío.
            task_dict = json.loads(str(task_obj))
            all_tasks_data.append(task_dict)
            
    except Exception as error:
        print(f"Error al obtener las tareas: {error}")
        return None
    
    return all_tasks_data

# --- 2. Obtener y Convertir a Pandas ---
print("Obteniendo y procesando tareas de Todoist...")
tasks_list_of_dicts = fetch_all_tasks_to_list()

if tasks_list_of_dicts:
    df_tasks = pd.DataFrame(tasks_list_of_dicts)
    
    # 3. Vista Previa del DataFrame
    print(f"\n✅ Éxito: DataFrame creado con {len(df_tasks)} tareas.")
    print("\n--- Vista de Columnas Relevantes ---")
    # Imprimimos las columnas que necesitarás para el reporte:
    print(df_tasks[['id', 'project_id', 'content', 'due', 'completed_at', 'priority']].head())
    
else:
    print("❌ Fallo al obtener tareas. Si este mensaje persiste, verifica la instalación del SDK.")