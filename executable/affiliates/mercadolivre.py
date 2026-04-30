import os
import time
import asyncio
import subprocess
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

from utils import fechar_brave, expandir_link_async

def get_linux_clipboard():
    """
    Fallback para ler o clipboard no Linux usando xclip diretamente,
    já que o pyperclip às vezes falha em containers.
    """
    try:
        result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return None

def _gerar_link_mercadolivre_sync(url: str) -> Optional[str]:
    """
    Gera link de afiliado seguindo a lógica do GitHub adaptada para VPS.
    """
    options = Options()

    if os.name == 'nt':
        # 🚨 WINDOWS (Brave)
        from webdriver_manager.chrome import ChromeDriverManager
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir=C:\\Users\\{os.getlogin()}\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")
        options.add_argument("--profile-directory=Default")
        fechar_brave()
        time.sleep(1)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # 🚨 LINUX / VPS DOCKER (Chromium + Stealth)
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
        stealth(driver,
            languages=["pt-BR", "pt"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

    try:
        # INJEÇÃO DE COOKIES (Necessário se não houver login manual)
        ml_cookies_str = os.getenv("ML_COOKIES", "").strip()
        if ml_cookies_str:
            driver.get("https://www.mercadolivre.com.br/robots.txt")
            for cookie_chunk in ml_cookies_str.split(';'):
                cookie_chunk = cookie_chunk.strip()
                if not cookie_chunk or '=' not in cookie_chunk: continue
                name, value = cookie_chunk.split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': value.strip(), 'domain': '.mercadolivre.com.br'})

        print(f"[DEBUG] Abrindo URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # STEP 1: Fechar banner de cookies (Lógica do GitHub)
        try:
            print("[DEBUG] Tentando fechar banner de cookies")
            cookie_banner = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container")))
            close_button = cookie_banner.find_element(By.TAG_NAME, "button")
            close_button.click()
            time.sleep(1)
        except:
            print("[DEBUG] Banner de cookies não encontrado")

        # STEP 2: Clicar em "Acessar Produto" (XPATH do GitHub)
        print("[DEBUG] Tentando clicar em 'Acessar produto'")
        try:
            acessar_produto = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]")))
            acessar_produto.click()
            print("[DEBUG] Clicou em 'Acessar produto'")
            time.sleep(5)
        except Exception as e:
            print(f"[WARNING] Falha ao clicar em acessar produto (pode já estar na página): {e}")

        # STEP 3: Clicar em "Compartilhar" (XPATH do GitHub com retry)
        try:
            print("[DEBUG] Tentando clicar em 'Compartilhar'")
            compartilhar_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button")))
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            print("[DEBUG] Clicou em 'Compartilhar'")
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Falha no primeiro clique de 'Compartilhar', tentando retry...")
            time.sleep(5)
            compartilhar_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button")))
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            print("[DEBUG] Clicou em 'Compartilhar' no retry")
            time.sleep(2)

        # STEP 4: Clicar em "Copiar Link" (XPATH do GitHub)
        print("[DEBUG] Tentando clicar em 'Copiar link'")
        copiar_botao = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button")))
        copiar_botao.click()
        print("[DEBUG] Clicou em 'Copiar link'")
        time.sleep(3)

        # STEP 5: Recuperar o link (Tenta xclip no Linux, pyperclip no Windows)
        if os.name == 'nt':
            import pyperclip
            link_afiliado = pyperclip.paste()
        else:
            link_afiliado = get_linux_clipboard()
            # Fallback se xclip falhar
            if not link_afiliado:
                try:
                    link_input = driver.find_element(By.XPATH, "//input[contains(@value, 'mercadolivre.com.br')]")
                    link_afiliado = link_input.get_attribute("value")
                except: pass

        print(f"[DEBUG] Link capturado: {link_afiliado}")
        
        if link_afiliado and "mercadolivre.com.br" in link_afiliado:
            return link_afiliado
            
        return None

    except Exception as e:
        print(f"[ERROR] Erro no fluxo Selenium do ML: {e}")
        return None
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except: pass
        fechar_brave()


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    try:
        if "meli.la" in url:
            url = await expandir_link_async(url)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _gerar_link_mercadolivre_sync, url)
        return result
    except Exception as exc:
        print(f"[ERROR] Execução falhou: {exc}")
        return None
