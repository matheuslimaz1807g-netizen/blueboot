"""
affiliates/mercadolivre.py — Mercado Livre affiliate link via Selenium & Brave.

Uses the local Brave profile to scrape the affiliate link directly from
the ML platform, exactly as requested by the user.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Optional

def fechar_brave():
    try:
        if os.name == 'nt':
            subprocess.call(['taskkill', '/F', '/IM', 'brave.exe'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.call(['pkill', '-f', 'brave'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def gerar_link_mercadolivre_sync(url: str) -> Optional[str]:
    """
    Synchronous function that opens Brave, fetches the ML affiliate link,
    and returns it. Requires the user to have Brave installed and closed 
    prior to execution if they want to use the default profile lock freely.
    """
    import pyperclip
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    
    options = Options()

    if os.name == 'nt':
        # 🚨 WINDOWS (Usa o Brave do Usuário)
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        user_data_dir = r"C:\Users\mathe\AppData\Local\BraveSoftware\Brave-Browser\User Data"
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        fechar_brave()
        time.sleep(1)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # 🚨 LINUX / VPS DOCKER (Usa Chromium headless lendo a pasta do seu Brave)
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new") # VPS não tem tela, precisa ser headless
        options.add_argument("--window-size=1920,1080")
        
        # Mapeia a pasta original do seu servidor antigo para o Chromium do Docker ler!
        user_data_dir = "/app/brave_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        # ou "ProfileBot" se era o que estava no seu código original
        # O Chrome Manager via service pega o chromedriver interno
        service = Service("/usr/bin/chromedriver")

        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"[ERROR] Local Chrome init failed: {e}")
            return None

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # 1: Close cookie banner if exists
        try:
            cookie_banner = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container"))
            )
            cookie_banner.find_element(By.TAG_NAME, "button").click()
            time.sleep(1)
        except Exception:
            pass

        # 2: Click "Access Product"
        acessar_produto = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]")
            )
        )
        acessar_produto.click()
        time.sleep(5)

        # 3: Click "Share" with retry
        try:
            compartilhar_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div/button"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            time.sleep(2)
        except Exception:
            try:
                compartilhar_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
                compartilhar_btn.click()
                time.sleep(2)
            except Exception as e:
                print(f"[ERROR] Failed to click 'Share': {e}")
                return None

        # 4: Click "Copy Link"
        copiar_botao = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button")
            )
        )
        copiar_botao.click()
        time.sleep(1)

        # 5: Get from clipboard
        link_afiliado = pyperclip.paste()
        return link_afiliado
    except Exception as e:
        print(f"❌ Error during ML Selenium flow: {e}")
        return None
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass
        fechar_brave()

async def convert(url: str, ml_token: str = "") -> Optional[str]:
    """
    Wrap the synchronous Selenium routine in an async thread pool 
    to prevent blocking the Telethon loop.
    """
    try:
        # Resolve shortlinks before throwing it to selenium
        import httpx
        if "meli.la" in url:
            async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
                r = await client.get(url)
                url = str(r.url)

        # Run Selenium synchronously in thread pool
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, gerar_link_mercadolivre_sync, url)
        
        # If it returns a sensible http link, return it.
        if result and result.startswith("http"):
            return result
        return None
    except Exception as exc:
        print(f"[ERROR] Selenium execution failed: {exc}")
        return None

def open_login_page_sync():
    """Opens Brave at ML login page."""
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    user_data_dir = r"C:\Users\mathe\AppData\Local\BraveSoftware\Brave-Browser\User Data"
    
    # Check if brave exists
    if not os.path.exists(brave_path):
        raise FileNotFoundError(f"Brave não encontrado em {brave_path}")

    fechar_brave()
    time.sleep(1)
    
    # Just open Brave directly with the profile
    # Using subprocess.Popen instead of Selenium so the user can interact freely
    try:
        subprocess.Popen([
            brave_path, 
            "https://www.mercadolivre.com.br/menu/login",
            f"--user-data-dir={user_data_dir}",
            "--profile-directory=Default"
        ])
    except Exception as e:
        print(f"[ERROR] Failed to open Brave: {e}")
        raise

async def open_login_page():
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, open_login_page_sync)
