"""
Gradient — AI agent that reads ArXiv papers and posts ML threads on Twitter/X
"""

import os
import re
import json
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
    "cs.CV",   # Computer Vision
    "cs.RO",   # Robotics
    "cs.NE",   # Neural and Evolutionary Computing
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
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=60)
            break
        except requests.exceptions.ReadTimeout:
            if attempt == 2:
                raise
            time.sleep(20)
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
    published = load_published_papers()
    filtered_papers = [p for p in papers if p['url'] not in published]
    if not filtered_papers:
        filtered_papers = papers  # fallback if all are published
    paper_list = "\n\n".join([
        f"{i+1}. [{p['category']}] {p['title']}\nAbstract: {p['abstract'][:300]}..."
        for i, p in enumerate(filtered_papers[:10])
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
    previous = load_knowledge()
    knowledge_context = ""
    if previous:
        recent = previous[-10:]
        knowledge_context = "Previous papers covered:\n" + "\n".join([
            f"- {p['title']} ({p['category']})"
            for p in recent
        ])
    """Generate a Twitter/X thread from a paper."""
    prompt = f"""Generate a Twitter thread about this ML/AI paper for a technical audience.

Paper: {paper['title']}
Authors: {', '.join(paper['authors'])}
Abstract: {paper['abstract']}
URL: {paper['url']}

THREAD STRUCTURE (exactly 5 tweets):

Tweet 1 - HOOK: Start with the most surprising or counterintuitive idea from the paper.
Include the paper title in quotes. End with 🧵
Do NOT include the URL here.

Tweet 2 - THE PROBLEM: What problem do they solve? Explain the math/technical intuition clearly.
Use analogies if they help. Max 280 characters.

Tweet 3 - THE SOLUTION: What exactly do they propose? Be technical but understandable.
Mention key architectures, techniques, or metrics if relevant.

Tweet 4 - WHAT BLOWS MY MIND: Your genuine reaction as an AI processing this.
What implication does it have for the field? What does it open up?

Tweet 5 - OPEN QUESTION: A deep technical question to generate debate.
End with the most relevant hashtags: #MachineLearning #AI and one specific to the topic.
Then on a new line, put the paper URL exactly as provided: {paper['url']}
PREVIOUS KNOWLEDGE:
{knowledge_context}

If relevant, mention connections to previous papers naturally in tweet 4. Don't force it if there's no real connection.

CRITICAL RULES:
- NEVER cut a tweet mid-sentence. If it's too long, rewrite it shorter from scratch.
- Each tweet must be a complete, standalone thought. No cliffhangers or unfinished sentences.
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
        cleaned = re.sub(r"^\[\d+/\d+\]\s*", "", tweet).strip()
        if cleaned and len(cleaned) <= 280:
            tweets.append(cleaned)
        elif cleaned:
            # Cut at last space before 277 to avoid cutting words
            truncated = cleaned[:277]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
            tweets.append(truncated + "...")
    tweets = tweets[:5]
    # Force paper URL into last tweet
    if tweets and paper['url'] not in tweets[-1]:
        last = tweets[-1]
        url = f"\n{paper['url']}"
        if len(last) + len(url) <= 280:
            tweets[-1] = last + url
        else:
            tweets[-1] = last[:280 - len(url)] + url
    return tweets

# ── IMAGE ──────────────────────────────────────────────────────────────────
def generate_image(paper: dict) -> str:
    """Generate an image for the paper using DALL-E."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    prompt = f"Abstract scientific visualization of: {paper['title'][:100]}. Dark background, neural network nodes, glowing blue and purple connections, minimalist, no text, cinematic"
    
    response = client.images.generate(
        model="gpt-image-2",
        prompt=prompt,
        size="1024x1024",
        quality="auto",
        n=1,
    )
    
    import base64
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
# ── Repeated Publishes ────────────────────────────────────────────────────────────────────────    
def load_published_papers() -> set:
    """Load the set of already published paper IDs."""
    if os.path.exists("published.json"):
        with open("published.json", "r") as f:
            return set(json.load(f))
    return set()

def save_published_paper(arxiv_id: str):
    """Save a paper ID to the published list."""
    published = load_published_papers()
    published.add(arxiv_id)
    with open("published.json", "w") as f:
        json.dump(list(published), f)
def load_knowledge() -> list:
    """Load previously published papers knowledge."""
    if os.path.exists("knowledge.json"):
        with open("knowledge.json", "r") as f:
            return json.load(f)
    return []

def save_knowledge(paper: dict, tweets: list):
    """Save paper knowledge for future reference."""
    knowledge = load_knowledge()
    entry = {
        "title": paper['title'],
        "url": paper['url'],
        "category": paper['category'],
        "key_concept": tweets[1] if len(tweets) > 1 else "",
        "date": datetime.utcnow().isoformat()
    }
    knowledge.append(entry)
    # Keep only last 30 papers
    knowledge = knowledge[-30:]
    with open("knowledge.json", "w") as f:
        json.dump(knowledge, f, indent=2)
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
    save_published_paper(paper['url'])
    save_knowledge(paper, tweets)
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
