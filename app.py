from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import json
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def scrape_pharmeasy(medicine_name):
    url = f"https://pharmeasy.in/search/all?name={medicine_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        # Add a delay to prevent rate limiting
        time.sleep(1)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Print response status and first 500 characters of content for debugging
        print(f"Response Status: {response.status_code}")
        print(f"Response Preview: {response.text[:500]}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try different possible selectors
        medicine_items = []
        
        # Method 1: Try finding by data-test-id
        items = soup.find_all(attrs={"data-test-id": "product-card"})
        if items:
            print(f"Found {len(items)} items using data-test-id")
            medicine_items = items
            
        # Method 2: Try finding by class that contains 'ProductCard'
        if not medicine_items:
            items = soup.find_all("div", class_=lambda x: x and "ProductCard" in x)
            if items:
                print(f"Found {len(items)} items using ProductCard class")
                medicine_items = items
        
        # Method 3: Try finding anchor tags with medicine links
        if not medicine_items:
            items = soup.find_all("a", href=lambda x: x and "/online-medicine-order/" in x)
            if items:
                print(f"Found {len(items)} items using anchor tags")
                medicine_items = items

        results = []
        for item in medicine_items:
            try:
                # Try different methods to extract information
                name = None
                price = None
                url = None
                
                # Try to find name
                name_elem = (
                    item.find(attrs={"data-test-id": "product-name"}) or
                    item.find(class_=lambda x: x and "medicineName" in x) or
                    item.find("h1") or
                    item.find("h2")
                )
                if name_elem:
                    name = name_elem.text.strip()
                
                # Try to find price
                price_elem = (
                    item.find(attrs={"data-test-id": "product-price"}) or
                    item.find(class_=lambda x: x and "Price" in x)
                )
                if price_elem:
                    price = price_elem.text.strip()
                
                # Try to find URL
                url_elem = item.find("a", href=True) if item.name != "a" else item
                if url_elem and url_elem.get("href"):
                    url = f"https://pharmeasy.in{url_elem['href']}" if url_elem['href'].startswith('/') else url_elem['href']
                
                # Only add to results if URL is present
                if url:
                    results.append({
                        "name": name or "Name not found",
                        "price": price or "Price not found",
                        "url": url
                    })
                    
            except Exception as e:
                print(f"Error processing item: {str(e)}")
                continue
        
        return results
        
    except requests.RequestException as e:
        print(f"Request failed: {str(e)}")
        return [{"error": f"Request failed: {str(e)}"}]
    except Exception as e:
        print(f"Scraping failed: {str(e)}")
        return [{"error": f"Scraping failed: {str(e)}"}]

@app.route('/search_medicines', methods=['POST'])
def search_medicines():
    try:
        data = request.json
        medicines = data.get("medicines", [])
        results = {}

        for medicine in medicines:
            scraped_data = scrape_pharmeasy(medicine)
            # Filter out entries without a URL
            filtered_data = [item for item in scraped_data if "url" in item and item["url"] != "URL not found"]
            results[medicine] = filtered_data

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)