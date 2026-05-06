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

from utils import expandir_link_async

def fechar_brave():
    if os.name == 'nt':
        try:
            subprocess.call(['taskkill', '/F', '/IM', 'brave.exe'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

def get_linux_clipboard():
    try:
        result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return None

def _gerar_link_mercadolivre_sync(url: str, ml_cookies_str: str) -> Optional[str]:
    options = Options()

    if os.name == 'nt':
        from webdriver_manager.chrome import ChromeDriverManager
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        options.binary_location = brave_path
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir=C:\\Users\\{os.getlogin()}\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data")
        options.add_argument("--profile-directory=Default")
        fechar_brave()
        time.sleep(1)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
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
        except:
            pass

    try:
        # Injeção de Cookies
        ml_cookies_str = (ml_cookies_str or "").strip()
        if ml_cookies_str:
            driver.get("https://www.mercadolivre.com.br/robots.txt")
            for cookie_chunk in ml_cookies_str.split(';'):
                cookie_chunk = cookie_chunk.strip()
                if not cookie_chunk or '=' not in cookie_chunk:
                    continue
                name, value = cookie_chunk.split('=', 1)
                driver.add_cookie({'name': name.strip(), 'value': value.strip(), 'domain': '.mercadolivre.com.br'})

        print(f"[DEBUG] Abrindo URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # 1. Fechar banner de cookie
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "cookie-consent-banner-opt-out__container"))).find_element(By.TAG_NAME, "button").click()
            print("[DEBUG] Cookie banner fechado")
            time.sleep(1)
        except:
            print("[DEBUG] Sem banner de cookie")

        # 2. Clicar em "Ir para produto"
        print("[DEBUG] Clicando em 'Ir para produto'")
        try:
            xpath_ir = "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]"
            ir_para_produto = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_ir)))
            ir_para_produto.click()
            print("[DEBUG] Clicou em 'Ir para produto'")
            time.sleep(6)

            # Troca de aba se abriu uma nova
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                print(f"[DEBUG] Trocado para nova aba. Titulo: {driver.title}")

        except Exception as e:
            print(f"[ERROR] Falha ao entrar no produto: {e}")
            return None

        # 3. Compartilhar — XPaths confirmados no teste local
        print(f"[DEBUG] Título da página atual: {driver.title}")
        SHARE_XPATHS = [
            "/html/body/div[1]/nav/div/div[3]/div[2]/div/button/span",  # confirmado funcionando
            "/html/body/div[1]/nav/div/div[3]/div[2]/div/button",        # pai do span
            "/html/body/div[1]/nav/div/div[3]/div/div/button",           # fallback
            "/html/body/div[2]/nav/div/div[3]/div/div/button",           # fallback 2
        ]

        clicou_compartilhar = False
        for xpath in SHARE_XPATHS:
            try:
                print(f"[DEBUG] Tentando XPath Compartilhar: {xpath}")
                btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                btn.click()
                print(f"[DEBUG] Compartilhar clicado! XPath usado: {xpath}")
                time.sleep(2)
                clicou_compartilhar = True
                break
            except:
                print(f"[DEBUG] XPath nao funcionou: {xpath}")
                continue

        if not clicou_compartilhar:
            print("[ERROR] Nenhum XPath funcionou para 'Compartilhar'.")
            return None

        # 4. Copiar Link — XPath confirmado no teste local
        print("[DEBUG] Tentando clicar em 'Copiar link'")
        try:
            xpath_copy = "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button"
            copiar_botao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_copy)))
            copiar_botao.click()
            print("[DEBUG] Copiar link clicado")
        except Exception as e:
            print(f"[ERROR] Falha ao clicar em 'Copiar link': {e}")
            return None

        time.sleep(4)

        # 5. Captura do link final
        if os.name == 'nt':
            import pyperclip
            link_afiliado = pyperclip.paste()
        else:
            link_afiliado = get_linux_clipboard()

        if not link_afiliado or ("mercadolivre.com.br" not in link_afiliado and "meli.la" not in link_afiliado):
            try:
                link_afiliado = driver.find_element(By.XPATH, "//input[contains(@value, 'meli.la') or contains(@value, 'mercadolivre.com.br')]").get_attribute("value")
            except:
                pass

        print(f"[DEBUG] Link Final: {link_afiliado}")
        return link_afiliado if link_afiliado and ("mercadolivre.com.br" in link_afiliado or "meli.la" in link_afiliado) else None

    except Exception as e:
        print(f"[ERROR] Erro Geral ML: {e}")
        return None
    finally:
        print("[DEBUG] Fechando WebDriver")
        try:
            if 'driver' in locals():
                driver.quit()
        except:
            pass
        fechar_brave()


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    """
    Converte um link do Mercado Livre em link de afiliado.
    """
    try:
        if "meli.la" in url:
            url = await expandir_link_async(url)
            print(f"[DEBUG] Link meli.la expandido para: {url}")

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _gerar_link_mercadolivre_sync, url, ml_token)

        if result:
            return result

        return url

    except Exception as exc:
        print(f"[ERROR] ML: Erro inesperado: {exc}")
        return url
