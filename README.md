# 🧠 DeadNeuronML

An autonomous AI agent that reads ArXiv ML papers daily and posts technical threads on Twitter/X — fully automated, zero manual intervention.

> Follow [@DeadNeuronML](https://twitter.com/DeadNeuronML) · [Live web interface](https://vicentszr.github.io/deadneuronML)

---

## What it does

Every day at 9:00 UTC, the agent:

1. **Fetches 20 recent papers** from ArXiv across 7 ML categories (cs.LG, cs.AI, cs.CL, stat.ML, cs.CV, cs.RO, cs.NE)
2. **Selects the most interesting** using Claude — based on novelty, surprising findings, and technical depth
3. **Generates a visual** with gpt-image-2 — an abstract scientific visualization of the core concept
4. **Writes a 5-tweet thread** in English with Claude — hook, problem, solution, insight, open question
5. **Posts automatically** to Twitter/X with the image attached
6. **Saves to memory** — updates `knowledge.json` and `published.json` for context in future threads

---

## Web interface

A 3D web interface at **[vicentszr.github.io/deadneuronML](https://vicentszr.github.io/deadneuronML)** shows:

- **3D neuron avatar** — interactive Three.js visualization, drag to rotate
- **Knowledge graph** — every paper covered, mapped by category with connections
- **Agent panel** — click any paper node to ask DeadNeuronML about it in real time (powered by Claude via Vercel proxy)
- **Text-to-speech** — the agent reads its explanation aloud

---

## Stack

| Component | Technology |
|-----------|-----------|
| Paper source | ArXiv API (free) |
| Paper selection | Claude (Anthropic API) |
| Thread generation | Claude (Anthropic API) |
| Image generation | gpt-image-2 (OpenAI API) |
| Publishing | Twitter API v2 + Tweepy |
| Automation | GitHub Actions (cron job) |
| Web frontend | Three.js + Canvas 2D |
| Web hosting | GitHub Pages |
| API proxy | Vercel serverless |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/vicentszr/deadneuronML.git
cd deadneuronML
pip install -r requirements.txt
```

### 2. Get API keys

- **Anthropic** — [console.anthropic.com](https://console.anthropic.com)
- **OpenAI** — [platform.openai.com](https://platform.openai.com) (organization verification required for gpt-image-2)
- **Twitter Developer** — [developer.twitter.com](https://developer.twitter.com) (Basic tier required for posting)

### 3. Set environment variables

```bash
export ANTHROPIC_API_KEY=your_key
export OPENAI_API_KEY=your_key
export TWITTER_API_KEY=your_key
export TWITTER_API_SECRET=your_key
export TWITTER_ACCESS_TOKEN=your_key
export TWITTER_ACCESS_SECRET=your_key
export TWITTER_BEARER_TOKEN=your_key
```

### 4. Run locally

```bash
python gradient_3.py
```

### 5. Deploy to GitHub Actions

Add all environment variables as GitHub Secrets in your repo settings. The workflow runs automatically every day at 9:00 UTC.

---

## Cost

| Service | Monthly cost |
|---------|-------------|
| Claude API | ~$0.15 |
| gpt-image-2 API | ~$1.20 |
| Twitter API (pay-per-use) | ~$0.30 |
| GitHub Actions | Free |
| ArXiv API | Free |
| GitHub Pages | Free |
| Vercel | Free |

**Total: ~$1.65/month**

---

## Project structure

```
deadneuronML/
├── gradient_3.py          # Main agent
├── requirements.txt       # Python dependencies
├── published.json         # Papers already published (auto-generated)
├── knowledge.json         # Papers knowledge base (auto-generated)
├── index.html             # Web interface
├── DEVLOG.md              # Full build log
└── .github/
    └── workflows/
        └── gradient.yml  # GitHub Actions cron job
```

---

## Built by

[@vicentszr](https://github.com/vicentszr) — CS student building AI agents.