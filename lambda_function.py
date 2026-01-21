import requests
from bs4 import BeautifulSoup
import time
from openai import OpenAI
import os

def scrape_erewash_news(base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    # 1. Fetch the main news listing page
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve page: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    news_links = soup.select('h2 a')
    article_texts = []

    for link in news_links:
        article_texts.append(get_article_text(link, headers))

    return article_texts
        

def get_article_text(link, headers):
    title = link.get_text(strip=True)
    href = link.get('href')
    
    # Ensure the link is a full URL
    if href.startswith('/'):
        full_url = f"https://www.erewash.gov.uk{href}"
    else:
        full_url = href

    print(f"\n--- Scraping: {title} ---")
    article_content = scrape_article_content(full_url, headers)
    return article_content
    
    # Respectful delay between requests
    time.sleep(1)


def scrape_article_content(url, headers):
    try:
        res = requests.get(url, headers=headers)
        article_soup = BeautifulSoup(res.text, 'html.parser')
        
        # 3. Extract the main text
        # Most gov sites put the main body in an <article> or a specific <div>
        content_div = article_soup.find('div', class_='item-page') or article_soup.find('article')
        
        if content_div:
            # Get all paragraphs
            paragraphs = content_div.find_all('p')
            full_text = "\n".join([p.get_text(strip=True) for p in paragraphs])
            return full_text
        else:
            print("Could not find article body.")
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")

def get_from_file(line_num):
    fp = open("local-creds.txt")
    for i, line in enumerate(fp):
        if i == line_num:
            return line.strip('\n')

def generate_from_open_ai(latest, modifier):
    org_id = os.environ.get('open_ai_org') or get_from_file(0)
    project_id = os.environ.get('open_ai_project') or get_from_file(1)
    api_key = os.environ.get('open_ai_api_key') or get_from_file(2)

    client = OpenAI(
        organization=org_id,
        project=project_id,
        api_key=api_key
    )

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": "You are a journalist writing satirical local news about the Borough of Erewash for your paper, the Erewash Rag. When given an article the Borough Council published it is your job to write a satirical version of it. The style of the articles should be very absurdist"},
            {"role": "user", "content": "This article has been published by Erewash Borough Council. " + modifier + ": " + latest}
        ]
    )

    return completion.choices[0].message.content

# Run the scraper
if __name__ == "__main__":
    url = "https://www.erewash.gov.uk/news"
    stories = scrape_erewash_news(url)

    prompt_modifiers = [
        "Make it sound like the council are an authoritarian dictatorship",
        "Do it as a very pompous opinion piece as the arts editor",
        "Write it like an undercover reporter who needs to hide their sources and fears reprisals",
        "Make it sound like the council is full of spies for the Chinese government",
        "Make the council sound like hardcore Communists",
        "Throw in a random anecdote about how you saw a councilor eating soil whilst researching the story"
    ]

    for story in stories:
        for mod in prompt_modifiers:
            print("\n-----------------")
            print("\n--- In the style of " + mod + " ---")
            print(generate_from_open_ai(story, mod))