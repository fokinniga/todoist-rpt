from todoist_api_python.api import TodoistAPI
import pandas as pd
import json

api = TodoistAPI("874b527c4061e519eb927828b5d76da2f67f521d")
# Obtener tareas:
# tasks_iterator = api.get_tasks(project_id=None, section_id=None, parent_id=None, label=None, ids=None, limit=10)

def getProyect(project_id):
    proyect_data = api.get_project(project_id)
    return proyect_data.name

def getSection(section_id):
    if(section_id != None):
        section_data= api.get_section(section_id)
        return section_data.name
    else:
        return None
py_list = []
projectsapi = api.get_projects(limit=None)
for projects in projectsapi:
    for project in projects:
        print(type(project))
        #py_list.append(json.loads(str(project)))
        print(f"ID: {project.id}, Nombre: {project.name}")

# tasks_iterator = api.get_tasks(project_id="6f424rwJR7rJhXhQ", section_id=None, parent_id=None, label=None, ids=None, limit=10)
# tasks_iterator = api.get_tasks()

# for tasks in tasks_iterator:
#     for task in tasks:
#         print(f"Proyecto: {task.project_id} {getProyect(task.project_id)} Seccion: {task.section_id} {getSection(task.section_id)} Contenido: {task.content} Completa: {task.completed_at} Deadline: {task.deadline} Descripcion: {task.description} Duedate: {task.due} Duration: {task.duration}")

