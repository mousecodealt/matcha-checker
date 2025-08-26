import requests
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import datetime
import time
import os
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()


# ======================
# Configuration
# ======================

# Products 
PRODUCTS = [
    # from ippodo tea
    ("https://ippodotea.com/products/sayaka-100g", "Sayaka Matcha 100g"),
    ("https://ippodotea.com/collections/all/products/sayaka-no-mukashi", "Sayaka Matcha 40g"),
    ("https://ippodotea.com/collections/all/products/horai-no-mukashi", "Horai 20g"),
    ("https://ippodotea.com/collections/all/products/ummon-no-mukashi-20g", "Ummon 20g"),
    ("https://ippodotea.com/collections/all/products/ummon-no-mukashi-40g", "Ummon 40g"),

    # from rockymatcha.com
    ("https://www.rockysmatcha.com/products/rockys-matcha-tsujiki-blend-matcha-20g?_pos=13&_sid=cd0ee3081&_ss=r",
     "Rocky Matcha Tsujiki Ceremonial Blend Matcha 20g"),
    ("https://www.rockysmatcha.com/products/rockys-matcha-shirakawa-ceremonial-blend-matcha-100g?_pos=14&_sid=cd0ee3081&_ss=r",
     "Rocky Matcha Shirakawa Ceremonial Blend Matcha 100g"),
    ("https://www.rockysmatcha.com/products/rocky-s-matcha-for-saie-ceremonial-blend-matcha-20g?_pos=15&_sid=cd0ee3081&_ss=r",
     "Rocky Matcha for Saie Ceremonial Blend Matcha 20g"),
    ("https://www.rockysmatcha.com/products/rockys-matcha-ceremonial-blend-matcha-100g?_pos=16&_sid=cd0ee3081&_ss=r",
     "Rocky Matcha Ceremonial Blend Matcha 100g"),
    ("https://www.rockysmatcha.com/products/rockys-matcha-osada-ceremonial-blend-matcha-20g?_pos=12&_sid=6a0cedabe&_ss=r",
     "Rocky Matcha Osada Ceremonial Blend Matcha 20g"),
    ("https://www.rockysmatcha.com/products/rockys-matcha-ceremonial-blend-matcha-20g?_pos=11&_sid=6a0cedabe&_ss=r",
     "Rocky Matcha Ceremonial Blend Matcha 20g"),

    # from Marukyu Koyamaen (via UjichaMatcha)
    ("https://ujichamatcha.com/products/wakatake-marukyu-koyamaen?variant=41732342644810", "Wakatake 100g bag"),
    ("https://ujichamatcha.com/products/wakatake-marukyu-koyamaen?variant=42028381470794", "Wakatake 100g tin"),

    # testing examples
    # ("https://ujichamatcha.com/products/chaginza-matcha-uogashi-meicha", "Testing Ujimatcha ChaGinza"),
    # ("https://ippodotea.com/collections/all/products/uji-shimizu-sticks", "Testing Ippodotea Uji Shimizu"),
    # ("https://www.rockysmatcha.com/products/rockys-matcha-houjicha-20g?_pos=3&_fid=929ef2a94&_ss=c", "Testing Rocky Matcha Houjicha 20g"),
]

CHECK_INTERVAL = 300  # seconds 
START_HOUR = 3         # 3 AM
END_HOUR = 9           # 9 AM

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAILS = os.getenv("RECEIVER_EMAILS", "").split(",")


def check_stock(url):
    """
    Loads the page with Playwright (headless), parses with BeautifulSoup,
    checks 'sold out' phrases first, then inspects a submit button for 'add to cart' if present.
    Returns True if appears in stock, False otherwise.
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = context.new_page()

        try:
            page.goto(url, timeout=30_000, wait_until="domcontentloaded")
            html = page.content()
        except PWTimeout:
            browser.close()
            return False
        except Exception:
            browser.close()
            return False
        finally:
            # close at end of with-block anyway; explicit close for clarity
            browser.close()

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(separator=" ").lower()

    sold_out_phrases = ["sold out", "out of stock", "currently unavailable", "notify me"]

    # Primary check: if page loudly says sold-out, assume False unless a live Add-to-Cart is present and enabled
    if any(phrase in page_text for phrase in sold_out_phrases):
        button = soup.find("button", {"type": "submit"})
        if button:
            text = (button.get_text(strip=True) or "").lower()
            is_disabled = button.has_attr("disabled") or "disabled" in (button.get("class") or [])
            add_phrases = ["add to cart", "add to bag", "add to basket"]
            if any(phrase in text for phrase in add_phrases) and not is_disabled:
                return True
        return False

    # No obvious sold-out text; check if there is an Add-to-Cart style button that is enabled
    button = soup.find("button", {"type": "submit"})
    if button:
        text = (button.get_text(strip=True) or "").lower()
        is_disabled = button.has_attr("disabled") or "disabled" in (button.get("class") or [])
        add_phrases = ["add to cart", "add to bag", "add to basket"]
        if any(phrase in text for phrase in add_phrases) and not is_disabled:
            return True

    # Fallback: if we can’t positively confirm add-to-cart, be conservative
    return False


def send_email(name, url):
    subject = f"{name} is now in Stock!"
    body = f"{name} is now available: {url}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(RECEIVER_EMAILS)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"📧 Email sent for {name}")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def is_within_check_hours():
    now = datetime.datetime.now()
    current_hour = now.hour
    return START_HOUR <= current_hour <= END_HOUR


if __name__ == "__main__":
    while True:
        if is_within_check_hours():
            for url, name in PRODUCTS:
                try:
                    print(f"🔍 Checking {name}...")
                    if check_stock(url):
                        send_email(name, url)
                    else:
                        print(f"❌ {name} still sold out.\n")
                except Exception as e:
                    print(f"⚠️ Error checking {name}: {e}")
        else:
            now = datetime.datetime.now().strftime("%H:%M")
            print(f"[SKIP {now}] Outside window {START_HOUR}:00–{END_HOUR}:00")

        print(f"Waiting {CHECK_INTERVAL} seconds before next check...\n")
        time.sleep(CHECK_INTERVAL)