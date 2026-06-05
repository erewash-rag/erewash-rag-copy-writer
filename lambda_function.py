import requests
from bs4 import BeautifulSoup
import time
from openai import OpenAI
import os
import random
import base64
import re
import json
import logging
import boto3
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_and_upload_image(article_title):
    logger.info("Generating image for: %s", article_title)

    org_id = os.environ.get('open_ai_org') or get_from_file(0)
    project_id = os.environ.get('open_ai_project') or get_from_file(1)
    api_key = os.environ.get('open_ai_api_key') or get_from_file(2)

    openai_client = OpenAI(organization=org_id, project=project_id, api_key=api_key)

    prompt = "Create an absurdist satirical cartoon for a news article with the title " + article_title

    result = openai_client.images.generate(
        model="gpt-image-2",
        prompt=prompt
    )

    image_bytes = base64.b64decode(result.data[0].b64_json)
    logger.info("Image generated (%d bytes)", len(image_bytes))

    bucket = os.environ.get('s3_image_bucket') or get_from_file(4)
    safe_title = re.sub(r'[^a-zA-Z0-9_-]', '_', article_title)[:60]
    s3_key = f"images/{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_title}.png"

    aws_key = os.environ.get('aws_access_key_id') or get_from_file(5)
    aws_secret = os.environ.get('aws_secret_access_key') or get_from_file(6)

    logger.info("Uploading image to s3://%s/%s", bucket, s3_key)
    s3 = boto3.client('s3', aws_access_key_id=aws_key, aws_secret_access_key=aws_secret)
    s3.put_object(Bucket=bucket, Key=s3_key, Body=image_bytes, ContentType='image/png')

    url = f"https://{bucket}.s3.amazonaws.com/{s3_key}"
    logger.info("Image uploaded: %s", url)
    return url


def scrape_erewash_news(base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    logger.info("Fetching news listing: %s", base_url)
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        logger.error("Failed to retrieve news page: HTTP %s", response.status_code)
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    news_links = soup.select('h2 a')
    logger.info("Found %d article links", len(news_links))

    article_texts = []
    for link in news_links:
        article_texts.append(get_article_text(link, headers))

    logger.info("Scraped %d articles", len(article_texts))
    return article_texts
        

def get_article_text(link, headers):
    title = link.get_text(strip=True)
    href = link.get('href')
    
    # Ensure the link is a full URL
    if href.startswith('/'):
        full_url = f"https://www.erewash.gov.uk{href}"
    else:
        full_url = href

    logger.info("Scraping article: %s (%s)", title, full_url)
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
            paragraphs = content_div.find_all('p')
            full_text = "\n".join([p.get_text(strip=True) for p in paragraphs])
            logger.debug("Extracted %d paragraphs from %s", len(paragraphs), url)
            return full_text
        else:
            logger.warning("Could not find article body at %s", url)

    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)

def get_from_file(line_num):
    fp = open("local-creds.txt")
    for i, line in enumerate(fp):
        if i == line_num:
            return line.strip('\n')

def generate_from_open_ai(latest, modifier):
    logger.info("Generating article with persona: %s", modifier.split(',')[0])
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
            {"role": "system", "content": "You are a journalist writing satirical local news about the Borough of Erewash for your paper, the Erewash Rag. When given an article the Borough Council published it is your job to write a satirical artical on the same topic. The style of the articles should be very absurdist. For each prompt you are given you will be given an author persona. The articles you create are going to be sent to a REST API so it's important you return JSON format with the following fields: \"title\" the title for your article (Note this should NOT include emoji), \"author\" the author persona for that given prompt, \"content\" (the actual text of the article, this should be MINIMUM 3 PARAGRAPHS but up to 6), \"excerpt\" which is a small snippet of \"content\" to hook the reader and should be no more than 20 words and \"category\" you may choose a category that best fits from these options: \"Poly-ticks\" - news about politics, \"Sporty Spice\" - news about sports, \"The (F)Arts\" - news about art or culture, \"Derbyshire\" - wider news for Derbyshire and not just Erewash, \"Local News\" - a generic catchall for news about Erewash"},
            {"role": "user", "content": "This article has been published by Erewash Borough Council. You are to write an article for the Erewash Rag on the same news. Your author persona for this article is " + modifier + ": " + latest}
        ]
    )

    logger.info("Article generated successfully")
    return completion.choices[0].message.content

def send_article(data, image=None, source_url=None, draft=True, featured=False):
    # Strip markdown code fences if the LLM wrapped the JSON in ```json ... ```
    raw = data.strip()
    fenced = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", raw)
    if fenced:
        raw = fenced.group(1)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s", e)
        logger.debug("Raw response: %s", data)
        return

    # Required fields from the LLM
    payload = {
        "title":    parsed.get("title", ""),
        "content":  parsed.get("content", ""),
        "excerpt":  parsed.get("excerpt", ""),
        "author":   parsed.get("author", ""),
        "category": parsed.get("category", "Local News"),
    }

    # Fixed / derived fields
    payload["date"]     = datetime.now().strftime("%Y-%m-%d")
    payload["draft"]    = str(draft).lower()
    payload["featured"] = str(featured).lower()

    # Optional fields — only included when provided
    if image is not None:
        payload["image"] = image
    if source_url is not None:
        payload["sourceUrl"] = source_url

    logger.info("Sending article: \"%s\" by %s [%s]", payload["title"], payload["author"], payload["category"])
    logger.debug("Payload: %s", json.dumps(payload, indent=2, ensure_ascii=False))

    api_url = "https://k1a2nskxl0.execute-api.eu-west-2.amazonaws.com/prod/articles"
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ.get('api_key') or get_from_file(3)
    }
    response = requests.post(api_url, headers=headers, json=payload)
    return response.json()

# Run the scraper
if __name__ == "__main__":

    # send_article("my content", "my title", "my excerpt", "my sourceUrl", "my imageUrl")

    url = "https://www.erewash.gov.uk/news"
    stories = scrape_erewash_news(url)

    prompt_modifiers = [
        "Emma Porridge, the political editor. You have a subtle desire in all your writing to make it sound like Erewash Borough Council are actually an authoritarian dictatorship",
        "Archibald Montgomery-Fitzwilliam, who writes about cultural affairs. Do it as a very pompous opinion piece gushing at the beauty of all culture",
        "Rex Foodbasket, a veteran undercover reporter who hides their sources in fear of reprisals and always makes it sound like they're revealing watergate even if they're actually just telling you something completely mundane",
        "Rachel Spoonbender, a slightly nutty conspiracy theorist who thinks the council is either full of spies for the Chinese government or who thinks there's a secret cabal of hardcore Communists at the heart of local government. They are slightly reticent to mention these things directly though because they've already been told off by the editor a few times",
        "Gary Wheelbarrow, a former miner and industrial worker who thinks what Maggie Thatcher did is worse than genocide and just will not let it go. They should write most articles from a perspective of \"it's not like it was back in my day\" and have a slight fear of all things more technologically advanced than an electric kettle",
        "Alice Ashbottom, a poncy middle aged lady who loves womens hour, the WI and says they value a sense of community but all they really do is stir the pot"
    ]

    logger.info("Processing %d stories", len(stories))
    for i, story in enumerate(stories, start=1):
        logger.info("--- Story %d/%d ---", i, len(stories))
        mod = random.choice(prompt_modifiers)
        article_json = generate_from_open_ai(story, mod)

        try:
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", article_json.strip())
            article_title = json.loads(raw).get("title", "Erewash News")
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Could not parse article title for story %d, using fallback", i)
            article_title = "Erewash News"

        image_url = generate_and_upload_image(article_title)
        send_article(article_json, image=image_url)

    logger.info("Done — processed %d stories", len(stories))