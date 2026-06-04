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

Added image generation to make threads more visually engaging in the Twitter feed.

### API changes
OpenAI updated their image model names. `dall-e-3` was deprecated — updated to `gpt-image-1`, then to `gpt-image-2` (released April 2026). The `quality` parameter also changed from `standard` to `auto`. Required organization verification to use `gpt-image-2`.

### Response format
`gpt-image-2` returns images as base64 instead of URLs. Updated the code to decode and save locally before uploading to Twitter's media endpoint.

---

## Knowledge system

Added two JSON files that persist between executions:

**published.json** — stores ArXiv URLs of already-published papers to avoid repetition.

**knowledge.json** — stores the title, category, key concept and date of each paper. Passed to Claude as context so future threads can reference past coverage and make connections between papers.

Both files are automatically committed to the repo by GitHub Actions after each run.

---

## GitHub Actions deployment

Configured a daily cron job on GitHub Actions to run the agent automatically at 9:00 UTC.

Issues encountered during setup:
- Filename mismatch between workflow config and actual script name
- Missing dependencies (`tweepy`, `openai`) in the install step
- Missing `OPENAI_API_KEY` in the workflow secrets
- ArXiv rate limiting (429) from running the workflow too many times in quick succession

After resolving these, the first fully automated run completed successfully. The agent now runs every day without manual intervention.

---

## Web interface — 3D visualization

Built a web interface at `vicentszr.github.io/deadneuronML` with:

**3D Neuron Avatar** — built with Three.js. A neuron with dendrites, orbital rings, and particle effects. Fully interactive — drag to rotate with inertia. Changes color (green → blue) when the agent is "thinking".

**Knowledge Graph** — a 2D canvas visualization where each paper is a node colored by ArXiv category. Nodes are clustered by category with connections drawn between related papers. Hover shows a tooltip, click opens the agent panel.

**Agent Panel** — a slide-in panel that, when a paper node is clicked, calls Claude via a Vercel proxy to generate a real-time explanation of the paper in DeadNeuronML's voice. The text appears with a typewriter effect and is read aloud via the Web Speech API.

### CORS challenge
Calling the Anthropic API directly from GitHub Pages is blocked by CORS. Solution: deployed a serverless proxy on Vercel (`deadneuron-ml.vercel.app/api/claude`) that handles the API call server-side. The proxy adds appropriate CORS headers and keeps the API key secure in Vercel environment variables.

### canvas pointer-events issue
The Three.js canvas was covering the entire page with `position: absolute; inset: 0`, blocking clicks on the knowledge graph below. Fixed by setting `pointer-events: none` on the canvas and moving drag listeners to the hero section container instead.

---

## Current state

Every day at 9:00 UTC the agent:
1. Fetches 20 recent papers from ArXiv (7 categories)
2. Selects the most interesting with Claude
3. Generates a scientific visualization with gpt-image-2
4. Writes a 5-tweet technical thread in English
5. Posts to @DeadNeuronML automatically
6. Saves paper to knowledge.json and published.json
7. Commits updated memory files to GitHub

The web interface at `vicentszr.github.io/deadneuronML` shows the knowledge graph and allows anyone to ask the agent about any paper it has covered.

Total infrastructure cost: ~$1.65/month.

---

## Next steps

- **Auto-reply to mentions** — monitor mentions and generate contextual technical replies with Claude. Requires Twitter Basic tier for read access.
- **LinkedIn publishing** — once LinkedIn opens API access for individual developers, add automatic cross-posting.
- **Metrics dashboard** — track engagement per thread, identify which paper categories perform best.
- **ML embeddings** — use sentence-transformers to measure semantic similarity between papers and build smarter connections in the knowledge graph.
- **ElevenLabs TTS** — replace Web Speech API with a custom voice for DeadNeuronML for higher quality audio.

---

## Key learnings

1. **API pricing changes fast** — Twitter's free tier restrictions changed significantly. Always budget for paid API access in production bots.
2. **LinkedIn's API is enterprise-first** — individual developers have very limited access. Getting basic user information requires scopes not available on standard plans.
3. **Model names deprecate** — OpenAI and Anthropic update model identifiers regularly. Pin versions and monitor deprecation notices.
4. **GitHub Actions is the simplest possible infra** — for a daily cron job with no persistent state, it's free and reliable.
5. **CORS is always a problem** — any frontend that calls external APIs needs a proxy. Vercel serverless functions are the simplest solution.
6. **canvas pointer-events** — Three.js full-screen canvases block all interaction below them. Always set `pointer-events: none` if the canvas is decorative.
7. **The hard part is the plumbing** — integrating multiple APIs with different auth systems, rate limits, and versioning is where most of the complexity lives.

---

## three.ws avatar integration

Added a 3D avatar from three.ws to replace the hand-built Three.js neuron. The motivation was that three.ws announced a partnership with IBM on June 3, 2026 to build enterprise AI agents — the platform is gaining significant traction.

### Avatar creation
Created the avatar in three.ws/create using the template editor: black suit, Vision Pro glasses, dark aesthetic matching the DeadNeuronML brand. The avatar is stored at `three.ws/api/avatars/3372d458-a6ff-43fc-9ed4-250bf53f7198`.

### Brain configuration
Configured "My First Agent" in three.ws/brain with Claude Sonnet 4.6 and the DeadNeuronML system prompt. Also synthesized a persona via three.ws/brain → Persona with the correct tone, vocabulary and topics.

### Embed
Used the `<agent-3d>` web component embed:

```html
<script type="module" src="https://three.ws/agent-3d/latest/agent-3d.js"></script>
<agent-3d src="https://three.ws/api/avatars/3372d458-a6ff-43fc-9ed4-250bf53f7198" style="width:100%;height:700px;display:block;"></agent-3d>
```

### Backend outage
On June 5, 2026 three.ws experienced a backend outage affecting all LLM providers. The avatar renders correctly but chat returns HTTP 400 errors. This will resolve automatically when three.ws restores service — no code changes needed.

### Voice
ElevenLabs is not configured on three.ws's server — agents fall back to Browser TTS by default. Custom voice can be added later via three.ws/voice once ElevenLabs is available.
