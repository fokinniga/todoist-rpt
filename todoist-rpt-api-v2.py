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
API_URL = 'https://api.todoist.com/api/v1'


def seleccionar_tipo_de_reporte():
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

# Ejemplo de cómo se usaría esta función
# tipo_reporte = seleccionar_tipo_de_reporte()
# print(f"Has seleccionado: {tipo_reporte}")

def getProyectos():
    """
    Obtiene la lista de proyectos de la cuenta de Todoist.
    """
    try:
        response = requests.get(API_URL + '/projects', headers={'Authorization': f'Bearer {API_TOKEN}'})
        response.raise_for_status()
        answerJson = response.json()
        #print(type(answerJson))
        pys_df = pd.DataFrame(answerJson['results'])
        return pys_df
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la lista de proyectos: {e}")
        return []   

def seleccionar_proyecto_root(df_root_pys):
    """
    Muestra los proyectos raíz y le pide al usuario que seleccione uno por número.
    
    :param df_root_pys: DataFrame con solo los proyectos principales.
    :return: El nombre del proyecto seleccionado.
    """
    
    print("\n--- 🌳 Proyectos Raíz Disponibles ---")
    
    # Mostrar los proyectos con el nuevo índice secuencial
    proyectos_disponibles = df_root_pys[['name']].copy()
    proyectos_disponibles.index += 1 # Ajustar el índice para que empiece en 1 para el usuario
    print(proyectos_disponibles.to_string(header=False))
    
    max_opcion = len(df_root_pys)
    
    while True:
        try:
            opcion = input(f"\nIngresa el número del proyecto (1 a {max_opcion}) a reportar: ")
            opcion = int(opcion)
            
            if 1 <= opcion <= max_opcion:
                # Retornar el nombre del proyecto. Restamos 1 porque el índice real de pandas empieza en 0
                nombre_proyecto = df_root_pys.loc[opcion - 1, 'name']
                return nombre_proyecto
            else:
                print(f"⚠️ Opción no válida. Por favor, ingresa un número entre 1 y {max_opcion}.")
        except ValueError:
            print("⚠️ Entrada no válida. Por favor, ingresa un número.")

# --- Ejemplo de uso ---

# 1. Asumiendo que df_root_pys ya fue creado y reseteado:
# df_root_pys = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)

# 2. Llamar a la función
# proyecto_seleccionado = seleccionar_proyecto_root(df_root_pys)
# print(f"\n✅ Has seleccionado el proyecto: {proyecto_seleccionado}")


# --- Ejecución ---
#¿Qué tipo de reporte se va a generar?
tipo_reporte = seleccionar_tipo_de_reporte()
if tipo_reporte == "semanal":
    print("Generando reporte semanal...")
    df_pys = getProyectos()
    df_root_pys = df_pys[df_pys['parent_id'].isna()]
    df_root_pys = df_root_pys.reset_index(drop=True)
    #print(df_root_pys)
    proyecto_seleccionado = seleccionar_proyecto_root(df_root_pys)
    print(f"\n✅ Has seleccionado el proyecto: {proyecto_seleccionado}")    
else:
    print("Generando reporte por proyecto...")
    df_pys = getProyectos()
    print(df_pys)

#print(type(df_pys))
#primer_renglon = df_pys.iloc[0]
#print(primer_renglon)
#print(type(primer_renglon))

# 1. Obtener las tareas completadas
#tasks = get_completed_tasks(API_TOKEN, API_URL, since=SINCE_DATE, until=UNTIL_DATE)

# 2. Generar el reporte
#generate_report(tasks)