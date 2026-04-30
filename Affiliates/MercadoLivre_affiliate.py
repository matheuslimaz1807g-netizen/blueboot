"""
mercadolivre_link_generator.py
--------------------------------
Automates the process of generating affiliate links on Mercado Livre using Selenium with Brave browser.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pyperclip
import time

def gerar_link_mercadolivre(url: str) -> str | None:
    """
    Generates a Mercado Livre affiliate link using Selenium automation.
    """
    print("[DEBUG] Starting gerar_link_mercadolivre")

    # ==========================================
    # 🚨 CAMINHOS PARA O BRAVE NO WINDOWS
    # ==========================================
    # Caminho do executável do Brave (Padrão Windows 64-bits)
    brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    
    # Caminho do seu perfil logado (User Data) - Onde seus cookies estão
    user_data_dir = r"C:\Users\mathe\AppData\Local\BraveSoftware\Brave-Browser\User Data"

    # Configurações do Navegador
    options = Options()
    options.binary_location = brave_path
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")
    
    # 🔥 Usando o seu perfil logado para não pedir senha de novo
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--profile-directory=Default")

    try:
        # Baixa e gerencia o ChromeDriver compatível automaticamente
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"[ERROR] Falha ao iniciar o ChromeDriver: {e}")
        print("\n🚨 ATENÇÃO: O erro acima geralmente acontece porque o Brave já está aberto.")
        print("Feche TODAS as janelas do Brave antes de rodar o bot para ele conseguir usar seu perfil!\n")
        return None

    try:
        print(f"[DEBUG] Opening URL: {url}")
        driver.get(url)
        wait = WebDriverWait(driver, 20)

        # --- STEP 1: Handle cookie consent banner ---
        try:
            print("[DEBUG] Trying to close cookie banner")
            cookie_banner = wait.until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "cookie-consent-banner-opt-out__container")
                )
            )
            close_button = cookie_banner.find_element(By.TAG_NAME, "button")
            close_button.click()
            print("🍪 Cookie banner closed successfully")
            time.sleep(1)
        except Exception:
            print("🍪 No visible cookie banner found")

        # --- STEP 2: Click “Access Product” ---
        print("[DEBUG] Attempting to click 'Access product'")
        acessar_produto = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/main/div/div/div[2]/div[2]/section/section/section/div/ul/div/div[2]",
                )
            )
        )
        acessar_produto.click()
        print("[DEBUG] Clicked 'Access product'")
        time.sleep(5)

        # --- STEP 3: Click “Share” button (with retry logic) ---
        try:
            print("[DEBUG] Trying to click 'Share'")
            compartilhar_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[1]/nav/div/div[3]/div/div/button")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            print("[DEBUG] Clicked 'Share'")
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed to click 'Share': {e}")
            print("[DEBUG] Waiting 5 seconds before retry...")
            time.sleep(5)
            compartilhar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/nav/div/div[3]/div/div/button")
                )
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", compartilhar_btn)
            compartilhar_btn.click()
            print("[DEBUG] Clicked 'Share' on second attempt")
            time.sleep(2)

        # --- STEP 4: Click “Copy Link” ---
        print("[DEBUG] Trying to click 'Copy link'")
        copiar_botao = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "/html/body/div[1]/nav/div/div[3]/div/div[2]/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/button",
                )
            )
        )
        copiar_botao.click()
        print("[DEBUG] Clicked 'Copy link'")
        time.sleep(2)  # Ensure clipboard data is updated

        # --- STEP 5: Retrieve the affiliate link from clipboard ---
        link_afiliado = pyperclip.paste()
        print(f"[DEBUG] Affiliate link copied: {link_afiliado}")

        return link_afiliado

    except Exception as e:
        print("❌ Error:", e)
        return None

    finally:
        print("[DEBUG] Closing WebDriver session")
        if 'driver' in locals():
            driver.quit()