#!/bin/bash

# Archivo de salida
OUTPUT="transcripcion_completa.txt"
echo "--- INICIO DEL MÓDULO ---" > $OUTPUT

# Lista de URLs (puedes ponerlas en un archivo urls.txt)
# Aquí un ejemplo de cómo iterar sobre un archivo con una URL por línea
while IFS= read -r url || [ -n "$url" ]; do
    echo "Descargando: $url"
    
    # Descargar el contenido y añadirlo al final del archivo
    # Usamos -s para modo silencioso y añadimos un separador
    echo -e "\n\n[Siguiente Video]\n" >> $OUTPUT
    curl -s "$url" >> $OUTPUT
    
done < urls.txt

echo "Proceso finalizado. Archivo generado: $OUTPUT"