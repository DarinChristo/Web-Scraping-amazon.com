import requests
from bs4 import BeautifulSoup
import mysql.connector
import time

# MySQL Connection Setup
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="system",
        database="amazon_products"
    )

# Insert product into MySQL
def insert_product(product):
    conn = connect_db()
    cursor = conn.cursor()

    query = "INSERT INTO products (asin, title, price, rating, link, reviews) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (product['asin'], product['title'], product['price'], product['rating'], product['link'], product['reviews'])
    cursor.execute(query, values)

    conn.commit()
    cursor.close()
    conn.close()

# Scrape products from Amazon.com with pagination and full title
def search_amazon_products(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    page = 1
    while True:
        url = f"https://www.amazon.com/s?k={query}&page={page}"
        print(f"\nScraping page {page}...")

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}. Status code: {response.status_code}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.find_all("div", {"data-component-type": "s-search-result"})

        valid_count = 0

        for product in products:
            asin = product.get("data-asin", "").strip()
            if not asin or len(asin) != 10:
                continue

            title_elem = product.find("h2")
            if not title_elem:
                continue

            link_elem = title_elem.find("a")
            if link_elem and link_elem.has_attr("title"):
                title = link_elem["title"].strip()
            else:
                title = title_elem.get_text(strip=True)

            link = f"https://www.amazon.com{link_elem['href']}" if link_elem and link_elem.has_attr('href') else "N/A"

            price_elem = product.select_one("span.a-price span.a-offscreen")
            if not price_elem:
                continue
            price = price_elem.get_text(strip=True)

            rating_elem = product.select_one("span.a-icon-alt")
            rating = rating_elem.get_text(strip=True) if rating_elem else "N/A"

            review_elem = product.select_one("span.a-size-base.s-underline-text")
            reviews = review_elem.get_text(strip=True) if review_elem else "N/A"

            product_data = {
                "asin": asin,
                "title": title,
                "price": price,
                "rating": rating,
                "link": link,
                "reviews": reviews
            }

            print(product_data)
            insert_product(product_data)
            valid_count += 1
            time.sleep(1)  # Be polite

        if valid_count == 0:
            print("No valid products found on this page. Exiting.")
            break

        page += 1
        time.sleep(2)

# Run the scraper
if __name__ == "__main__":
    keyword = input("Enter product to search on Amazon.com: ")
    search_amazon_products(keyword)
