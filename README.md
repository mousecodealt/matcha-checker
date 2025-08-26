A Python script that monitors matcha products availability across multiple e-commerce websites (Ippodo, Rocky Matcha, Marukyu Koyamaen, etc.) and sends email alerts when items are back in stock.

Built with Playwright and BeautifulSoup to scrape product availability and Gmail SMTP for notifications.  

Features:
- Monitors multiple product URLs
- Detects “Add to Cart” vs “Sold Out” status
- Sends email notifications automatically
- Configurable check interval and time window
- Uses `.env` file to keep credentials safe

Installation:
Clone the repo:
```bash
git clone https://github.com/mousecodealt/matcha-checker.git
cd matcha-checker

Create a virtual environment and install dependencies:
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

pip install -r requirements.txt
python -m playwright install

Configuration:
- Copy .env.example → .env:
- Fill in your email settings inside .env:
SENDER_EMAIL → your Gmail address
SENDER_PASSWORD → Gmail App Password (not your real login)
RECEIVER_EMAILS → one or more recipient addresses
