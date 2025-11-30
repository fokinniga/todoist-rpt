import os
import pandas as pd
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# --- CONFIGURACIÓN Y CONEXIÓN ---

# --- Cargar Variables de Entorno ---
# Esto busca el archivo .env en el directorio actual y carga las variables.
load_dotenv() 
# Leemos el token de la variable de entorno TODOIST_API_TOKEN
API_TOKEN = os.getenv('TODOIST_API_TOKEN')

# --- Configuración ---
API_URL = 'https://api.todoist.com/sync/v9/completed/get_all'

# Rango de fechas: Tareas completadas en los últimos 7 días
UNTIL_DATE = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
SINCE_DATE = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')


def get_completed_tasks(token, url, since=None, until=None):
    """
    Realiza una solicitud al endpoint de tareas completadas de la Todoist Sync API.
    """
    if not token:
        print("❌ Error: El token de API no se encontró. Asegúrate de que TODOIST_API_TOKEN está en tu archivo .env.")
        return []
        
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    params = {}
    if since:
        params['since'] = since
    if until:
        params['until'] = until

    try:
        print(f"Buscando tareas completadas desde {SINCE_DATE} hasta {UNTIL_DATE}...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        taskInfo = data.get('items', [])
        return taskInfo 

    except requests.exceptions.RequestException as e:
        print(f"❌ Error al realizar la solicitud: {e}")
        return []

def generate_report(completed_tasks):
    """
    Procesa la lista de tareas completadas e imprime un resumen.
    """
    if not completed_tasks:
        print("✅ No se encontraron tareas completadas en el rango de fechas especificado.")
        return

    print(f"\n🎉 Reporte de Tareas Completadas ({len(completed_tasks)} en total) 🎉")
    print("-" * 50)

    for i, task in enumerate(completed_tasks):
        # La Sync API proporciona 'content' y 'completed_at'
        content = task.get('content', 'Contenido no disponible (Eliminado)') 
        completed_at = task.get('completed_at')
        project_id = task.get('project_id')
        
        print(f"Tarea #{i+1}")
        print(f"  Contenido: **{content}**")
        print(f"  Completada: {completed_at}")
        print(f"  Proyecto ID: {project_id}")
        print("-" * 50)
    
    print("Reporte finalizado.")


# --- Ejecución ---
# 1. Obtener las tareas completadas
tasks = get_completed_tasks(API_TOKEN, API_URL, since=SINCE_DATE, until=UNTIL_DATE)

# 2. Generar el reporte
generate_report(tasks)