"""
mercadolivre.py — Geração de links de afiliado do Mercado Livre.

Usa Selenium com Chromium (Docker) ou Brave (Windows).
Baseado no mercadolivre_link_generator.py que funciona em produção.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Optional

from utils import expandir_link_async


def _gerar_link_mercadolivre_sync(url: str) -> str | None:
    """
    Gera link de afiliado do Mercado Livre usando Selenium.
    Mesma lógica do mercadolivre_link_generator.py que funciona em produção.
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()

    if os.name == 'nt':
        # Windows: Brave com perfil logado
        from webdriver_manager.chrome import ChromeDriverManager
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        user_data_dir = rf"C:\Users\{os.getlogin()}\AppData\Local\BraveSoftware\Brave-Browser\User Data"
        options.binary_location = brave_path
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        try:
            subprocess.call(['taskkill', '/F', '/IM', 'brave.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
        time.sleep(1)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Linux (Docker/VPS): Chromium
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        try:
            from selenium_stealth import stealth
            stealth(driver, languages=["pt-BR", "pt"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
        except: pass

    try:
        print(f"[DEBUG] Abrindo URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # --- STEP 1: Fechar cookie banner ---
        try:
            print("[DEBUG] Fechando cookie banner")
            cookie_banner = wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "cookie-consent-banner-opt-out__container")
                )
            )
            close_button = cookie_banner.find_element(By.TAG_NAME, "button")
            close_button.click()
            print("[DEBUG] Cookie banner fechado")
            time.sleep(1)
        except Exception:
            print("[DEBUG] Sem cookie banner")

        # --- STEP 2: Clicar "Ir para produto" / "Access Product" ---
        print("[DEBUG] Clicando em 'Ir para produto'")
        try:
            acessar_produto = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]",
                    )
                )
            )
            acessar_produto.click()
            print("[DEBUG] Clicou em 'Ir para produto'")
            time.sleep(5)
        except Exception as e:
            print(f"[DEBUG] XPATH fixo falhou: {e}")
            # Fallback: tenta por texto
            try:
                xpath_texto = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')] | //span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')]"
                ir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_texto)))
                ir_btn.click()
                print("[DEBUG] Clicou em 'Ir para produto' (fallback texto)")
                time.sleep(5)
            except Exception as e2:
                print(f"[ERROR] Falha ao clicar em 'Ir para produto': {e2}")
                return None

        # Trocar de aba se necessário
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print(f"[DEBUG] Trocado para nova aba: {driver.title}")

        # --- STEP 3: Clicar "Compartilhar" ---
        print("[DEBUG] Clicando em 'Compartilhar'")
        try:
            compartilhar_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div/button")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            print("[DEBUG] Clicou em 'Compartilhar'")
            time.sleep(2)
        except Exception as e:
            print(f"[DEBUG] Primeiro XPATH Compartilhar falhou: {e}")
            try:
                compartilhar_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button")
                    )
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
                compartilhar_btn.click()
                print("[DEBUG] Clicou em 'Compartilhar' (segundo XPATH)")
                time.sleep(2)
            except Exception as e2:
                print(f"[ERROR] Falha ao clicar em 'Compartilhar': {e2}")
                return None

        # --- STEP 4: Clicar "Copiar link" ---
        print("[DEBUG] Clicando em 'Copiar link'")
        try:
            copiar_botao = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button",
                    )
                )
            )
            copiar_botao.click()
            print("[DEBUG] Clicou em 'Copiar link'")
            time.sleep(2)
        except Exception as e:
            print(f"[DEBUG] XPATH Copiar link falhou: {e}")
            try:
                driver.find_element(By.XPATH, "//button[contains(., 'Copiar link')]").click()
                print("[DEBUG] Clicou em 'Copiar link' (fallback texto)")
                time.sleep(2)
            except:
                print("[ERROR] Falha ao clicar em 'Copiar link'")
                return None

        # --- STEP 5: Capturar link da área de transferência ---
        if os.name == 'nt':
            import pyperclip
            link_afiliado = pyperclip.paste()
        else:
            try:
                result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=5)
                link_afiliado = result.stdout.strip()
            except:
                link_afiliado = None

        print(f"[DEBUG] Link de afiliado: {link_afiliado}")
        return link_afiliado

    except Exception as e:
        print(f"[ERROR] Erro no ML: {e}")
        return None

    finally:
        print("[DEBUG] Fechando WebDriver")
        if 'driver' in locals():
            driver.quit()


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    """
    Converte um link do Mercado Livre em link de afiliado.
    
    1. Expande links encurtados (meli.la)
    2. Gera link de afiliado via Selenium
    3. Se falhar, retorna o link original (nunca aborta o pipeline)
    """
    try:
        if "meli.la" in url:
            url = await expandir_link_async(url)
            print(f"[DEBUG] Link meli.la expandido para: {url}")
        
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _gerar_link_mercadolivre_sync, url)
        
        if result:
            return result
        
        # Fallback: link original
        print(f"[WARNING] ML: Não foi possível gerar link de afiliado. Usando link original.")
        return url
        
    except Exception as exc:
        print(f"[ERROR] ML: Erro inesperado: {exc}")
        return url
