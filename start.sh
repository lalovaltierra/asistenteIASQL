#!/bin/bash
# IMPORTANTE: Movernos a la carpeta donde están tus scripts de Python
cd /app

echo "🔄 Esperando sincronización interna de red de contenedores..."
sleep 4

echo "🏋️‍♂️ [AUTOMÁTICO] Iniciando entrenamiento de los esquemas en ChromaDB (train.py)..."
python train.py

echo "🚀 Lanzando servidor FastAPI de Vanna..."
exec python main.py





