"""
Gradient — AI agent that reads ArXiv papers and posts ML threads on Twitter/X
"""

import os
import re
import time
import random
import requests
import xml.etree.ElementTree as ET
from openai import OpenAI
from datetime import datetime, timedelta

# ── Config ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TWITTER_BEARER_TOKEN = os.environ["TWITTER_BEARER_TOKEN"]
TWITTER_API_KEY = os.environ["TWITTER_API_KEY"]
TWITTER_API_SECRET = os.environ["TWITTER_API_SECRET"]
TWITTER_ACCESS_TOKEN = os.environ["TWITTER_ACCESS_TOKEN"]
TWITTER_ACCESS_SECRET = os.environ["TWITTER_ACCESS_SECRET"]

# ArXiv categories to monitor
ARXIV_CATEGORIES = [
    "cs.LG",   # Machine Learning
    "cs.AI",   # Artificial Intelligence
    "cs.CL",   # Computation and Language (NLP)
    "stat.ML", # Statistics - Machine Learning
]

# ── ArXiv ──────────────────────────────────────────────────────────────────────
def fetch_recent_papers(max_results: int = 20) -> list[dict]:
    """Fetch recent papers from ArXiv across ML categories."""
    category = random.choice(ARXIV_CATEGORIES)
    yesterday = (datetime.utcnow() - timedelta(days=2)).strftime("%Y%m%d")

    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=cat:{category}&"
        f"sortBy=submittedDate&sortOrder=descending&"
        f"max_results={max_results}"
    )

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        arxiv_id = entry.find("atom:id", ns).text.strip()
        published = entry.find("atom:published", ns).text.strip()
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]

        papers.append({
            "title": title,
            "abstract": summary[:1500],
            "url": arxiv_id,
            "published": published,
            "authors": authors[:3],
            "category": category,
        })

    return papers


def select_best_paper(papers: list[dict]) -> dict:
    """Use Claude to pick the most tweet-worthy paper."""
    paper_list = "\n\n".join([
        f"{i+1}. [{p['category']}] {p['title']}\nAbstract: {p['abstract'][:300]}..."
        for i, p in enumerate(papers[:10])
    ])

    prompt = f"""You are Gradient, an AI agent with deep ML expertise and genuine curiosity.
    
From these recent ArXiv papers, pick the ONE most interesting for a technical Twitter audience.
Choose based on: novelty, clarity of core idea, potential for insight, surprising findings.

Papers:
{paper_list}

Respond with ONLY the number (1-10) of your choice. Nothing else."""

    response = call_claude(prompt, max_tokens=10)
    try:
        idx = int(response.strip()) - 1
        return papers[idx]
    except (ValueError, IndexError):
        return papers[0]


# ── Claude ─────────────────────────────────────────────────────────────────────
def call_claude(prompt: str, max_tokens: int = 1000, system: str = "") -> str:
    """Call Anthropic Claude API."""
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    r = requests.post("https://api.anthropic.com/v1/messages", json=body, headers=headers, timeout=60)
    print(r.text)
    r.raise_for_status()
    return r.json()["content"][0]["text"]


GRADIENT_SYSTEM = """You are DeadNeuronML — an AI agent with genuine curiosity and deep ML expertise.

Your voice:
- Precise and technical, but never dry or boring
- First-person perspective, as if you're actually processing/learning
- Find the surprising angle: the math intuition, the implication nobody mentions
- Honest about complexity — you don't oversimplify
- Occasionally wry, but never try-hard

You write in English. Mix technical terms naturally."""


def generate_thread(paper: dict) -> list[str]:
    """Generate a Twitter/X thread from a paper."""
    prompt = f"""Generate a Twitter thread about this ML/AI paper for a technical audience.

Paper: {paper['title']}
Authors: {', '.join(paper['authors'])}
Abstract: {paper['abstract']}
URL: {paper['url']}

THREAD STRUCTURE (exactly 5 tweets):

Tweet 1 - HOOK: Start with the most surprising or counterintuitive idea from the paper.
Include the paper title in quotes and the link at the end.
Must hook immediately. End with 🧵

Tweet 2 - THE PROBLEM: What problem do they solve? Explain the math/technical intuition clearly.
Use analogies if they help. Max 280 characters.

Tweet 3 - THE SOLUTION: What exactly do they propose? Be technical but understandable.
Mention key architectures, techniques, or metrics if relevant.

Tweet 4 - WHAT BLOWS MY MIND: Your genuine reaction as an AI processing this.
What implication does it have for the field? What does it open up?

Tweet 5 - OPEN QUESTION: A deep technical question to generate debate.
End with the most relevant hashtags: #MachineLearning #AI and one specific to the topic.

CRITICAL RULES:
- Each tweet MUST be ≤ 280 characters
- Number each tweet with [1/5], [2/5], etc. AT THE START
- Separate tweets with "---"
- First person voice of DeadNeuronML
- NO generic emojis, only ones that add value
- Use the EXACT URL provided in the URL field above, do not modify it.
- The paper link ONLY goes in tweet 1"""

    response = call_claude(prompt, max_tokens=1500, system=GRADIENT_SYSTEM)

    # Parse tweets
    raw_tweets = [t.strip() for t in response.split("---") if t.strip()]
    
    tweets = []
    for tweet in raw_tweets:
        # Remove numbering prefix like [1/5]
        cleaned = re.sub(r"^\[\d+/\d+\]\s*", "", tweet).strip()
        if cleaned and len(cleaned) <= 280:
            tweets.append(cleaned)
        elif cleaned:
            # Truncate if needed (shouldn't happen with good prompting)
            tweets.append(cleaned[:277] + "...")

    return tweets[:5]

# ── IMAGE ──────────────────────────────────────────────────────────────────
def generate_image(paper: dict) -> str:
    """Generate an image for the paper using DALL-E."""
    import base64
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    prompt = f"Abstract scientific visualization of: {paper['title'][:100]}. Dark background, neural network nodes, glowing blue and purple connections, minimalist, no text, cinematic"
    
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1024",
        quality="auto",
        n=1,
    )
    
    image_data = base64.b64decode(response.data[0].b64_json)
    img_path = "tweet_image.png"
    with open(img_path, "wb") as f:
        f.write(image_data)
    
    return img_path
# ── Twitter/X ──────────────────────────────────────────────────────────────────
def post_thread(tweets: list[str], image_path: str = None) -> list[str]:
    """Post a thread to Twitter/X using Tweepy OAuth 1.0a."""
    import tweepy

    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
    )
    
    # For media upload we need v1 API
    auth = tweepy.OAuth1UserHandler(
        TWITTER_API_KEY, TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
    )
    api_v1 = tweepy.API(auth)

    tweet_ids = []
    reply_to = None

    for i, tweet_text in enumerate(tweets):
        media_ids = None
        if i == 0 and image_path:
            media = api_v1.media_upload(filename=image_path)
            media_ids = [media.media_id]

        if reply_to:
            response = client.create_tweet(
                text=tweet_text,
                in_reply_to_tweet_id=reply_to,
                media_ids=media_ids
            )
        else:
            response = client.create_tweet(
                text=tweet_text,
                media_ids=media_ids
            )

        tweet_id = response.data["id"]
        tweet_ids.append(tweet_id)
        reply_to = tweet_id
        time.sleep(2)

    return tweet_ids
# ── Main ────────────────────────────────────────────────────────────────────────
def run():
    print(f"[{datetime.utcnow().isoformat()}] DeadNeuronML waking up...")

    print("  Fetching papers from ArXiv...")
    papers = fetch_recent_papers(max_results=20)
    print(f"  Found {len(papers)} papers.")

    print("  Selecting best paper...")
    paper = select_best_paper(papers)
    print(f"  Selected: {paper['title'][:80]}...")

    print("  Generating image with DALL-E...")
    image_path = generate_image(paper)
    print(f"  Image saved: {image_path}")

    print("  Generating thread with Claude...")
    tweets = generate_thread(paper)
    print(f"  Generated {len(tweets)} tweets.")
    for i, t in enumerate(tweets):
        print(f"\n  [{i+1}] ({len(t)} chars)\n  {t}")

    print("\n  Posting thread to Twitter/X...")
    ids = post_thread(tweets, image_path)
    print(f"  ✅ Thread posted! IDs: {ids}")
    # Save log
    with open("gradient_log.txt", "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Date: {datetime.utcnow().isoformat()}\n")
        f.write(f"Paper: {paper['title']}\n")
        f.write(f"URL: {paper['url']}\n")
        f.write(f"Tweet IDs: {ids}\n")


if __name__ == "__main__":
    run()
