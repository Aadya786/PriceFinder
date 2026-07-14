from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from price_parser import Price
import smtplib
from email.message import EmailMessage
import os

app = Flask(__name__)
CORS(app)
def send_email(user_email, book_title, book_price, book_url):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    
    if not mail_user or not mail_pass:
        return False
        
    msg = EmailMessage()
    msg["Subject"] = f" Price Alert: {book_title} is on sale!"
    msg["From"] = mail_user
    msg["To"] = user_email
    msg.set_content(f"We found '{book_title}' for only £{book_price}!\n\nLink: {book_url}")
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(mail_user, mail_pass)
            smtp.send_message(msg)
        return True
    except Exception:
        return False

@app.route("/api/scrape", methods=["POST"])
def scrape_and_email():
    data = request.json or {}
    user_email = data.get("email")
    keyword = data.get("keyword", "")
    alert_price = float(data.get("price", 30))

    results = []
    for page_num in range(1, 4): 
        url = f"http://books.toscrape.com/catalogue/page-{page_num}.html"
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if response.status_code != 200:
                break
        except:
            break
        
        soup = BeautifulSoup(response.text, "lxml")
        products = soup.find_all("article", class_="product_pod")
        for prod in products:
            title = prod.h3.a["title"]
            if keyword.lower() in title.lower():
                price_text = prod.select_one(".price_color").text
                price_float = Price.fromstring(price_text).amount_float
                results.append({
                    "title": title,
                    "price": price_float,
                    "url": f"http://books.toscrape.com/catalogue/{prod.h3.a['href']}".replace("catalogue/catalogue/", "catalogue/")
                })

    deals = [b for b in results if b["price"] <= alert_price]
    emails_sent = 0
    if user_email and len(deals) > 0:
        for deal in deals[:3]:
            if send_email(user_email, deal["title"], deal["price"], deal["url"]):
                emails_sent += 1

    return jsonify({
        "status": "success",
        "total_found": len(results),
        "deals_found": len(deals),
        "emails_sent": emails_sent
    })
