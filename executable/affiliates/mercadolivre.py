import os
import time
import asyncio
import json
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyperclip

import undetected_chromedriver as uc
from utils import fechar_brave, expandir_link_async

def _gerar_link_mercadolivre_sync(url: str) -> Optional[str]:
    """
    Função síncrona que executa o Selenium para gerar o link do ML.
    """
    options = Options()

    if os.name == 'nt':
        # 🚨 WINDOWS (Usa o Brave do Usuário)
        from webdriver_manager.chrome import ChromeDriverManager
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        user_data_dir = r"C:\Users\mathe\AppData\Local\BraveSoftware\Brave-Browser\User Data"
        
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        
        fechar_brave()
        time.sleep(1)
        
        service = Service(ChromeDriverManager().install())
        
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"[ERROR] ML ChromeDriver init failed no Windows: {e}")
            return None
    else:
        # 🚨 LINUX / VPS DOCKER (Usa Undetected Chromedriver para bypass e estabilidade)
        options.binary_location = "/usr/bin/brave-browser"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Pasta de perfil do Brave
        user_data_dir = "/app/brave_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        try:
            # O UC baixa o driver e remenda o binário automaticamente
            driver = uc.Chrome(options=options, driver_executable_path="/usr/bin/chromedriver")
        except Exception as e:
            print(f"[ERROR] Undetected Chromedriver (Brave) falhou: {e}")
            return None

    try:
        # INJEÇÃO DE COOKIES (Evita login manual na VPS)
        ml_cookies_str = os.getenv("ML_COOKIES", "").strip()
        if ml_cookies_str:
            driver.get("https://www.mercadolivre.com.br/robots.txt")
            for cookie_chunk in ml_cookies_str.split(';'):
                cookie_chunk = cookie_chunk.strip()
                if not cookie_chunk or '=' not in cookie_chunk: continue
                name, value = cookie_chunk.split('=', 1)
                driver.add_cookie({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.mercadolivre.com.br'
                })

        driver.get(url)
        wait = WebDriverWait(driver, 15)
        print(f"[DEBUG] ML carregou a página: {driver.title}")

        # 1: Fechar banner de cookies
        try:
            cookie_banner = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container")))
            close_button = cookie_banner.find_element(By.TAG_NAME, "button")
            close_button.click()
            time.sleep(1)
        except: pass

        # 2: Clicar em "Acessar Produto"
        try:
            acessar_produto = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]")))
            acessar_produto.click()
            time.sleep(5)
        except: pass

        # 3: Clicar em "Compartilhar"
        try:
            compartilhar_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div/button")))
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            time.sleep(2)
        except Exception:
            try:
                compartilhar_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button")))
                driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
                compartilhar_btn.click()
                time.sleep(2)
            except Exception as e:
                # Debug se falhar
                try:
                    driver.save_screenshot("/app/sessions/ml_error_compartilhar.png")
                    print(f"[ERROR] Screenshot de erro salvo em /app/sessions/ml_error_compartilhar.png")
                except Exception as print_e:
                    print(f"[ERROR] Não foi possível salvar o screenshot: {print_e}")
                    try:
                        with open("/app/sessions/ml_error_page.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        print("[ERROR] HTML salvo em /app/sessions/ml_error_page.html")
                    except Exception as html_e:
                        print(f"[ERROR] HTML falhou: {html_e}")
                print(f"[ERROR] Falha ao clicar em 'Compartilhar': {e}")
                return None

        # 4: Clicar em "Copiar Link"
        try:
            copiar_botao = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Copiar link')]")))
            copiar_botao.click()
        except:
            # Fallback por XPATH completo
            copiar_botao = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button")))
            copiar_botao.click()
        
        time.sleep(2)
        link_afiliado = pyperclip.paste()
        
        if link_afiliado and "mercadolivre.com.br" in link_afiliado:
            return link_afiliado
        return None

    except Exception as e:
        print(f"[ERROR] Erro durante o fluxo Selenium do ML: {e}")
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
        
        if result and result.startswith("http"):
            return result
        return None
    except Exception as exc:
        print(f"[ERROR] Execução do Selenium falhou: {exc}")
        return None
