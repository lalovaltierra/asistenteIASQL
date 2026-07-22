FROM python:3.11-slim

# 2. Evitar que Python genere archivos .pyc y forzar salida en consola
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema y configurar repositorios
RUN apt-get update && apt-get install -y \
    curl apt-transport-https gnupg2 unixodbc-dev build-essential \
    # Descargar la llave de Microsoft usando el método moderno de GPG
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    # Configurar el repositorio específico para Debian 12 (base de python 3.11-slim)
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    # Actualizar listas e instalar el Driver ODBC 18
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    # Limpiar caché de apt para mantener la imagen ligera
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY ./backend /app/backend
COPY ./static /app/static

# 6. Copiar los scripts de arranque a la RAÍZ (para evitar que el volumen los pise)
#COPY start.sh /start.sh
#RUN chmod +x /start.sh

# 7. Copiar el resto del código (opcional si usas volúmenes, pero buena práctica)
COPY ./app /app

# 8. Exponer el puerto de FastAPI en Vanna
EXPOSE 8000

# 9. Ejecutar el script automatizado
#ENTRYPOINT ["/start.sh"]

# Comando para iniciar el servidor
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]