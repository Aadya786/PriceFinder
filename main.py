import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from price_parser import Price
import smtplib
from email.message import EmailMessage

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
MAIL_USER = " " # ADD YOUR EMAIL
MAIL_PASS = " " # ADD YOUR GOOGLE APP PASSWORD
MAIL_TO = "recipient_email@gmail.com"

st.set_page_config(page_title="Book SaleFinder", page_icon="📚", layout="centered")
st.title("Price Finder + Notifier")

st.write("Find books from [Books to Scrape](https://books.toscrape.com/index.html) and get email alerts if they match your budget!")

if "found_books" not in st.session_state:
    st.session_state.found_books = []
if "search_clicked" not in st.session_state:
    st.session_state.search_clicked = False

user_email = st.text_input("Your Email Address (Where to send alerts):", placeholder="example@gmail.com")
book_keyword = st.text_input("Book Title /  Keyword:", placeholder="e.g., Attic, Music, History")
alert_price = st.slider("Alert Me If Price Is Under (£):", min_value=5.0, max_value=60.0, value=30.0, step=1.0)

submit_button = st.button("Search and Track")

def search_books_site(keyword):
    results = []
    headers = {"User-Agent": "Mozilla/5.0"}

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_pages = 50

    try:
        for page_num in range(1, total_pages + 1):
            progress_bar.progress(page_num / total_pages)
            status_text.text(f"Scanning page {page_num} of {total_pages}...")

            url = f"http://books.toscrape.com/catalogue/page-{page_num}.html"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, "lxml")
            products = soup.find_all("article", class_="product_pod")

            for prod in products:
                title = prod.h3.a["title"]

                if keyword.lower() in title.lower():
                    relative_link = prod.h3.a["href"]
                    full_link = f"http://books.toscrape.com/catalogue/{relative_link}".replace("catalogue/catalogue/", "catalogue/")

                    price_text = prod.select_one(".price_color").text
                    price_float = Price.fromstring(price_text).amount_float

                    results.append({
                        "Title": title,
                        "Current Price": price_float,
                        "URL": full_link
                    })
        
        progress_bar.empty()
        status_text.empty()
        return results

    except Exception as e:
        st.error(f"Error scraping website: {e}")
        return []    
    
def send_alert_email(to_email, book_title, actual_price, budget_price, link, status_type="Below Budget"):
    msg = EmailMessage()
    msg['Subject'] = f"SaleFinder Price Alert! ({status_type})"
    msg['From'] =  MAIL_USER
    msg['To'] = to_email

    body = (
        f"Good News! We found a match for your search.\n\n"
        f"Book: {book_title}\n"
        f"Current Price: £{actual_price:.2f}\n"
        f"Your Target Budget: £{budget_price:.2f}\n"
        f"Status: {status_type}\n\n"
        f"Link to buy: {link}"
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(MAIL_USER, MAIL_PASS)
            smtp.send_message(msg)
            return True
    except Exception as e:
        st.sidebar.error(f"Failed to send email: {e}")
        return False

if submit_button:
    if not user_email or not book_keyword:
        st.warning("Please fill out both your email address and a book keyword!")
    else:
        with st.spinner("Searching the bookstore..."):
            st.session_state.found_books = search_books_site(book_keyword)
            st.session_state.search_clicked = True

if st.session_state.search_clicked:
    if not st.session_state.found_books:
        st.info(f"No books found matching '{book_keyword}' across the entire catalog.")
    else:
        under_budget_books = []
        over_budget_books = []
        
        for book in st.session_state.found_books:
            if book['Current Price'] <= alert_price:
                under_budget_books.append(book)
            else:
                over_budget_books.append(book)
                
        selected_books = []

        st.header("Deals Found! (Below Budget)")
        if not under_budget_books:
            st.write("No matching books are within your budget right now.")
        else:
            if st.button("Email Me All Deals Below Budget"):
                with st.spinner("Sending all deal alerts..."):
                    all_success_count = 0
                    for book in under_budget_books:
                        email_success = send_alert_email(
                            user_email, book['Title'], book['Current Price'], alert_price, book['URL'], "Below Budget"
                        )
                        if email_success:
                            all_success_count += 1
                    if all_success_count > 0:
                        st.success(f"Sent {all_success_count} deal alert(s) to **{user_email}**!")
            
            st.write("Or select specific books manually below:")
            st.divider()

            for idx, book in enumerate(under_budget_books):
                st.markdown(f"### [{book['Title']}]({book['URL']})")
                st.write(f"**Current Price:** £{book['Current Price']:.2f}")
                
                want_email = st.checkbox(f"Add to my custom email list", key=f"under_{idx}")
                if want_email:
                    book_copy = book.copy()
                    book_copy['status'] = "Below Budget Match"
                    selected_books.append(book_copy)
                st.divider()

        st.header("Out of Budget (Above Budget)")
        if not over_budget_books:
            st.write("No matching books exceed your budget limits.")
        else:
            if st.button("Email Me All Books Above Budget"):
                with st.spinner("Sending above-budget summaries..."):
                    above_success_count = 0
                    for book in over_budget_books:
                        email_success = send_alert_email(
                            user_email, book['Title'], book['Current Price'], alert_price, book['URL'], "Above Budget"
                        )
                        if email_success:
                            above_success_count += 1
                    if above_success_count > 0:
                        st.success(f"Sent {above_success_count} price summary alert(s) to **{user_email}**!")
            
            st.write("Or select specific books manually below:")
            st.divider()

            for idx, book in enumerate(over_budget_books):
                st.markdown(f"### [{book['Title']}]({book['URL']})")
                st.write(f"**Current Price:** £{book['Current Price']:.2f} (Target: Under £{alert_price:.2f})")
                
                want_email = st.checkbox(f"Add to my custom email list", key=f"over_{idx}")
                if want_email:
                    book_copy = book.copy()
                    book_copy['status'] = "Above Budget Track"
                    selected_books.append(book_copy)
                st.divider()

        if selected_books:
            if st.button("Send Email Alerts for Selected Books"):
                with st.spinner("Sending custom choices email alert..."):
                    success_count = 0
                    for book in selected_books:
                        email_success = send_alert_email(
                            user_email, book['Title'], book['Current Price'], alert_price, book['URL'], book['status']
                        )
                        if email_success:
                            success_count += 1
                    
                    if success_count > 0:
                        st.success(f"Successfully emailed {success_count} customized book alert(s) to **{user_email}**!")
