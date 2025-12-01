import os
import pandas as pd
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# --- CONFIGURACIÓN Y CONEXIÓN ---

# --- Cargar Variables de Entorno ---
load_dotenv() 
API_TOKEN = os.getenv('TODOIST_API_TOKEN')
# Validar token (buena práctica)
if not API_TOKEN:
    print("¡ERROR! La variable de entorno TODOIST_API_TOKEN no está configurada.")
    exit()

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


def getProyectos():
    """
    Obtiene la lista de proyectos de la cuenta de Todoist.
    """
    try:
        # La API de Todoist v1 para /projects no existe.
        # Asumo que estás usando la API REST v2 (https://api.todoist.com/rest/v2/projects)
        # o la API de Sync (https://api.todoist.com/sync/v9/projects) y que has ajustado la URL a API_URL = 'https://api.todoist.com/rest/v2'
        # o que la respuesta JSON incluye la lista de proyectos directamente.
        
        # Basado en tu código inicial: response = requests.get(API_URL + '/projects', headers={'Authorization': f'Bearer {API_TOKEN}'})
        # Si esta URL te devuelve una lista de diccionarios, la conversión funciona.
        # Si la respuesta es un dict con una clave 'results', lo ajustamos aquí:
        response = requests.get(API_URL + '/projects', headers={'Authorization': f'Bearer {API_TOKEN}'})
        response.raise_for_status()
        answerJson = response.json()
        
        # Ajuste de robustez: Si la respuesta no es una lista, asumimos que es un dict y buscamos la clave 'results'.
        if isinstance(answerJson, list):
            pys_df = pd.DataFrame(answerJson)
        elif isinstance(answerJson, dict) and 'results' in answerJson:
            pys_df = pd.DataFrame(answerJson['results'])
        else:
            print("Formato de respuesta inesperado de la API de Todoist.")
            return pd.DataFrame()
            
        return pys_df
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la lista de proyectos: {e}")
        return pd.DataFrame()

def seleccionar_proyecto_root(df_root_pys):
    """
    Muestra los proyectos raíz y le pide al usuario que seleccione uno por número.
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

# 🆕 NUEVA FUNCIÓN AÑADIDA
def obtener_subproyectos(df_pys, df_root_pys, nombre_proyecto_raiz):
    """
    Obtiene todos los subproyectos (hijos directos) del proyecto raíz seleccionado.
    
    :param df_pys: DataFrame completo de todos los proyectos.
    :param df_root_pys: DataFrame con solo los proyectos principales.
    :param nombre_proyecto_raiz: Nombre del proyecto seleccionado por el usuario.
    :return: DataFrame con los subproyectos (hijos directos) del proyecto raíz.
    """
    # 1. Obtener el ID del proyecto raíz
    # Usamos .item() para extraer el valor del ID de la serie resultante
    try:
        id_proyecto_raiz = df_root_pys.loc[df_root_pys['name'] == nombre_proyecto_raiz, 'id'].item()
    except ValueError:
        print(f"Error: No se pudo encontrar el ID del proyecto '{nombre_proyecto_raiz}'.")
        return pd.DataFrame()

    print(f"\nID del proyecto raíz '{nombre_proyecto_raiz}': {id_proyecto_raiz}")

    # 2. Filtrar df_pys para encontrar todos los proyectos cuyo 'parent_id' sea igual al 'id_proyecto_raiz'.
    # Usamos .copy() para evitar SettingWithCopyWarning
    df_subproyectos = df_pys[df_pys['parent_id'] == id_proyecto_raiz].copy()
    
    return df_subproyectos

# --- Ejecución ---
tipo_reporte = seleccionar_tipo_de_reporte()

if tipo_reporte == "semanal":
    print("Generando reporte semanal...")
    df_pys = getProyectos()
    
    if df_pys.empty:
        print("No se pudieron obtener los proyectos o el DataFrame está vacío.")
    else:
        # Filtrar proyectos raíz y resetear índice
        df_root_pys = df_pys[df_pys['parent_id'].isna()].reset_index(drop=True)
        
        # Seleccionar proyecto raíz
        proyecto_seleccionado = seleccionar_proyecto_root(df_root_pys)
        print(f"\n✅ Has seleccionado el proyecto: {proyecto_seleccionado}") 
        
        # Obtener subproyectos 🆕
        df_subproyectos = obtener_subproyectos(df_pys, df_root_pys, proyecto_seleccionado)
        
        if df_subproyectos.empty:
            print(f"--- ⚠️ El proyecto '{proyecto_seleccionado}' no tiene subproyectos directos. ---")
        else:
            print("\n--- 📂 Subproyectos Directos Encontrados (df_subproyectos) ---")
            print(df_subproyectos[['id', 'name', 'parent_id']].reset_index(drop=True))
            
elif tipo_reporte == "proyecto":
    print("Generando reporte por proyecto...")
    df_pys = getProyectos()
    print(df_pys)