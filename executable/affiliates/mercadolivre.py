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
    try:
        result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return None

def _gerar_link_mercadolivre_sync(url: str) -> Optional[str]:
    options = Options()

    if os.name == 'nt':
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
        options.binary_location = "/usr/bin/chromium"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        # Força User-Agent de Windows para combinar com a origem dos cookies
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        stealth(driver, languages=["pt-BR", "pt"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)

    try:
        # Injeção de Cookies
        ml_cookies_str = os.getenv("ML_COOKIES", "").strip()
        print(f"[DEBUG] ML_COOKIES detectado: {'SIM' if ml_cookies_str else 'NÃO'} (tamanho: {len(ml_cookies_str)} chars)")
        
        if ml_cookies_str:
            print("[DEBUG] Injetando cookies do Mercado Livre...")
            
            # Ir para domínio base primeiro
            driver.get("https://www.mercadolivre.com.br")
            time.sleep(1)
            
            # Detecta o domínio real (pode ter redirecionado para .com ou .com.ar dependendo da VPS)
            current_url = driver.current_url
            current_domain = current_url.split('/')[2].replace("www.", "")
            print(f"[DEBUG] Domínio detectado para cookies: {current_domain}")

            # Adiciona cookies com mais robustez
            cookies_injetados = 0
            for cookie_chunk in ml_cookies_str.split(';'):
                cookie_chunk = cookie_chunk.strip()
                if not cookie_chunk or '=' not in cookie_chunk: 
                    continue
                try:
                    name, value = cookie_chunk.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    
                    # Tenta injetar em múltiplos domínios
                    for domain in [f".{current_domain}", current_domain, ".mercadolivre.com.br", "mercadolivre.com.br"]:
                        try:
                            cookie_dict = {
                                'name': name,
                                'value': value,
                                'domain': domain,
                                'path': '/',
                                'secure': False,  # Tentar sem secure primeiro
                                'httpOnly': False,
                                'expiry': 2147483647
                            }
                            driver.add_cookie(cookie_dict)
                            cookies_injetados += 1
                            print(f"[DEBUG] Cookie '{name}' injetado em domínio {domain}")
                            break  # Se conseguiu, não tenta outros domínios
                        except:
                            pass
                except Exception as e:
                    print(f"[DEBUG] Erro ao processar cookie: {e}")
            
            print(f"[DEBUG] Total de cookies injetados: {cookies_injetados}")
            time.sleep(2)
        else:
            print("[INFO] ML_COOKIES não definido no ambiente. Verificar .env!")

        print(f"[DEBUG] Abrindo URL de perfil: {url}")
        driver.get(url)
        time.sleep(3)  # Aguardar carregamento
        wait = WebDriverWait(driver, 15)

        # 1. Fechar Cookies
        try:
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "cookie-consent-banner-opt-out__container"))).find_element(By.TAG_NAME, "button").click()
            time.sleep(1)
        except: pass

        # 2. Clicar em "Ir para produto"
        print("[DEBUG] Buscando botão 'Ir para produto'...")
        try:
            xpath_ir = "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')] | //span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ir para produto')] | /html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]"
            ir_para_produto = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_ir)))
            ir_para_produto.click()
            print("[DEBUG] Clicou em 'Ir para produto'.")
            time.sleep(6) 
            
            # 🚀 TROCA DE ABA: Se abriu uma nova aba, pula para ela
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                print(f"[DEBUG] Trocado para nova aba do produto. Titulo: {driver.title}")
            
        except Exception as e:
            print(f"[ERROR] Falha ao entrar no produto: {e}")
            driver.save_screenshot("/app/sessions/erro_navegacao.png")
            return None

        # 3. Compartilhar
        print(f"[DEBUG] Página Final URL: {driver.current_url}")
        print(f"[DEBUG] Título da página atual: {driver.title}")
        
        # Check para Login Wall - verificação múltipla
        title_lower = driver.title.lower()
        is_login_wall = ("entre" in title_lower or "ingresa" in title_lower or "login" in title_lower or 
                         title_lower.strip() == "mercado libre")
        
        # Verificação adicional: checar se há elemento de usuário logado
        try:
            # Se não conseguir encontrar o menu do usuário logado, provavelmente não está autenticado
            driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Ir para') or contains(@class, 'my-account')]")
            is_login_wall = False  # Encontrou elemento de usuário, então está logado
        except:
            if is_login_wall:
                is_login_wall = True
        
        if is_login_wall:
            print("[WARNING] Detectada página de LOGIN. A sessão (ML_COOKIES) pode ter expirado ou ser inválida para este IP.")
            driver.save_screenshot("/app/sessions/login_wall_detectado.png")

        try:
            print("[DEBUG] Buscando botão 'Compartilhar'...")
            
            # Múltiplas variações de XPath
            xpaths_compartilhar = [
                # Português - botão
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'compartilhar')]",
                # Espanhol - botão
                "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'compartir')]",
                # Div com role=button
                "//div[contains(@role, 'button') and (contains(., 'Compartilhar') or contains(., 'Compartir'))]",
                # Procura por SVG + texto (alguns layouts)
                "//button[contains(@aria-label, 'Compartilhar')] | //button[contains(@aria-label, 'Compartir')]",
                # Procura por classe contendo share
                "//button[contains(@class, 'share')] | //button[contains(@class, 'compartilhar')]",
                # Último recurso: procura qualquer botão com SVG de compartilhar
                "//button//svg[contains(@viewBox, '24 24')] | //button//svg[@class*='icon']",
            ]
            
            compartilhar_btn = None
            for xpath in xpaths_compartilhar:
                try:
                    print(f"[DEBUG] Tentando XPath: {xpath[:50]}...")
                    compartilhar_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    print(f"[DEBUG] ✓ Botão encontrado com XPath!")
                    break
                except:
                    pass
            
            if not compartilhar_btn:
                raise Exception("Botão 'Compartilhar' não encontrado com nenhum XPath")
            
            # Scroll para garantir que está visível
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", compartilhar_btn)
            time.sleep(1)
            
            compartilhar_btn.click()
            print("[DEBUG] Clicou em 'Compartilhar'.")
            time.sleep(3)
        except Exception as e:
            driver.save_screenshot("/app/sessions/erro_compartilhar.png")
            print(f"[ERROR] Falha ao clicar em 'Compartilhar'. Detalhes: {e}")
            print(f"[DEBUG] Página HTML snippet: {driver.find_element(By.TAG_NAME, 'body').get_attribute('innerHTML')[:500]}")
            return None

        # 4. Copiar Link (XPATH DO USUARIO)
        print("[DEBUG] Buscando botão 'Copiar link' via XPATH direto...")
        try:
            xpath_copy_user = "/html/body/div[1]/nav/div/div[3]/div[2]/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button"
            copiar_botao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_copy_user)))
            copiar_botao.click()
            print("[DEBUG] Clicou em 'Copiar link'.")
        except Exception as e:
            print(f"[DEBUG] Falha no XPATH direto de Copiar: {e}")
            try:
                driver.find_element(By.XPATH, "//button[contains(., 'Copiar link')]").click()
            except: pass
        
        time.sleep(4)

        # 5. Captura Final
        link_afiliado = get_linux_clipboard() if os.name != 'nt' else __import__('pyperclip').paste()
        if not link_afiliado or "mercadolivre.com.br" not in link_afiliado and "meli.la" not in link_afiliado:
            try:
                # Tenta ler do input meli.la se existir
                link_afiliado = driver.find_element(By.XPATH, "//input[contains(@value, 'meli.la') or contains(@value, 'mercadolivre.com.br')]").get_attribute("value")
            except: pass

        print(f"[DEBUG] Link Final: {link_afiliado}")
        return link_afiliado if link_afiliado and ("mercadolivre.com.br" in link_afiliado or "meli.la" in link_afiliado) else None

    except Exception as e:
        print(f"[ERROR] Erro Geral ML: {e}")
        return None
    finally:
        try:
            if 'driver' in locals(): driver.quit()
        except: pass
        fechar_brave()


async def convert(url: str, ml_token: str = "") -> Optional[str]:
    try:
        if "meli.la" in url: url = await expandir_link_async(url)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _gerar_link_mercadolivre_sync, url)
    except Exception as exc:
        print(f"[ERROR] Execução falhou: {exc}")
        return None 