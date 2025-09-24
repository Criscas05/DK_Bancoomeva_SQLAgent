"""
Este archivo __init__.py convierte la carpeta 'agent' en un paquete de Python.

Actúa como una "fachada" o una interfaz pública para el agente.
Cualquier otro módulo que necesite componentes del agente (como main.py)
debe importar desde aquí, no desde los submódulos internos como graph.py o tools.py.

Esto rompe los ciclos de importación y promueve una arquitectura más limpia.
"""
# Exponer el ejecutor del grafo compilado
from .graph import agent_executor

# Exponer las herramientas individuales que puedan ser necesarias en otros lugares
# (como en la "vía rápida" de corrección de main.py)
from .tools import execute_databricks_query, get_database_schema_info, search_similar_queries

# Exponer también la lista completa de herramientas por si se necesita
from .tools import agent_tools
