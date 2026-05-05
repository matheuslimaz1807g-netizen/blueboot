"""
mercadolivre.py — Geração de links de afiliado do Mercado Livre.

Estratégia:
1. Tenta usar a API oficial de afiliados do ML (sem Selenium)
2. Fallback: Selenium com Chromium (Docker) ou Brave (Windows)
3. Fallback final: retorna o link original para não travar o pipeline
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Optional

import httpx

from utils import expandir_link_async

# ── API de Afiliados do Mercado Livre ──────────────────────────────────────────
# Documentação: https://developers.mercadolivre.com.br/affiliate-program

ML_API_BASE = "https://api.mercadolibre.com"
ML_AFFILIATE_BASE = "https://www.mercadolivre.com.br"

# Padrão para extrair ID do produto de URLs do ML
_ML_PRODUCT_ID_PATTERN = re.compile(r"/ML[B|A]-\d{8,}(?:-\w+)?")
_ML_ITEM_ID_PATTERN = re.compile(r"ML[B|A]\d{8,}")


def _extract_product_id(url: str) -> str | None:
    """Extrai o ID do produto de uma URL do Mercado Livre."""
    # Tenta padrão /MLB-12345678
    match = _ML_PRODUCT_ID_PATTERN.search(url)
    if match:
        return match.group(0).strip("/")
    
    # Tenta padrão MLB12345678 direto
    match = _ML_ITEM_ID_PATTERN.search(url)
    if match:
        return match.group(0)
    
    return None


async def _convert_via_api(url: str, ml_token: str) -> str | None:
    """
    Tenta converter via API oficial de afiliados do ML.
    Usa o token do programa de afiliados para gerar link com tag.
    """
    if not ml_token:
        return None
    
    product_id = _extract_product_id(url)
    if not product_id:
        return None
    
    try:
        # API do ML para gerar link de afiliado
        # Formato: https://www.mercadolivre.com.br/item/{ID}/redirect?tag={TOKEN}
        affiliate_url = f"{ML_AFFILIATE_BASE}/item/{product_id}/redirect?tag={ml_token}"
        
        # Verifica se o link é válido fazendo uma requisição HEAD
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.head(affiliate_url, follow_redirects=False)
            if resp.status_code < 400:
                return affiliate_url
        
        # Alternativa: formato direto com tag
        affiliate_url = f"{ML_AFFILIATE_BASE}/item/{product_id}?tag={ml_token}"
        return affiliate_url
        
    except Exception as exc:
        print(f"[DEBUG] API ML falhou: {exc}")
        return None


async def _convert_via_selenium(url: str) -> str | None:
    """
    Tenta converter via Selenium (fallback).
    Só funciona se Chromium/Brave estiver disponível.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        return None

    options = Options()
    
    if os.name == 'nt':
        # Windows: usa Brave com perfil logado
        from webdriver_manager.chrome import ChromeDriverManager
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir=C:\\Users\\{os.getlogin()}\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")
        options.add_argument("--profile-directory=Default")
        try:
            subprocess.call(['taskkill', '/F', '/IM', 'brave.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: pass
        time.sleep(1)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Linux (Docker): usa Chromium headless
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        try:
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
            try:
                from selenium_stealth import stealth
                stealth(driver, languages=["pt-BR", "pt"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
            except: pass
        except Exception as e:
            print(f"[DEBUG] Chromium não disponível no Docker: {e}")
            return None

    try:
        print(f"[DEBUG] Selenium: Abrindo {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # Fechar cookie banner
        try:
            cookie_banner = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container")))
            cookie_banner.find_element(By.TAG_NAME, "button").click()
            time.sleep(1)
        except: pass

        # Clicar "Ir para produto"
        try:
            xpath_ir = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')] | //span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')] | /html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]"
            ir_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_ir)))
            ir_btn.click()
            time.sleep(6)
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
        except Exception as e:
            print(f"[DEBUG] Selenium: Falha ao ir para produto: {e}")
            return None

        # Compartilhar
        try:
            xpath_comp = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'compartilhar')] | //div[contains(@role, 'button') and contains(., 'Compartilhar')]"
            comp_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_comp)))
            driver.execute_script("arguments[0].scrollIntoView(true);", comp_btn)
            comp_btn.click()
            time.sleep(3)
        except:
            return None

        # Copiar link
        try:
            xpath_copy = "/html/body/div[1]/nav/div/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button"
            copy_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_copy)))
            copy_btn.click()
            time.sleep(2)
        except:
            try:
                driver.find_element(By.XPATH, "//button[contains(., 'Copiar link')]").click()
                time.sleep(2)
            except:
                return None

        # Capturar link
        if os.name == 'nt':
            import pyperclip
            link = pyperclip.paste()
        else:
            import subprocess
            result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=5)
            link = result.stdout.strip()
        
        if link and ("mercadolivre.com.br" in link or "meli.la" in link):
            return link
        
        return None

    except Exception as e:
        print(f"[DEBUG] Selenium ML: {e}")
        return None
    finally:
        try:
            if 'driver' in locals(): driver.quit()
        except: pass


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    """
    Converte um link do Mercado Livre em link de afiliado.
    
    Ordem de tentativas:
    1. API oficial de afiliados do ML (se ml_token estiver configurado)
    2. Selenium (se Chromium/Brave estiver disponível)
    3. Fallback: retorna o link original
    
    Args:
        url: URL do produto (pode ser meli.la encurtado)
        ml_token: Token do programa de afiliados do ML
    
    Returns:
        Link de afiliado ou link original como fallback
    """
    try:
        # Expande links encurtados
        if "meli.la" in url:
            url = await expandir_link_async(url)
            print(f"[DEBUG] ML: Link expandido: {url}")
        
        # Tentativa 1: API de afiliados
        if ml_token:
            api_result = await _convert_via_api(url, ml_token)
            if api_result:
                print(f"[DEBUG] ML: Convertido via API: {api_result}")
                return api_result
            print(f"[DEBUG] ML: API falhou, tentando Selenium...")
        
        # Tentativa 2: Selenium
        selenium_result = await _convert_via_selenium(url)
        if selenium_result:
            print(f"[DEBUG] ML: Convertido via Selenium: {selenium_result}")
            return selenium_result
        
        # Fallback: retorna link original
        print(f"[WARNING] ML: Não foi possível converter. Usando link original: {url}")
        return url
        
    except Exception as exc:
        print(f"[ERROR] ML: Erro inesperado: {exc}")
        return url
