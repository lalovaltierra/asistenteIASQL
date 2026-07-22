# 🏛️ iGTO AI: Motor RAG Text-to-SQL para Obra Pública

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)
![Ollama](https://img.shields.io/badge/Ollama-Gemma_3-purple.svg)
![SQL Server](https://img.shields.io/badge/SQL_Server-Supported-red.svg)

Un motor de Inteligencia Artificial basado en el paradigma de Generación Aumentada por Recuperación (RAG) para la conversión de lenguaje natural a sentencias SQL (Text-to-SQL). 

Este proyecto fue diseñado para democratizar el acceso analítico a datos gubernamentales (obra pública, planeación e inversión) permitiendo hacer consultas semánticas complejas sobre esquemas relacionales sin saber programar en SQL, manteniendo el 100% de la privacidad de los datos mediante ejecución local.

## 🚀 Arquitectura Técnica

El sistema utiliza una arquitectura multi-contenedor que aísla el procesamiento cognitivo de la base de datos transaccional:

* **Orquestación RAG:** `Vanna.ai` gestiona el contexto y los *embeddings*.
* **Motor LLM Local:** `Ollama` ejecutando **Gemma 3 (8B)** para inferencia sin depender de APIs de terceros (OpenAI/Anthropic).
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
```bash
git clone [https://github.com/lalovaltierra/asistenteIASQL.git](https://github.com/lalovaltierra/asistenteIASQL.git)
cd asistenteIASQL
# Configura tu archivo .env con la cadena de conexión a SQL Server
