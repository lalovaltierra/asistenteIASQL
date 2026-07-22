# 🏛️ iGTO AI: Motor RAG Text-to-SQL para Obra Pública

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![Ollama](https://img.shields.io/badge/Ollama-Qwen_3.5-purple.svg)
![SQL Server](https://img.shields.io/badge/SQL_Server-Supported-red.svg)

Un motor de Inteligencia Artificial basado en el paradigma de Generación Aumentada por Recuperación (RAG) para la conversión de lenguaje natural a sentencias SQL (Text-to-SQL). 

Este proyecto fue diseñado para democratizar el acceso analítico a datos gubernamentales (obra pública, planeación e inversión) permitiendo hacer consultas semánticas complejas sobre esquemas relacionales sin saber programar en SQL, manteniendo el 100% de la privacidad de los datos mediante ejecución local.

## 🚀 Arquitectura Técnica

El sistema utiliza una arquitectura multi-contenedor que aísla el procesamiento cognitivo de la base de datos transaccional:

* **Orquestación RAG:** `Vanna.ai` gestiona el contexto y los *embeddings*.
* **Motor LLM Local:** `Ollama` ejecutando **Qwen 3.5 (5B)** para inferencia sin depender de APIs de terceros (OpenAI/Anthropic).
* **Vector Store:** `ChromaDB` para indexar esquemas DDL, reglas de negocio y *Few-Shots*.
* **Capa API & Seguridad:** `FastAPI` + `Uvicorn` intercepta peticiones, inyecta reglas Regex de sanitización y gestiona los endpoints RESTful.
* **Auditoría Local:** Base de datos embebida en `SQLite` para registrar métricas de tiempo (LLM vs SQL), queries generadas y control de errores.
* **Base de Datos Principal:** Microsoft SQL Server (Manejo de esquemas cruzados `cat.` y `datos.`).

## 🛠️ Cómo echarlo a andar (Quickstart)

### 1. Requisitos Previos
* Docker y Docker Compose instalados.
* Una instancia de SQL Server accesible (con tus tablas de prueba).
* NVIDIA GPU (Recomendado para inferencia rápida con Ollama).

### 2. Clonar y Configurar
Clona este repositorio y configura tus variables de entorno:

git clone [https://github.com/lalovaltierra/asistenteIASQL.git](https://github.com/lalovaltierra/asistenteIASQL.git)
cd asistenteIASQL

#### Configura tu archivo .env con la cadena de conexión a SQL Server

### 3. Levantar la Infraestructura
Inicia los contenedores (API, Base Vectorial y Ollama):

docker-compose up -d

### 4. Descargar el Modelo Local (Qwen 3.5)
Utilizamos una versión cuantizada de Qwen 3.5 alojada en Hugging Face. Para cargarla en el contenedor de Ollama (ollama_service), sigue estos pasos:

####A. Descargar el archivo .gguf:
Descarga el peso del modelo en un directorio local que esté montado como volumen en tu Docker (por ejemplo, en ./models/).

wget "[https://huggingface.co/tu-usuario/ruta-al-modelo/resolve/main/qwen-3.5-q5_k_m.gguf](https://huggingface.co/tu-usuario/ruta-al-modelo/resolve/main/qwen-3.5-q5_k_m.gguf)" -O ./models/qwen3.5.gguf
(Nota: Ajusta la URL al repositorio exacto de Hugging Face que estés utilizando).

####B. Crear el Modelfile:
Crea un archivo llamado Modelfile dentro de la misma carpeta ./models/ con el siguiente contenido:

Dockerfile
FROM ./qwen3.5.gguf

# Aquí puedes agregar SYSTEM prompts base si tu arquitectura lo requiere

####C. Construir el modelo en Ollama:
Ejecuta la instrucción dentro del contenedor para compilarlo:

docker exec -it ollama_service ollama create qwen_local -f /models/Modelfile

### 5. Inyectar la Memoria Semántica (Entrenamiento)
Antes de hacer preguntas, el modelo necesita conocer la estructura de tu base de datos. Ejecuta el script de entrenamiento para popular ChromaDB:

docker exec -it vanna_fastapi python backend/train.py
(Espera a que la consola confirme que todas las tablas y reglas fueron inyectadas con éxito).

### 6. ¡A consultar!
El servidor estará corriendo en http://localhost:8000. Puedes probar el endpoint principal enviando un POST a /api/query con el payload:

JSON
{
  "question": "¿Cuáles son los 5 proyectos con mayor avance financiero en 2026?"
}
