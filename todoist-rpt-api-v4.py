import os
import pandas as pd
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import requests
from typing import Tuple, Optional, Dict, List

# --- CONFIGURACIÓN Y CONEXIÓN ---

# --- Cargar Variables de Entorno ---
load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
# Validar token 
if not API_TOKEN:
    print("¡ERROR! La variable de entorno TODOIST_API_TOKEN no está configurada.")
    exit() 

# --- Configuración ---
# Usamos el base URL de la API v1
API_URL = 'https://api.todoist.com/api/v1' 


# --- Funciones de Selección y Utilidad ---

def seleccionar_tipo_de_reporte() -> str:
    """
    Pregunta al usuario qué tipo de reporte de Todoist desea generar.
    """
    print("--- 📝 Generador de Reportes de Todoist ---")
    print("Por favor, selecciona el tipo de reporte a generar:")
    print("1. **Reporte semanal**")
    print("2. **Reporte por proyecto**")
    
    while True:
        try:
            opcion = input("Ingresa el número de la opción (1 o 2): ")
            opcion = int(opcion)
            
            if opcion == 1:
                return "semanal"
            elif opcion == 2:
                return "proyecto"
            else:
                print("⚠️ Opción no válida. Por favor, ingresa 1 o 2.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")


def seleccionar_rango_fechas() -> Tuple[date, date]:
    """
    Pregunta al usuario el rango de fechas a reportar. Retorna (since_date, until_date).
    """
    today = datetime.now().date()
    lunes_actual = today - timedelta(days=today.weekday())
    domingo_actual = lunes_actual + timedelta(days=6)
    lunes_pasado = lunes_actual - timedelta(weeks=1)
    domingo_pasado = domingo_actual - timedelta(weeks=1)

    print("\n--- 📅 Rango de Fechas ---")
    print(f"1. Semana Actual (Lunes {lunes_actual} - Domingo {domingo_actual})")
    print(f"2. Semana Pasada (Lunes {lunes_pasado} - Domingo {domingo_pasado})")
    print("3. Últimos N días (a partir de hoy)")

    while True:
        opcion = input("Ingresa el número de la opción (1, 2 o 3): ")
        
        try:
            opcion_num = int(opcion)
            
            if opcion_num == 1:
                return lunes_actual, domingo_actual
            
            elif opcion_num == 2:
                return lunes_pasado, domingo_pasado
            
            elif opcion_num == 3:
                while True:
                    try:
                        n_dias = int(input("Ingresa el número de días a reportar (ej. 7): "))
                        if n_dias > 0:
                            since_date = today - timedelta(days=n_dias - 1)
                            until_date = today 
                            return since_date, until_date
                        else:
                            print("⚠️ Debes ingresar un número positivo de días.")
                    except ValueError:
                        print("⚠️ Entrada no válida. Ingresa un número entero.")
            else:
                print("⚠️ Opción no válida. Ingresa 1, 2 o 3.")
        except ValueError:
            print("⚠️ Entrada no válida. Ingresa un número.")


def seleccionar_proyecto_root(df_root_pys: pd.DataFrame) -> str:
    """
    Muestra los proyectos raíz y le pide al usuario que seleccione uno por número.
    """
    
    print("\n--- 🌳 Proyectos Raíz Disponibles ---")
    
    proyectos_disponibles = df_root_pys[['name']].copy()
    proyectos_disponibles.index += 1
    print(proyectos_disponibles.to_string(header=False))
    
    max_opcion = len(df_root_pys)
    
    while True:
        try:
            opcion = input(f"\nIngresa el número del proyecto (1 a {max_opcion}) a reportar: ")
            opcion = int(opcion)
            
            if 1 <= opcion <= max_opcion:
                nombre_proyecto = df_root_pys.loc[opcion - 1, 'name']
                return nombre_proyecto
            else:
                print(f"⚠️ Opción no válida. Por favor, ingresa un número entre 1 y {max_opcion}.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")


def obtener_subproyectos(df_pys: pd.DataFrame, df_root_pys: pd.DataFrame, nombre_proyecto_raiz: str) -> Tuple[str, pd.DataFrame]:
    """
    Obtiene el ID del proyecto raíz y un DataFrame con sus subproyectos directos.
    """
    try:
        id_proyecto_raiz = df_root_pys.loc[df_root_pys['name'] == nombre_proyecto_raiz, 'id'].item()
    except ValueError:
        print(f"Error: No se pudo encontrar el ID del proyecto '{nombre_proyecto_raiz}'.")
        return "", pd.DataFrame()

    print(f"\nID del proyecto raíz: {id_proyecto_raiz}")
    
    df_subproyectos = df_pys[df_pys['parent_id'] == id_proyecto_raiz].copy()
    
    return id_proyecto_raiz, df_subproyectos


# --- Funciones de Conexión a API ---

def getProyectos() -> pd.DataFrame:
    """
    Obtiene la lista de proyectos de la cuenta de Todoist.
    """
    try:
        print("-> Conectando a la API para obtener proyectos...")
        response = requests.get(API_URL + '/projects', headers={'Authorization': f'Bearer {API_TOKEN}'})
        response.raise_for_status()
        answerJson = response.json()
        
        if isinstance(answerJson, list):
            pys_df = pd.DataFrame(answerJson)
        elif isinstance(answerJson, dict) and 'results' in answerJson:
            pys_df = pd.DataFrame(answerJson['results'])
        else:
            print("Formato de respuesta inesperado de la API de Todoist al obtener proyectos.")
            return pd.DataFrame()
            
        print(f"-> Proyectos obtenidos: {len(pys_df)}")
        return pys_df
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la lista de proyectos: {e}")
        return pd.DataFrame()


def get_tareas_activas(proyecto_id: str) -> pd.DataFrame:
    """
    Obtiene las tareas activas para un proyecto específico.
    *** CORREGIDA PARA MANEJAR RESPUESTA CON 'results' ***
    """
    try:
        print(f"   -> Obteniendo tareas activas para ID: {proyecto_id}...")
        response = requests.get(
            API_URL + '/tasks', 
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            params={'project_id': proyecto_id}
        )
        response.raise_for_status()
        answerJson = response.json()
        
        # Manejo principal (basado en el feedback del usuario)
        if isinstance(answerJson, dict) and 'results' in answerJson:
            return pd.DataFrame(answerJson['results'])
        # Fallback: Si es una lista directa
        elif isinstance(answerJson, list):
            return pd.DataFrame(answerJson)
        else:
            print("⚠️ Respuesta inesperada en tareas activas, se esperaba una lista o un dict con 'results'.")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener tareas activas: {e}")
        return pd.DataFrame()


def get_tareas_completadas(proyecto_id: str, since_date: date, until_date: date) -> pd.DataFrame:
    """
    Obtiene las tareas completadas para un proyecto en un rango de fechas.
    """
    # Formato ISO 8601 (incluyendo todo el día)
    since_str = since_date.strftime('%Y-%m-%dT00:00:00')
    until_str = until_date.strftime('%Y-%m-%dT23:59:59')
    
    try:
        print(f"   -> Obteniendo tareas completadas desde {since_date} hasta {until_date}...")
        response = requests.get(
            API_URL + '/tasks/completed/by_completion_date', 
            headers={'Authorization': f'Bearer {API_TOKEN}'},
            params={
                'project_id': proyecto_id,
                'since': since_str,
                'until': until_str
            }
        )
        response.raise_for_status()
        tareas = response.json()
        
        if isinstance(tareas, dict) and 'items' in tareas:
            return pd.DataFrame(tareas['items'])
        elif isinstance(tareas, list):
             return pd.DataFrame(tareas)
        else:
            print("⚠️ Respuesta inesperada en tareas completadas.")
            return pd.DataFrame()

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener tareas completadas: {e}")
        return pd.DataFrame()


# --- Ejecución Principal ---

if __name__ == "__main__":
    tipo_reporte = seleccionar_tipo_de_reporte()

    if tipo_reporte == "semanal":
        print("\n--- 🛠️ Generando reporte semanal... ---")
        
        # 1. Obtener rango de fechas
        since_date, until_date = seleccionar_rango_fechas()
        print(f"\nReporte configurado para el rango: **{since_date}** al **{until_date}**")

        # 2. Obtener proyectos y validar
        df_pys = getProyectos()
        
        if df_pys.empty:
            print("No se pudieron obtener los proyectos o el DataFrame está vacío. Terminando.")
            exit()
        
        # 3. Seleccionar proyecto raíz
        df_root_pys = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)
        proyecto_seleccionado = seleccionar_proyecto_root(df_root_pys)
        print(f"\n✅ Has seleccionado el proyecto: **{proyecto_seleccionado}**") 
        
        # 4. Obtener ID del proyecto raíz y subproyectos
        id_proyecto_raiz, df_subproyectos = obtener_subproyectos(df_pys, df_root_pys, proyecto_seleccionado)
        
        if not id_proyecto_raiz:
            exit()
            
        # 5. Obtener Tareas del Proyecto Raíz
        print("\n--- 📥 Extrayendo Tareas del Proyecto Raíz ---")
        
        df_tareas_activas_raiz = get_tareas_activas(id_proyecto_raiz)
        df_tareas_completadas_raiz = get_tareas_completadas(id_proyecto_raiz, since_date, until_date)
        
        # 6. Obtener Tareas de Subproyectos
        
        # 6a. Inicializar DataFrames para consolidación de subproyectos
        df_tareas_subproyectos_activas = pd.DataFrame()
        df_tareas_subproyectos_completadas = pd.DataFrame()
        
        if not df_subproyectos.empty:
            print("\n--- 📥 Extrayendo Tareas de Subproyectos Directos ---")
            
            for index, row in df_subproyectos.iterrows():
                sub_id = row['id']
                sub_name = row['name']
                print(f"Procesando subproyecto: {sub_name} (ID: {sub_id})")
                
                # Tareas Activas
                sub_activas = get_tareas_activas(sub_id)
                if not sub_activas.empty:
                    df_tareas_subproyectos_activas = pd.concat([df_tareas_subproyectos_activas, sub_activas], ignore_index=True)
                
                # Tareas Completadas
                sub_completadas = get_tareas_completadas(sub_id, since_date, until_date)
                if not sub_completadas.empty:
                    df_tareas_subproyectos_completadas = pd.concat([df_tareas_subproyectos_completadas, sub_completadas], ignore_index=True)
            
        # 7. Consolidar DataFrames Finales (Raíz + Subproyectos)
        
        df_final_activas = pd.DataFrame()
        df_final_completadas = pd.DataFrame()
        
        # Consolidar tareas activas
        df_final_activas = pd.concat([df_tareas_activas_raiz, df_tareas_subproyectos_activas], ignore_index=True)

        # Consolidar tareas completadas
        df_final_completadas = pd.concat([df_tareas_completadas_raiz, df_tareas_subproyectos_completadas], ignore_index=True)


        # 8. Mostrar resultados (Resumen del reporte)
        print(df_final_activas)
        print(df_final_completadas)
        print("\n--- 📊 RESUMEN FINAL DE TAREAS CONSOLIDADAS ---")
        print(f"Total Tareas ACTIVAS (Raíz + Subproyectos): {len(df_final_activas)}")
        print(f"Total Tareas COMPLETADAS (Raíz + Subproyectos): {len(df_final_completadas)}")
        
        # Aquí puedes usar df_final_activas y df_final_completadas para generar el reporte
        # print("\nDATAFRAME FINAL DE ACTIVAS:")
        # print(df_final_activas.head())
        # print("\nDATAFRAME FINAL DE COMPLETADAS:")
        # print(df_final_completadas.head())
            
    elif tipo_reporte == "proyecto":
        print("Generando reporte por proyecto...")
        df_pys = getProyectos()
        if not df_pys.empty:
            print(df_pys)