from todoist_api_python.api import TodoistAPI
import pandas as pd
import json
from datetime import datetime, timedelta

# --- Configuración (Usar tu token válido) ---
API_TOKEN = "874b527c4061e519eb927828b5d76da2f67f521d" 
api = TodoistAPI(API_TOKEN)

def getTaskList():
    i = 0
    task_data = []
    print("step 1")
    taskapi = api.get_tasks()
    for tasks in taskapi:
        for task in tasks:
            i += 1
            print(i)
            print("step 2")
            if task.due:
                due_date = task.due.date
            else:
                due_date = "None"
            task_data.append({
                'project_id': task.project_id,
                'section_id': task.section_id,
                'task_content': task.content,
                'completed_at': task.completed_at,
                'deadline': task.deadline,
                'description': task.description,
                'due_date': due_date,
                'duration': task.duration
            })
    df_tasks = pd.DataFrame(task_data)
    return df_tasks

def getProyectList():
    project_data = []
    projectsapi = api.get_projects(limit=None)
    for projects in projectsapi:
        for project in projects:
            #print(f"ID: {project.id}, Nombre: {project.name}")
            if project.parent_id:
                # Si parent_id es un objeto Project, extraemos su ID.
                if isinstance(project.parent_id, str):
                    # Caso de fallback: si fuera un string de ID
                    parent_id_value = project.parent_id
                    #print("caso uno")
                else:
                    # Caso actual: es un objeto Project, accedemos a su ID
                    parent_id_value = project.parent_id.id
                    #print("caso dos")
            project_data.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_group': project.parent_id
            })
    df_projects = pd.DataFrame(project_data)
    return df_projects

def getSectionList():
    sections_data = []
    sectionapi = api.get_sections(limit=None)
    for sections in sectionapi:
        for section in sections:
            sections_data.append({
                'section_id': section.id,
                'section_name': section.name
            })
    df_sections = pd.DataFrame(sections_data)
    return df_sections

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

def generate_todoist_report():

    df_projects = getProyectList()
    #print(df_projects)
    df_sections = getSectionList()
    #print(df_sections)
    df_tasks = getTaskList()
    print(df_tasks)
    df_report = process_and_filter_report(df_tasks, df_projects, df_sections)




# Ejecutar el script
if __name__ == "__main__":
    generate_todoist_report()