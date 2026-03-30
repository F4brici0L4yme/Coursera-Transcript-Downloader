import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import queue
from playwright.sync_api import sync_playwright
import requests
import re
import time
import os

# --- Lógica de Limpieza de Texto ---
def limpiar_texto(texto_bruto):
    lineas = texto_bruto.split('\n')
    texto_limpio = []
    for linea in lineas:
        linea = linea.strip()
        if not linea or re.match(r'^\d+$', linea) or '-->' in linea or linea == "WEBVTT":
            continue
        texto_limpio.append(linea)
    return ' '.join(texto_limpio)

# --- Lógica Principal de Extracción ---
# Ahora recibe una 'cola' en lugar de un 'callback' directo
def procesar_curso(url_curso, cola):
    archivo_salida = "transcripciones_notebooklm.txt"
    
    def log(mensaje):
        cola.put(("log", mensaje)) # Enviamos el mensaje a la cola
        
    def finalizar():
        cola.put(("fin", None))

    with open(archivo_salida, "w", encoding="utf-8") as f:
        f.write("--- TRANSCRIPCIONES DEL MÓDULO ---\n\n")

    log("Iniciando Playwright...\n")
    
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir="./coursera_session",
                headless=False 
            )
            page = browser.new_page()
            
            log(f"Navegando al módulo: {url_curso[:40]}...\n")
            page.goto(url_curso, wait_until="domcontentloaded", timeout=60000) 
            
            log("Esperando 10 segundos para asegurar login y carga...\n")
            time.sleep(10)

            video_links = page.query_selector_all("a[href*='/lecture/']")
            hrefs = list(dict.fromkeys([link.get_attribute("href") for link in video_links]))
            
            log(f"¡Se encontraron {len(hrefs)} videos!\n" + "-"*30 + "\n")

            for i, href in enumerate(hrefs):
                full_url = f"https://www.coursera.org{href}"
                log(f"\n[{i+1}/{len(hrefs)}] Entrando a video...")
                
                max_reintentos = 2
                exito = False
                
                for intento in range(max_reintentos):
                    try:
                        page.goto(full_url, wait_until="load", timeout=45000)
                        
                        titulo_el = page.wait_for_selector("h1", timeout=15000)
                        titulo_video = titulo_el.inner_text() if titulo_el else f"Video_{i+1}"
                        log(f"\n   -> Título: {titulo_video}")

                        downloads_tab = page.wait_for_selector('button[data-testid="lecture-downloads-tab"]', timeout=15000)
                        downloads_tab.click()
                        
                        selector_link = 'a[href*="fileExtension=txt"]'
                        page.wait_for_selector(selector_link, timeout=10000)
                        link_element = page.query_selector(selector_link)
                        
                        if link_element:
                            raw_url = link_element.get_attribute("href")
                            url_txt = raw_url if raw_url.startswith("http") else f"https://www.coursera.org{raw_url}"
                            
                            log(" | Descargando...")
                            respuesta = requests.get(url_txt)
                            if respuesta.status_code == 200:
                                texto_limpio = limpiar_texto(respuesta.text)
                                
                                with open(archivo_salida, "a", encoding="utf-8") as f:
                                    f.write(f"# {titulo_video}\n")
                                    f.write(texto_limpio + "\n\n")
                                log(" | ¡Guardado!")
                                exito = True
                                break 
                        
                        time.sleep(2)

                    except Exception as e:
                        log(f"\n   [!] Error en intento {intento+1}: {str(e)[:50]}...")
                        time.sleep(3) 
                
                if not exito:
                    log(f"\n   [x] No se pudo procesar este video.")

            log(f"\n\n¡PROCESO COMPLETADO!\nArchivo generado: {os.path.abspath(archivo_salida)}")
            
        except Exception as e:
            log(f"\nError fatal: {e}")
        finally:
            browser.close()
            finalizar() # Avisa a Tkinter que ya terminó

# --- Interfaz Gráfica (GUI) ---
def iniciar_gui():
    ventana = tk.Tk()
    ventana.title("Coursera Downloader para NotebookLM")
    ventana.geometry("600x500")
    ventana.configure(padx=20, pady=20)

    cola_mensajes = queue.Queue() # Aquí se guardan los mensajes del hilo

    tk.Label(ventana, text="URL del módulo de Coursera:", font=("Arial", 10, "bold")).pack(anchor="w")
    entrada_url = tk.Entry(ventana, width=70)
    entrada_url.pack(pady=5)

    tk.Label(ventana, text="Registro de actividad:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,0))
    caja_texto = scrolledtext.ScrolledText(ventana, width=70, height=15, state=tk.DISABLED, bg="#f4f4f4")
    caja_texto.pack(pady=5)

    # Función que se ejecuta cada 100ms en el hilo principal buscando mensajes nuevos
    def revisar_cola():
        while not cola_mensajes.empty():
            tipo, dato = cola_mensajes.get()
            
            if tipo == "log":
                caja_texto.config(state=tk.NORMAL)
                caja_texto.insert(tk.END, dato)
                caja_texto.see(tk.END)
                caja_texto.config(state=tk.DISABLED)
            elif tipo == "fin":
                btn_iniciar.config(state=tk.NORMAL)
                return # Detenemos la revisión
        
        # Volver a ejecutarse en 100 milisegundos
        ventana.after(100, revisar_cola)

    def boton_iniciar_click():
        url = entrada_url.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor, ingresa una URL válida.")
            return
        
        btn_iniciar.config(state=tk.DISABLED)
        caja_texto.config(state=tk.NORMAL)
        caja_texto.delete(1.0, tk.END)
        caja_texto.config(state=tk.DISABLED)
        
        # Iniciar la escucha de la cola
        ventana.after(100, revisar_cola)
        
        # Ejecutar Playwright pasando la cola como argumento
        hilo = threading.Thread(target=procesar_curso, args=(url, cola_mensajes))
        hilo.daemon = True
        hilo.start()

    btn_iniciar = tk.Button(ventana, text="Iniciar Extracción", bg="#2e7d32", fg="white", font=("Arial", 12, "bold"), command=boton_iniciar_click)
    btn_iniciar.pack(pady=15)

    ventana.mainloop()

if __name__ == "__main__":
    iniciar_gui()