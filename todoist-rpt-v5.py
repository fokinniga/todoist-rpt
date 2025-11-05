from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

# --- Configuración ---
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d" 
api = TodoistAPI(API_TOKEN)

# Función Auxiliar para la conversión
def to_dict_list(paginator):
    """Convierte el ResultsPaginator a una lista plana de diccionarios."""
    data_list = []
    for item in paginator:
        try:
            # Usamos json.loads(str(item)) para convertir el objeto de la API a dict
            data_list.append(json.loads(str(item)))
        except json.JSONDecodeError as e:
            print(f"Error de serialización: {e}")
            continue
    return data_list

# --- PASO 1: Obtener TODOS los datos de referencia (SOLO 3 LLAMADAS A LA API) ---
print("1. Obteniendo Proyectos, Secciones y Tareas (3 llamadas total)...")
try:
    # Obtener Proyectos y crear el DataFrame de referencia
    projects_list = to_dict_list(api.get_projects(limit=None))
    df_projects = pd.DataFrame(projects_list)[['id', 'name']]
    df_projects.rename(columns={'name': 'project_name'}, inplace=True)

    # Obtener Secciones y crear el DataFrame de referencia
    sections_list = to_dict_list(api.get_sections(limit=None))
    df_sections = pd.DataFrame(sections_list)[['id', 'name']]
    df_sections.rename(columns={'name': 'section_name'}, inplace=True)

    # Obtener Tareas y crear el DataFrame principal
    tasks_list = to_dict_list(api.get_tasks())
    df_tasks = pd.DataFrame(tasks_list)

except Exception as e:
    print(f"❌ ERROR FATAL al obtener datos iniciales (Token/Conexión): {e}")
    exit()

# --- PASO 2: Unir Tareas con Proyectos y Secciones (Usando Pandas Merge) ---
print("2. Uniendo datos para el reporte...")

# 2.1: Unir Tareas con Proyectos por 'project_id'
df_report = df_tasks.merge(
    df_projects, 
    left_on='project_id', 
    right_on='id', 
    how='left'
)

# 2.2: Unir el resultado con Secciones por 'section_id'
df_report = df_report.merge(
    df_sections, 
    left_on='section_id', 
    right_on='id', 
    how='left',
    suffixes=('', '_sec') # Sufijo para evitar conflicto de nombres de columna
)

# 2.3: Limpieza y selección de columnas para el reporte
final_columns = [
    'content', 
    'project_name',      # Nombre del Proyecto (obtenido del merge)
    'section_name',      # Nombre de la Sección (obtenido del merge)
    'completed_at', 
    'due', 
    'description', 
    'duration', 
    'project_id'         # Dejamos el ID por si lo necesitas para un filtro
]

df_final_report = df_report[final_columns].fillna({'section_name': 'Sin Sección'})


# --- PASO 3: Vista del Reporte Final ---
print("\n3. Reporte Final (Primeras filas):")
print(f"Filas totales en el reporte: {len(df_final_report)}")
print(df_final_report.head())