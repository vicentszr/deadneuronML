# 📓 DEVLOG — Building DeadNeuronML

A full log of how this project was built, the problems encountered, and how they were solved.

---

## The idea

The goal was to build an autonomous AI agent that publishes ML research content automatically — technically rigorous, with its own voice, and fully automated.

The concept: an agent that reads real ArXiv papers every day, processes them with an LLM, and posts technical threads with AI-generated images. No manual intervention after deployment.

**Stack chosen:**
- ArXiv API → paper source
- Claude (Anthropic) → intelligence layer
- DALL-E (OpenAI) → image generation
- Twitter/X → publishing platform
- GitHub Actions → automation

---

## Setup and first run

Started by setting up the Python environment and installing dependencies. Used the ArXiv public API to fetch recent papers from ML categories (cs.LG, cs.AI, cs.CL, stat.ML).

First successful run output:

```
Found 20 papers.
Selecting best paper...
Selected: Drifting Preference Optimization for One-Step Generative Models
Generating thread with Claude...
Generated 5 tweets.
```

The ArXiv API and Claude integration worked well from the start. The generated threads were technically precise with a consistent first-person voice.

---

## Twitter API — First major challenge

### 402 Payment Required
The first posting attempt returned a 402 error. Twitter's free tier no longer allows posting tweets programmatically — the API pricing changed.

Investigated OAuth 1.0a vs OAuth 2.0 approaches. The issue wasn't authentication — it was the account tier. Switched to Tweepy to simplify the OAuth flow, same result.

**Solution:** Purchased Twitter API pay-per-use credits.

### Thread replies → 403 Forbidden
After getting the first tweet to post, replies (needed to create a thread) returned 403. Creating reply chains requires the Basic tier ($100/month).

Restructured the posting logic to work within the current tier constraints.

---

## LinkedIn API — Extended investigation

Explored LinkedIn as an alternative or complementary publishing platform. This required significant investigation into their API structure.

### Scope restrictions
The LinkedIn Developer free tier only provides the `w_member_social` scope — which allows posting but not reading the user profile. However, posting via the API requires the author's numeric ID (`urn:li:member:XXXXXXXXX`), which can only be obtained with scopes unavailable on the basic plan (`r_liteprofile`, `openid`).

### Extracting the user ID
After trying multiple API endpoints that returned 403, found the ID encoded in base64 inside a network request visible in browser DevTools:

```python
data = base64.urlsafe_b64decode('ACoAADJ8MwwB...')
user_id = int.from_bytes(data[4:8], 'big')  # → 847000332
```

### API versioning issues
The `/rest/posts` endpoint requires a `LinkedIn-Version` header. Multiple versions returned `NONEXISTENT_VERSION`. After research, discovered this endpoint is part of the Marketing Developer Platform, which requires separate enterprise approval.

**Decision:** Returned to Twitter as the primary platform. LinkedIn will be revisited when API access improves.

---

## Adding image generation

Added DALL-E image generation to make threads more visually engaging in the Twitter feed.

### API changes
OpenAI updated their image model names. `dall-e-3` was deprecated — updated to `gpt-image-1`. The `quality` parameter also changed from `standard` to `auto`.

### Response format
`gpt-image-1` returns images as base64 instead of URLs. Updated the code to decode and save locally before uploading to Twitter's media endpoint.

---

## GitHub Actions deployment

Configured a daily cron job on GitHub Actions to run the agent automatically at 9:00 UTC.

Issues encountered during setup:
- Filename mismatch between workflow config and actual script name
- Missing dependencies (`tweepy`, `openai`) in the install step
- Missing `OPENAI_API_KEY` in the workflow secrets

After resolving these, the first fully automated run completed successfully in 55 seconds. ✅

The agent now runs every day without manual intervention.

---

## Current state

Every day at 9:00 UTC the agent:
1. Fetches 20 recent papers from ArXiv
2. Selects the most interesting with Claude
3. Generates a scientific visualization with DALL-E
4. Writes a 5-tweet technical thread in English
5. Posts to [@DeadNeuronML](https://twitter.com/DeadNeuronML) automatically

Total infrastructure cost: ~$1.65/month.

---

## Next steps

- **Auto-reply to mentions** — monitor mentions and generate contextual technical replies with Claude. Requires Twitter Basic tier for read access.
- **LinkedIn publishing** — once LinkedIn opens API access for individual developers, add automatic cross-posting.
- **Metrics dashboard** — build a dashboard to track engagement per thread, identify which paper categories perform best, and optimize posting time.

---

## Key learnings

1. **API pricing changes fast** — Twitter's free tier restrictions changed significantly. Always budget for paid API access in production bots.
2. **LinkedIn's API is enterprise-first** — individual developers have very limited access. Getting basic user information requires scopes not available on standard plans.
3. **Model names deprecate** — OpenAI and Anthropic update model identifiers regularly. Pin versions and monitor deprecation notices.
4. **GitHub Actions is the simplest possible infra** — for a daily cron job with no persistent state, it's free and reliable.
5. **The hard part is the plumbing** — integrating multiple APIs with different auth systems, rate limits, and versioning is where most of the complexity lives.
