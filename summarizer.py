import feedparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import os
import time

# Configuration
RSS_URL = "https://www.neakriti.gr/rss.xml"
ALLOWED_SECTIONS = ["/kriti/", "/ellada/"]
DB_FILE = "processed_articles.json"
SUMMARY_DIR = "summaries"

# Initialize Gemini 3 Fast (using the 2026 Flash model)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-3.0-flash') # Gemini 3 Fast equivalent

def get_full_text(url):
    """Scrapes the main article text from NeaKriti."""
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        # NeaKriti typical article body selector
        paragraphs = soup.select('.article-body p, .article-text p')
        return " ".join([p.text for p in paragraphs])
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def summarize(text):
    """Sends text to Gemini for a 3-bullet Greek summary."""
    prompt = f"Περίληψε το παρακάτω άρθρο σε 3 σύντομες και περιεκτικές κουκκίδες (bullets) στα Ελληνικά:\n\n{text}"
    response = model.generate_content(prompt)
    return response.text

def main():
    if not os.path.exists(SUMMARY_DIR): os.makedirs(SUMMARY_DIR)
    
    # Load history
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: processed = json.load(f)
    else:
        processed = []

    feed = feedparser.parse(RSS_URL)
    new_entries = []

    for entry in feed.entries:
        link = entry.link
        # Filter 1: Section check
        if any(section in link for section in ALLOWED_SECTIONS):
            # Filter 2: Check if already processed
            article_id = link.split('/')[-1].split('_')[0] # Extracts "2159092"
            
            if article_id not in processed:
                print(f"Processing: {link}")
                full_text = get_full_text(link)
                
                if full_text and len(full_text) > 200:
                    summary_text = summarize(full_text)
                    
                    # Save individual JSON for the frontend to fetch
                    with open(f"{SUMMARY_DIR}/{article_id}.json", "w", encoding="utf-8") as f:
                        json.dump({"summary": summary_text, "url": link}, f, ensure_content_type=False)
                    
                    processed.append(article_id)
                    new_entries.append(article_id)
                    time.sleep(1) # Rate limiting safety

    # Update history (keep last 500 articles to prevent file bloat)
    with open(DB_FILE, 'w') as f:
        json.dump(processed[-500:], f)

if __name__ == "__main__":
    main()