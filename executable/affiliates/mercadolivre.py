"""
affiliates/mercadolivre.py — Mercado Livre affiliate link generation.

Suporta:
- Windows: Executa o Brave localmente de forma visível com o perfil do usuário.
- Linux (VPS): Executa Chromium headless, com suporte a injeção de cookies via .env.

FUTURE: multi-tenant
- Substituir ML_COOKIES global por um gerenciador de cookies atrelado ao tenant_id.
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils import expandir_link_async, fechar_brave


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
        # 🚨 LINUX / VPS DOCKER (Usa Chromium headless lendo a pasta local)
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # Removido --headless=new para rodar como navegador real na tela virtual (Xvfb) e evitar block
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Pasta de perfil (Volume mapeado no Docker)
        user_data_dir = "/app/brave_profile"
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--profile-directory=Default")
        
        # Tenta usar o driver do sistema
        service = Service("/usr/bin/chromedriver")
        
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"[ERROR] ML ChromeDriver init failed no Linux: {e}")
            return None

    try:
        # INJEÇÃO DE COOKIES (Evita login manual na VPS)
        ml_cookies_str = os.getenv("ML_COOKIES", "").strip()
        if ml_cookies_str:
            # Precisa estar no domínio para injetar cookies
            driver.get("https://www.mercadolivre.com.br/robots.txt")
            for cookie_chunk in ml_cookies_str.split(';'):
                cookie_chunk = cookie_chunk.strip()
                if not cookie_chunk or '=' not in cookie_chunk:
                    continue
                name, value = cookie_chunk.split('=', 1)
                driver.add_cookie({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.mercadolivre.com.br'
                })

        driver.get(url)
        wait = WebDriverWait(driver, 15)
        print(f"[DEBUG] ML carregou a página: {driver.title}")

        # 1: Fechar banner de cookies, se houver
        try:
            cookie_banner = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container"))
            )
            cookie_banner.find_element(By.TAG_NAME, "button").click()
            time.sleep(1)
        except Exception:
            pass

        # 2: Clicar em "Acessar Produto" (caso seja uma página intermediária do meli.la)
        try:
            acessar_produto = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]")
                )
            )
            acessar_produto.click()
            time.sleep(5)
        except Exception:
            pass

        # 3: Clicar em "Compartilhar"
        try:
            compartilhar_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div/button"))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            time.sleep(2)
        except Exception:
            try:
                # Tenta segundo XPATH possível
                compartilhar_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button"))
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
                compartilhar_btn.click()
                time.sleep(2)
            except Exception as e:
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
            copiar_botao = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button")
                )
            )
            copiar_botao.click()
            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Falha ao clicar em 'Copiar Link': {e}")
            return None

        # 5: Recuperar o link copiado da área de transferência
        link_afiliado = pyperclip.paste()
        return link_afiliado

    except Exception as e:
        print(f"[ERROR] Erro durante o fluxo Selenium do ML: {e}")
        return None
    finally:
        try:
            if 'driver' in locals():
                driver.quit()
        except Exception:
            pass
        fechar_brave()


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    """
    Função pública unificada. Expande a URL e delega ao executor síncrono.
    """
    try:
        # Resolve shortlinks antes de passar para o Selenium
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
