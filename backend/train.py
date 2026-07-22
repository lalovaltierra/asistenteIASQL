import os
import pyodbc
import requests
import warnings
from vanna.chromadb import ChromaDB_VectorStore
from vanna.ollama import Ollama

warnings.filterwarnings('ignore', category=UserWarning)

class TolerantVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)
        self.ollama_host = config.get('ollama_host', 'http://ollama:11434')
        self.model = config.get('model', 'qwen3.5:9b')
        #self.model = config.get('model', 'qwen2.5-coder:7b')

    # Sobreescribimos el método para evitar que Vanna corte la conexión prematuramente
    def submit_prompt(self, prompt, **kwargs):
        url = f"{self.ollama_host}/api/chat"
        payload = {"model": self.model, "messages": prompt, "stream": False}
        # ¡La magia está aquí! 300 segundos de paciencia para tu equipo
        response = requests.post(url, json=payload, timeout=300)
        return response.json()["message"]["content"]

vn = TolerantVanna(config={
    'path': '/app/chroma_db',
    'ollama_host': os.getenv('OLLAMA_HOST', 'http://ollama:11434'),
    'model': 'qwen3.5:9b'
})
# remplazar en caso de requerirse por 'model': 'qwen2.5-coder:7b'

print("Iniciando el entrenamiento Vanna Clásico Tolerante...")
mssql_conn_str = os.getenv('MSSQL_CONN_STR')


try:
    conn = pyodbc.connect(mssql_conn_str)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.name AS schema_name, t.name AS table_name, c.name AS column_name, tp.name AS data_type
        FROM sys.tables t INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN sys.columns c ON t.object_id = c.object_id INNER JOIN sys.types tp ON c.user_type_id = tp.user_type_id
        WHERE t.is_ms_shipped = 0
    """)
    schema_text = "Estructura BD:\n" + "".join([f"Tabla: {r.schema_name}.{r.table_name}, Columna: {r.column_name} ({r.data_type})\n" for r in cursor.fetchall()])
    conn.close()
    
    vn.train(documentation=schema_text)
    print("✅ Esquema indexado.")
except Exception as e:
    print(f"Error esquema: {e}")

vn.train(ddl="CREATE TABLE cat.cMunicipios (idMunicipio SMALLINT PRIMARY KEY, NombreMunicipio VARCHAR(100), ClaveMunicipio VARCHAR(3), Vigente BIT, idRegion INT)")
vn.train(documentation="En cat.cMunicipios: Vigente (1=activo). NombreMunicipio es el nombre.")
vn.train(question="¿Cuántos municipios existen?", sql="SELECT COUNT(idMunicipio) FROM cat.cMunicipios WHERE Vigente = 1")
print("✅ Documentación y Few-Shot indexados.")
