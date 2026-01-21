import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai # Modern 2026 SDK
import json
import os
import time

# Configuration
RSS_URL = "https://www.neakriti.gr/rss.xml"
ALLOWED_SECTIONS = ["/kriti/", "/ellada/"]
DB_FILE = "processed_articles.json"
SUMMARY_DIR = "summaries"

# Initialize Gemini 3 Fast
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def get_full_text(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        paragraphs = soup.select('.article-body p, .article-text p')
        return " ".join([p.text for p in paragraphs])
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

def summarize(text):
    prompt = f"Περίληψε το παρακάτω άρθρο σε 3 σύντομες κουκκίδες στα Ελληνικά:\n\n{text}"
    # Using the Gemini 2.0 Flash (Gemini 3 Fast equivalent)
    response = client.models.generate_content(
        model="gemini-3.0-flash", contents=prompt
    )
    return response.text

def main():
    if not os.path.exists(SUMMARY_DIR): os.makedirs(SUMMARY_DIR)
    
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: processed = json.load(f)
    else:
        processed = []

    feed = feedparser.parse(RSS_URL)
    
    for entry in feed.entries:
        link = entry.link
        if any(section in link for section in ALLOWED_SECTIONS):
            article_id = link.split('/')[-1].split('_')[0]
            
            if article_id not in processed:
                print(f"Processing: {article_id}")
                full_text = get_full_text(link)
                
                if full_text and len(full_text) > 200:
                    summary_text = summarize(full_text)
                    
                    file_path = f"{SUMMARY_DIR}/{article_id}.json"
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump({"summary": summary_text, "url": link}, f, ensure_ascii=False)
                    
                    print(f"✅ Saved summary for {article_id}")
                    processed.append(article_id)
                    time.sleep(1)

    with open(DB_FILE, 'w') as f:
        json.dump(processed[-500:], f)

if __name__ == "__main__":
    main()