import os
import time
import tempfile
import re
from datetime import datetime
import sqlite3
import pyodbc
import pandas as pd
import requests
import warnings
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from vanna.chromadb import ChromaDB_VectorStore
from vanna.ollama import Ollama

warnings.filterwarnings('ignore', category=UserWarning)

# =====================================================================
# CONFIGURACIÓN DE LOGS (Se guardarán en el contenedor de Docker)
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VannaAPI")

# =====================================================================
# SISTEMA DE AUDITORÍA (Base de Datos Local SQLite)
# =====================================================================
DB_AUDIT_PATH = "audit_logs.db"

def init_audit_db():
    conn = sqlite3.connect(DB_AUDIT_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS bitacora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
            pregunta TEXT,
            sql_generado TEXT,
            tiempo_ia REAL,
            tiempo_sql REAL,
            estatus TEXT,
            detalle_error TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Inicializamos la tabla al arrancar FastAPI
init_audit_db()

def registrar_auditoria(pregunta, sql_gen="", t_ia=0, t_sql=0, estatus="EXITO", error=""):
    try:
        conn = sqlite3.connect(DB_AUDIT_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO bitacora (pregunta, sql_generado, tiempo_ia, tiempo_sql, estatus, detalle_error)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (pregunta, sql_gen, t_ia, t_sql, estatus, error))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error guardando en bitacora: {str(e)}")
# =====================================================================

class TolerantVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)
        self.ollama_host = config.get('ollama_host', 'http://ollama:11434')
        self.model = config.get('model', 'qwen3.5:9b')
        #self.model = config.get('model', 'qwen2.5-coder:7b')

    def submit_prompt(self, prompt, **kwargs):
            url = f"{self.ollama_host}/api/chat"
           
            # =====================================================================
            # SYSTEM PROMPT INYECTADO Y OPTIMIZADO PARA Qwen (T-SQL)
            # =====================================================================
            sqlcoder_system_instruction = {
                "role": "system",
                "content": (
                    "You are a Microsoft SQL Server (T-SQL) expert developer. Your sole task is to generate "
                    "a valid, optimized T-SQL query based on the provided database schema, documentation, and user question.\n\n"
                    "CRITICAL RULES FOR TABLE NAMES AND SCHEMAS:\n"
                    "1. ALWAYS respect the exact names of the tables from the DDL. NEVER modify, shorten, or assume names.\n"
                    "2. ALWAYS use the full schema prefix for tables. NEVER write tables without it.\n"
                    "3. The table for municipalities is EXACTLY 'cat.cMunicipios'. NEVER write 'cat.municipios' or 'dbo.municipios'. It requires the 'c' prefix.\n"
                    "4. The transactional tables are 'datos.mProyectos_iGTO' and 'datos.cProyectosInversion'. Always use their full schema prefixes.\n\n"
                    "CRITICAL SINTAX RULES:\n"
                    "1. DO NOT use placeholders, parameters, or question marks ('?') under any circumstance. Extract and use the literal values provided in the user's question directly into the SQL string.\n"
                    "2. Respond ONLY with the executable SQL code block. Do not include markdown text explanations outside the SQL code, do not start with 'Here is the SQL', just return the query.\n"
                    "3. Ensure the dialect is strictly compatible with Microsoft SQL Server (T-SQL)."
                    "4. Catalog tables use the 'cat.' prefix (e.g., 'cat.cMunicipios').\n"
                    "5. If filtering by year, DO NOT use YEAR(). Use the integer column 'Ejercicio' (e.g., Ejercicio = 2026).\n"
                    "6. For any reference to 'folio', ALWAYS use the exact column name 'FolioObraAccion'. NEVER use 'folio' or 'ClaveFolio'."
                    "7. For any text filter or name of a municipality, ALWAYS use the exact column name 'NombreMunicipio'. NEVER use 'municipio' or 'Nombre' as a column."
                )
            }
            
            # Inyectamos nuestra regla maestra al principio de la conversación
            if isinstance(prompt, list):
                prompt.insert(0, sqlcoder_system_instruction)
            # ========================================================
           
            # Ajustamos parámetros para forzar determinismo (temperatura baja)
            payload = {
                "model": self.model, 
                "messages": prompt, 
                "stream": False,
                "options": {
                    "temperature": 0.1,      # Forzamos máximo determinismo
                    "top_p": 0.1,
                    "num_ctx": 8192
                }
            }
            
            # AQUI ES DONDE CAMBIAS EL TIEMPO DE ESPERA.
            # 600 = 10 minutos (si requieres más, sube el número)
            try:
                response = requests.post(url, json=payload, timeout=600)
                response.raise_for_status()
                
                # 1. Obtenemos el texto exacto que escupió la IA
                raw_text = response.json()["message"]["content"]
                
                # 2. EL RAYO X: Lo imprimimos en la consola para auditar a Qwen
                logger.info(f"🤖 RESPUESTA CRUDA DE QWEN 3.5:\n{raw_text}")
                
                # 3. EL LIMPIAPARABRISAS: Quitamos cualquier comilla markdown rebelde a la fuerza
                cleaned_text = raw_text.replace("```sql", "").replace("```", "").strip()
                
                return cleaned_text
                
            except requests.exceptions.ReadTimeout:
                logger.error("TIMEOUT 504: El modelo tardó demasiado.")
                raise HTTPException(status_code=504, detail="El modelo tardó demasiado. Simplifica la consulta.")
            except Exception as e:
                logger.error(f"ERROR 502: {str(e)}")
                raise HTTPException(status_code=502, detail=f"Error Ollama: {str(e)}")

vn = TolerantVanna(config={
    'path': '/app/chroma_db',
    'ollama_host': os.getenv('OLLAMA_HOST', 'http://ollama:11434'),
    'model': 'qwen3.5:9b'
})
# remplazar en caso de requerirse por 'model': 'qwen2.5-coder:7b'

app = FastAPI(title="Vanna Custom UI")
mssql_conn_str = os.getenv('MSSQL_CONN_STR')

class QuestionRequest(BaseModel):
    question: str

class DownloadRequest(BaseModel):
    sql: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "vanna_classic"}

@app.post("/api/query")
def ask_question(req: QuestionRequest):
    logger.info(f"Nueva pregunta recibida: '{req.question}'")

    # Variables de control para la bitácora
    sql = ""
    t_ollama = 0
    t_sql = 0

    try:
        # 1. Cronometrar Generación SQL (Ollama)
        inicio_ollama = time.perf_counter()
        sql = vn.generate_sql(req.question)
        tiempo_ollama = time.perf_counter() - inicio_ollama

        if not sql:
            logger.warning("Fallo en la generación de SQL (Respuesta vacía).")
            raise HTTPException(status_code=400, detail="No se pudo generar SQL.")
        
        # ====================================================================
        # PARCHE DE SEGURIDAD MLOPS (POST-PROCESAMIENTO)
        # Si la IA olvida los esquemas, Python los inyecta mediante Regex.
        # ====================================================================
        # Arregla mProyectos_iGTO
        sql = re.sub(r'(?i)(?<!datos\.)\bmProyectos_iGTO\b', 'datos.mProyectos_iGTO', sql)
        # Arregla cProyectosInversion
        sql = re.sub(r'(?i)(?<!datos\.)\bcProyectosInversion\b', 'datos.cProyectosInversion', sql)
        # Arregla cMunicipios (y evita que use "municipios" a secas)
        sql = re.sub(r'(?i)(?<!cat\.)\bc?Municipios\b', 'cat.cMunicipios', sql)
        # ====================================================================
        # 👇 NUEVO ESCUDO PARA LA COLUMNA FOLIO 👇
        # Si encuentra la palabra exacta "folio" o "ClaveFolio" (ignorando mayúsculas/minúsculas), la reemplaza.
        #sql = re.sub(r'(?i)\b(ClaveFolio|folio)\b', 'FolioObraAccion', sql)
        #sql = re.sub(r'(?i)\b(municipio|Nombre)\b', 'NombreMunicipio', sql)
        
        # ========================================================
        # NUEVO ESCUDO CONTRA ALUCINACIONES DE PARÁMETROS ODBC
        # ========================================================
        if "?" in sql:
            logger.warning(f"La IA generó un placeholder (?): {sql}")
            raise HTTPException(
                status_code=400, 
                detail="La Inteligencia Artificial generó una consulta ambigua. Por favor, reformula tu pregunta con datos más específicos (ej. usando nombres exactos)."
            )
        # ========================================================

        logger.info(f"SQL Generado en {tiempo_ollama:.2f}s:\n{sql}")

        # 2. Cronometrar Ejecución SQL Server
        inicio_sql = time.perf_counter()
        with pyodbc.connect(mssql_conn_str) as conn:
            df = pd.read_sql(sql, conn)
        tiempo_sql = time.perf_counter() - inicio_sql

        tiempo_total = tiempo_ollama + tiempo_sql

        # ✅ GUARDAMOS EL ÉXITO EN LA BITÁCORA
        registrar_auditoria(req.question, sql, t_ollama, t_sql, "EXITO", "")
    
        logger.info(f"SQL Server finalizó en {tiempo_sql:.4f}s. Filas obtenidas: {len(df)}. Tiempo Total: {tiempo_total:.2f}s")

        return {
                    "sql": sql, 
                    "data": df.head(100).to_dict(orient="records"),
                    "metrics": {
                        "time_llm": round(tiempo_ollama, 2),
                        "time_sql": round(tiempo_sql, 4),
                        "time_total": round(tiempo_total, 2)
                    }
        }

    except Exception as e:
        # ❌ GUARDAMOS EL ERROR EN LA BITÁCORA
        error_msg = str(e)
        logger.error(f"Error procesando la consulta: {error_msg}")
        registrar_auditoria(req.question, sql, t_ollama, t_sql, "ERROR", error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/auditoria")
def get_auditoria(limite: int = 100, fecha: str = None):
    """
    Obtiene los registros de la bitácora. 
    Opcional: pasar una fecha en formato YYYY-MM-DD (ej. ?fecha=2026-06-29)
    """
    try:
        conn = sqlite3.connect(DB_AUDIT_PATH)
        conn.row_factory = sqlite3.Row # Para que devuelva diccionarios
        c = conn.cursor()
        
        if fecha:
            # Filtra solo los de un día en particular
            c.execute("SELECT * FROM bitacora WHERE date(fecha_hora) = ? ORDER BY id DESC LIMIT ?", (fecha, limite))
        else:
            # Trae los más recientes
            c.execute("SELECT * FROM bitacora ORDER BY id DESC LIMIT ?", (limite,))
            
        resultados = [dict(row) for row in c.fetchall()]
        conn.close()
        return resultados
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo bitácora: {str(e)}")

@app.post("/api/download")
def download_excel(req: DownloadRequest):
    try:
        with pyodbc.connect(mssql_conn_str) as conn:
            df = pd.read_sql(req.sql, conn)
            
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_file.name, index=False)
        
        return FileResponse(
            path=temp_file.name, 
            filename="reporte_datos.xlsx", 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Error descargando Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)