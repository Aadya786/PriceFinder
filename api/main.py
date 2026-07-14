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

def send_email(user_email, book_title, book_price, book_url, status_type):
    mail_user = os.environ.get("MAIL_USER")
    mail_pass = os.environ.get("MAIL_PASS")
    
    if not mail_user or not mail_pass:
        return False
        
    msg = EmailMessage()
    msg["Subject"] = f"SaleFinder Price Alert! ({status_type})"
    msg["From"] = mail_user
    msg["To"] = user_email
    
    body = (
        f"Good News! We found a match for your search.\n\n"
        f"Book: {book_title}\n"
        f"Current Price: £{book_price:.2f}\n"
        f"Status: {status_type}\n\n"
        f"Link to buy: {book_url}"
    )
    msg.set_content(body)
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(mail_user, mail_pass)
            smtp.send_message(msg)
        return True
    except Exception:
        return False

@app.route("/api/scrape", methods=["POST"])
def scrape_books():
    data = request.json or {}
    keyword = data.get("keyword", "")

    results = []
    for page_num in range(1, 6): 
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

    return jsonify({"status": "success", "books": results})

@app.route("/api/send-alerts", methods=["POST"])
def send_alerts():
    data = request.json or {}
    user_email = data.get("email")
    selected_books = data.get("books", [])
    
    if not user_email or not selected_books:
        return jsonify({"status": "error", "message": "Missing email or selected books"}), 400

    emails_sent = 0
    for book in selected_books:
        success = send_email(user_email, book["title"], book["price"], book["url"], book["status"])
        if success:
            emails_sent += 1

    return jsonify({"status": "success", "emails_sent": emails_sent})
