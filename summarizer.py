import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai
import json
import os
import time

# Configuration
RSS_URL = "https://www.neakriti.gr/rss.xml"
ALLOWED_SECTIONS = ["/kriti/", "/ellada/"]
DB_FILE = "processed_articles.json"
SUMMARY_DIR = "summaries"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL_ID = "gemini-3-flash-preview" # Gemini 3 Fast/Flash 2026 stable name

def get_full_text(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Neakriti often uses 'article-body' or 'field-item even'
        # We search for the most likely containers
        content = soup.select_one('.article-body') or soup.select_one('.field-name-body') or soup.select_one('article')
        
        if content:
            paragraphs = content.find_all('p')
            text = " ".join([p.text for p in paragraphs])
            return text if len(text) > 100 else None
        return None
    except Exception as e:
        print(f"❌ Scraping error for {url}: {e}")
        return None

def summarize(text):
    prompt = f"Περίληψε το παρακάτω άρθρο σε 3 σύντομες κουκκίδες στα Ελληνικά:\n\n{text}"
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return response.text
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return None

def main():
    if not os.path.exists(SUMMARY_DIR): os.makedirs(SUMMARY_DIR)
    
    processed = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            try: processed = json.load(f)
            except: processed = []

    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries:
        link = entry.link
        if any(section in link for section in ALLOWED_SECTIONS):
            article_id = link.split('/')[-1].split('_')[0]
            
            if article_id not in processed:
                print(f"🔍 Attempting: {article_id}")
                full_text = get_full_text(link)
                
                if full_text:
                    print(f"📖 Text found ({len(full_text)} chars). Calling Gemini...")
                    summary_text = summarize(full_text)
                    
                    if summary_text:
                        with open(f"{SUMMARY_DIR}/{article_id}.json", "w", encoding="utf-8") as f:
                            json.dump({"summary": summary_text, "url": link}, f, ensure_ascii=False)
                        
                        processed.append(article_id)
                        print(f"✅ SUCCESSFULLY SAVED: {article_id}.json")
                        time.sleep(1)
                else:
                    print(f"⚠️ Could not extract text for {article_id}. Skipping.")

    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(processed[-500:], f, ensure_ascii=False)

if __name__ == "__main__":
    main()