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
    query = """
        INSERT INTO products (asin, title, price, rating, link, reviews, specifications)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        product['asin'],
        product['title'],
        product['price'],
        product['rating'],
        product['link'],
        product['reviews'],
        product['specifications']
    )
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

# Get the total number of result pages
def get_total_pages(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    url = f"https://www.amazon.com/s?k={query}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    pagination = soup.select("span.s-pagination-item")
    pages = []
    for el in pagination:
        try:
            pages.append(int(el.get_text().strip()))
        except ValueError:
            continue
    return max(pages) if pages else 1

# Scrape Amazon results
def search_amazon_products(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
        "Accept-Language": "en-US,en;q=0.9"
    }

    total_pages = get_total_pages(query)
    print(f"\n📄 Total pages found: {total_pages}")

    for page in range(1, total_pages + 1):
        url = f"https://www.amazon.com/s?k={query}&page={page}"
        print(f"\n🔎 Scraping page {page}...")

        response = requests.get(url, headers=headers)
        if response.status_code != 200 or "captcha" in response.text.lower():
            print(f"Blocked or CAPTCHA on page {page}. Stopping.")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        products = soup.find_all("div", {"data-component-type": "s-search-result"})
        if not products:
            print("No products found. End of results.")
            break

        valid_count = 0
        for product in products:
            asin = product.get("data-asin", "").strip()
            if not asin or len(asin) != 10:
                continue

            h2 = product.find("h2")
            if not h2:
                continue

            link_tag = h2.find("a")
            full_title = (link_tag["title"].strip()
                          if link_tag and link_tag.has_attr("title")
                          else h2.get_text(strip=True))
            link = ("https://www.amazon.com" + link_tag['href']
                    if link_tag and link_tag.has_attr("href")
                    else "N/A")

            price_el = product.select_one("span.a-price span.a-offscreen")
            if not price_el:
                continue
            price = price_el.get_text(strip=True)

            rating_el = product.select_one("span.a-icon-alt")
            rating = rating_el.get_text(strip=True) if rating_el else "N/A"

            reviews_el = product.select_one("span.a-size-base.s-underline-text")
            reviews = reviews_el.get_text(strip=True) if reviews_el else "N/A"

            words = full_title.split()
            brand = words[0] if words else "Unknown"
            specs = " ".join(words[1:]) if len(words) > 1 else "N/A"

            product_data = {
                "asin": asin,
                "title": brand,
                "price": price,
                "rating": rating,
                "link": link,
                "reviews": reviews,
                "specifications": specs
            }

            print(product_data)
            insert_product(product_data)
            valid_count += 1
            time.sleep(1)

        if valid_count == 0:
            print("No valid products on this page. Stopping.")
            break

        time.sleep(2)

# Filter by brand/title and price range
def filter_data(title, min_price, max_price):
    conn = connect_db()
    cur = conn.cursor()
    query = """
        SELECT * FROM products
        WHERE title = %s
          AND REPLACE(REPLACE(price, '$', ''), ',', '') REGEXP '^[0-9]+(\.[0-9]{1,2})?$'
          AND CAST(REPLACE(REPLACE(price, '$', ''), ',', '') AS DECIMAL(10,2))
              BETWEEN %s AND %s
    """
    cur.execute(query, (title, min_price, max_price))
    results = cur.fetchall()

    if results:
        for row in results:
            print(row)
    else:
        print(f"No products found for '{title}' between ${min_price} and ${max_price}.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    keyword = input("Enter product to search on Amazon.com: ").strip()
    search_amazon_products(keyword)

    while True:
        title = input("\nEnter brand/title to filter (case‑sensitive): ").strip()
        if not title:
            print("⚠️ Empty input. Try again.")
            continue
        try:
            min_p = float(input("Enter minimum price (e.g., 50): ").strip())
            max_p = float(input("Enter maximum price (e.g., 200): ").strip())
        except ValueError:
            print("⚠️ Invalid price. Please enter numeric values.")
            continue

        filter_data(title, min_p, max_p)

        again = input("Filter again? (Yes/No): ").strip().lower()
        if again == 'no':
            print("✅ Exiting filter mode.")
            break
