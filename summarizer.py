import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai  # The new 2026 SDK
import json
import os
import time

# Configuration
RSS_URL = "https://www.neakriti.gr/rss.xml"
ALLOWED_SECTIONS = ["/kriti/", "/ellada/"]
DB_FILE = "processed_articles.json"
SUMMARY_DIR = "summaries"

# Initialize Gemini 3 Flash Preview
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_ID = "gemini-3-flash-preview"

def get_full_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        # Selector for Neakriti content
        paragraphs = soup.select('.article-body p, .article-text p')
        text = " ".join([p.text for p in paragraphs])
        return text if len(text) > 150 else None
    except Exception as e:
        print(f"Scraping error: {e}")
        return None

def summarize(text):
    prompt = f"Περίληψε το παρακάτω άρθρο σε 3 σύντομες κουκκίδες στα Ελληνικά:\n\n{text}"
    try:
        # Modern Gemini 3 call syntax
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return None

def main():
    if not os.path.exists(SUMMARY_DIR): os.makedirs(SUMMARY_DIR)
    
    # Load processed history
    processed = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try: processed = json.load(f)
            except: processed = []

    print(f"Checking RSS for new articles in {ALLOWED_SECTIONS}...")
    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries:
        link = entry.link
        if any(section in link for section in ALLOWED_SECTIONS):
            article_id = link.split('/')[-1].split('_')[0]
            
            if article_id not in processed:
                print(f"🚀 Summarizing: {article_id}")
                full_text = get_full_text(link)
                
                if full_text:
                    summary_text = summarize(full_text)
                    if summary_text:
                        with open(f"{SUMMARY_DIR}/{article_id}.json", "w", encoding="utf-8") as f:
                            json.dump({"summary": summary_text, "url": link}, f, ensure_ascii=False)
                        
                        processed.append(article_id)
                        print(f"✅ Created: {article_id}.json")
                        time.sleep(1) # Flash is fast, but let's be polite

    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(processed[-500:], f, ensure_ascii=False)

if __name__ == "__main__":
    main()