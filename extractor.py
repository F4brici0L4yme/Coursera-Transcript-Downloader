from playwright.sync_api import sync_playwright
import time

# Configuración
COURSE_URL = "https://www.coursera.org/learn/digital-twins/home/module/1"
OUTPUT_FILE = "urls.txt"

def run(playwright):
    # Mantenemos la sesión para no loguearnos cada vez
    browser = playwright.chromium.launch_persistent_context(
        user_data_dir="./coursera_session",
        headless=True # Cambia a True cuando verifiques que funciona
    )
    
    page = browser.new_page()
    captured_urls = []

    # 1. Ir a la página principal del curso/módulo
    page.goto(COURSE_URL)
    print("Esperando login... (tienes 15 segundos si no has iniciado sesión)")
    time.sleep(10)

    # 2. Obtener todos los links de lecciones de video
    # Usamos un selector más preciso para los items de la lista
    video_links = page.query_selector_all("a[href*='/lecture/']")
    hrefs = [link.get_attribute("href") for link in video_links]
    
    # Eliminar duplicados manteniendo el orden
    hrefs = list(dict.fromkeys(hrefs))
    
    print(f"Se encontraron {len(hrefs)} videos. Iniciando navegación...")

    for i, href in enumerate(hrefs):
        full_url = f"https://www.coursera.org{href}"
        print(f"[{i+1}/{len(hrefs)}] Procesando: {href}")
        
        try:
            page.goto(full_url, wait_until="networkidle")
            
            # 3. PASO CLAVE: Hacer clic en la pestaña "Downloads"
            # Usamos el data-testid que pusiste en tu ejemplo
            downloads_tab = page.wait_for_selector('button[data-testid="lecture-downloads-tab"]', timeout=10000)
            downloads_tab.click()
            
            # 4. Esperar a que aparezca el link que contiene "fileExtension=txt"
            # El selector busca un <a> cuyo href contenga ese texto
            selector_link = 'a[href*="fileExtension=txt"]'
            page.wait_for_selector(selector_link, timeout=5000)
            
            # Extraer el atributo href
            link_element = page.query_selector(selector_link)
            if link_element:
                raw_url = link_element.get_attribute("href")
                # Asegurarnos de que sea una URL completa
                final_url = raw_url if raw_url.startswith("http") else f"https://www.coursera.org{raw_url}"
                captured_urls.append(final_url)
                print(f"   ✓ URL capturada.")
            
            time.sleep(1) # Un pequeño respiro para no saturar

        except Exception as e:
            print(f"   × Error en este video (posiblemente no tiene transcript): {e}")

    # 5. Guardar resultados
    with open(OUTPUT_FILE, "w") as f:
        for url in captured_urls:
            f.write(url + "\n")
    
    print(f"\n¡Proceso finalizado! {len(captured_urls)} URLs guardadas en {OUTPUT_FILE}")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)