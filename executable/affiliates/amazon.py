"""
affiliates/amazon.py — Amazon Associates affiliate link generation via SiteStripe.

Fluxo:
  1. Abre a URL do produto Amazon com cookies de sessão injetados.
  2. Clica em "Obter link" (#amzn-ss-get-link-button) na SiteStripe bar.
  3. Clica em "Copiar link de associado" (#amzn-ss-copy-affiliate-link-btn-announce).
  4. Captura o link gerado via clipboard ou input do DOM.

Autenticação: via cookie string (AMZ_COOKIES) no .env.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils import expandir_link_async, fechar_brave


def _get_clipboard() -> Optional[str]:
    """Lê conteúdo do clipboard (cross-platform)."""
    if os.name == "nt":
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return None
    else:
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return None


def _clear_clipboard() -> None:
    """Limpa o clipboard antes da operação para evitar falsos positivos."""
    if os.name == "nt":
        try:
            import pyperclip
            pyperclip.copy("")
        except Exception:
            pass
    else:
        try:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=b"", timeout=5,
            )
        except Exception:
            pass


def _inject_cookies(driver, cookies_str: str, domain: str) -> int:
    """
    Injeta cookies no driver Selenium para o domínio especificado.
    Retorna a quantidade de cookies injetados com sucesso.
    """
    injected = 0
    for chunk in cookies_str.split(";"):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        try:
            name, value = chunk.split("=", 1)
            name = name.strip()
            value = value.strip()

            for dom in [f".{domain}", domain, ".amazon.com.br", "amazon.com.br"]:
                try:
                    driver.add_cookie({
                        "name": name,
                        "value": value,
                        "domain": dom,
                        "path": "/",
                        "secure": True,
                        "httpOnly": False,
                        "expiry": 2147483647,
                    })
                    injected += 1
                    print(f"[Amazon] Cookie '{name}' injetado em {dom}")
                    break
                except Exception:
                    pass
        except Exception as e:
            print(f"[Amazon] Erro ao processar cookie: {e}")
    return injected


def _create_driver():
    """Cria e configura o driver Selenium."""
    options = Options()

    if os.name == "nt":
        from webdriver_manager.chrome import ChromeDriverManager

        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        options.binary_location = brave_path
        options.add_argument("--start-maximized")
        options.add_argument(
            f"--user-data-dir=C:\\Users\\{os.getlogin()}\\AppData\\Local\\"
            "BraveSoftware\\Brave-Browser\\User Data"
        )
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
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)

        try:
            from selenium_stealth import stealth
            stealth(
                driver,
                languages=["pt-BR", "pt"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
        except ImportError:
            print("[Amazon] selenium_stealth não disponível, continuando sem stealth.")

    return driver


def _gerar_link_amazon_sync(url: str, cookies_str: str) -> Optional[str]:
    """
    Gera link de associado da Amazon via SiteStripe (síncrono).

    Parâmetros
    ----------
    url         : URL completa do produto Amazon.
    cookies_str : String de cookies de autenticação da conta de associado.

    Fluxo:
      1. Navega até amazon.com.br para injetar cookies.
      2. Acessa a URL do produto.
      3. Clica em "Obter link" na barra SiteStripe.
      4. Clica em "Copiar link de associado".
      5. Captura o link do clipboard ou do DOM.
    """
    amz_cookies_str = cookies_str.strip() if cookies_str else ""
    if not amz_cookies_str:
        print("[Amazon] AMZ_COOKIES não definido. Impossível gerar link.")
        return None

    driver = _create_driver()

    try:
        # ── 1. Navegar para o domínio base e injetar cookies ──────────────────
        print("[Amazon] Navegando para amazon.com.br para injetar cookies...")
        driver.get("https://www.amazon.com.br")
        time.sleep(2)

        current_domain = driver.current_url.split("/")[2].replace("www.", "")
        print(f"[Amazon] Domínio detectado: {current_domain}")

        total = _inject_cookies(driver, amz_cookies_str, current_domain)
        print(f"[Amazon] Total de cookies injetados: {total}")
        time.sleep(1)

        # ── 2. Acessar a URL do produto ───────────────────────────────────────
        print(f"[Amazon] Acessando URL do produto: {url}")
        driver.get(url)
        time.sleep(4)

        print(f"[Amazon] Página carregada: {driver.title}")
        print(f"[Amazon] URL atual: {driver.current_url}")

        # Verificar se está logado (SiteStripe só aparece para associados logados)
        try:
            driver.find_element(By.ID, "amzn-ss-wrap")
            print("[Amazon] ✓ SiteStripe bar detectada — usuário autenticado.")
        except Exception:
            print("[Amazon] ⚠ SiteStripe bar NÃO detectada. Sessão pode ter expirado.")
            try:
                driver.save_screenshot("/app/sessions/amazon_no_sitestripe.png")
            except Exception:
                pass

        wait = WebDriverWait(driver, 15)

        # ── 3. Clicar em "Obter link" ────────────────────────────────────────
        print("[Amazon] Buscando botão 'Obter link'...")

        obter_link_selectors = [
            (By.ID, "amzn-ss-get-link-button"),
            (By.CSS_SELECTOR, "#amzn-ss-get-link-button"),
            (By.XPATH, "//button[contains(., 'Obter link')]"),
            (By.XPATH, "//a[contains(., 'Obter link')]"),
            (By.XPATH, "//span[contains(., 'Obter link')]"),
            (By.XPATH, "//*[contains(text(), 'Obter link')]"),
            (By.XPATH, "//button[contains(., 'Get link')]"),
            (By.CSS_SELECTOR, "[data-action='ss-get-short-link']"),
        ]

        obter_btn = None
        for by, selector in obter_link_selectors:
            try:
                print(f"[Amazon] Tentando selector: ({by}, {selector})")
                obter_btn = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((by, selector))
                )
                print(f"[Amazon] ✓ Botão 'Obter link' encontrado!")
                break
            except Exception:
                pass

        if not obter_btn:
            print("[Amazon] ✗ Botão 'Obter link' não encontrado com nenhum seletor.")
            try:
                driver.save_screenshot("/app/sessions/amazon_erro_obter_link.png")
            except Exception:
                pass
            return None

        # Scroll e clique
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            obter_btn,
        )
        time.sleep(1)

        # Limpa clipboard antes de copiar
        _clear_clipboard()

        obter_btn.click()
        print("[Amazon] Clicou em 'Obter link'.")
        time.sleep(3)

        # ── 4. Clicar em "Copiar link de associado" ──────────────────────────
        print("[Amazon] Buscando botão 'Copiar link de associado'...")

        copiar_selectors = [
            (By.ID, "amzn-ss-copy-affiliate-link-btn-announce"),
            (By.CSS_SELECTOR, "#amzn-ss-copy-affiliate-link-btn-announce"),
            (By.XPATH, "//span[@id='amzn-ss-copy-affiliate-link-btn-announce']"),
            (By.XPATH, "//button[contains(., 'Copiar link de associado')]"),
            (By.XPATH, "//span[contains(., 'Copiar link de associado')]"),
            (By.XPATH, "//*[contains(text(), 'Copiar link')]"),
            (By.XPATH, "//button[contains(., 'Copy affiliate link')]"),
            (By.CSS_SELECTOR, "[data-action='ss-copy-link']"),
        ]

        copiar_btn = None
        for by, selector in copiar_selectors:
            try:
                print(f"[Amazon] Tentando selector: ({by}, {selector})")
                copiar_btn = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((by, selector))
                )
                print(f"[Amazon] ✓ Botão 'Copiar link' encontrado!")
                break
            except Exception:
                pass

        if not copiar_btn:
            print("[Amazon] ✗ Botão 'Copiar link' não encontrado.")
            # Fallback: tentar capturar de um input/textarea visível
            link = _try_extract_link_from_dom(driver)
            if link:
                return link
            try:
                driver.save_screenshot("/app/sessions/amazon_erro_copiar.png")
            except Exception:
                pass
            return None

        copiar_btn.click()
        print("[Amazon] Clicou em 'Copiar link de associado'.")
        time.sleep(3)

        # ── 5. Capturar o link gerado ────────────────────────────────────────
        link_afiliado = _get_clipboard()
        print(f"[Amazon] Link do clipboard: {link_afiliado}")

        # Validação do link
        if link_afiliado and _is_valid_amazon_affiliate_link(link_afiliado):
            print(f"[Amazon] ✓ Link de associado capturado: {link_afiliado}")
            return link_afiliado

        # Fallback: tentar extrair do DOM
        print("[Amazon] Clipboard vazio ou inválido. Tentando extrair do DOM...")
        link_afiliado = _try_extract_link_from_dom(driver)

        if link_afiliado and _is_valid_amazon_affiliate_link(link_afiliado):
            print(f"[Amazon] ✓ Link extraído do DOM: {link_afiliado}")
            return link_afiliado

        print("[Amazon] ✗ Não foi possível capturar o link de associado.")
        try:
            driver.save_screenshot("/app/sessions/amazon_erro_captura.png")
        except Exception:
            pass
        return None

    except Exception as e:
        print(f"[Amazon] Erro geral: {e}")
        return None

    finally:
        try:
            if "driver" in locals():
                driver.quit()
        except Exception:
            pass
        fechar_brave()


def _try_extract_link_from_dom(driver) -> Optional[str]:
    """
    Tenta extrair o link de associado diretamente de inputs/textareas no DOM.
    """
    selectors = [
        # Input com o link de afiliado
        "//input[contains(@value, 'amzn.to')]",
        "//input[contains(@value, 'amazon.com.br') and contains(@value, 'tag=')]",
        "//textarea[contains(., 'amzn.to')]",
        "//textarea[contains(., 'amazon.com.br')]",
        # SiteStripe text box
        "//input[@id='amzn-ss-text-shortlink-textarea']",
        "//input[contains(@id, 'amzn-ss')]",
        "//textarea[contains(@id, 'amzn-ss')]",
    ]

    for xpath in selectors:
        try:
            element = driver.find_element(By.XPATH, xpath)
            value = element.get_attribute("value") or element.text
            if value and _is_valid_amazon_affiliate_link(value.strip()):
                return value.strip()
        except Exception:
            pass

    return None


def _is_valid_amazon_affiliate_link(link: str) -> bool:
    """Verifica se o link é um link válido de associado Amazon."""
    if not link:
        return False
    link = link.strip()
    return (
        ("amzn.to" in link)
        or ("amazon.com.br" in link and "tag=" in link)
        or ("amazon.com" in link and "tag=" in link)
    )


async def convert(original_link: str, amz_cookies: str = "") -> Optional[str]:
    """
    Gera um link de associado Amazon via SiteStripe.

    Parâmetros
    ----------
    original_link : URL do produto Amazon (encurtada ou completa).
    amz_cookies   : String de cookies de autenticação. Se não fornecido,
                    tenta ler da variável de ambiente AMZ_COOKIES como fallback.

    Retorna o link de associado gerado ou None em caso de falha.
    """
    # Usa o cookie recebido ou cai para a variável de ambiente como fallback
    cookies_str = amz_cookies.strip() if amz_cookies else os.getenv("AMZ_COOKIES", "").strip()

    # Expande links curtos (amzn.to)
    if "amzn.to" in original_link or len(original_link) < 80:
        expanded = await expandir_link_async(original_link)
    else:
        expanded = original_link

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, _gerar_link_amazon_sync, expanded, cookies_str
        )
        return result
    except Exception as exc:
        print(f"[Amazon] Execução falhou: {exc}")
        return None
