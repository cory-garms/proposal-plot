# ProposalPilot AI — Beta Setup Guide

This guide gets the app running on your local network using Docker. No Python or Node.js installation required on the host.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose (Linux)
- The `proposal-pilot/` folder from whoever shared it with you

---

## Step 1 — Configure the app

In the `proposal-pilot/` folder, copy the example config file:

```
cp .env.example .env
```

Open `.env` in a text editor. At minimum, you need to set:

1. **JWT_SECRET** — replace `change-me-before-deploy` with a long random string. You can generate one with:
   ```
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **LLM provider** — the app needs an AI model to score solicitations and generate draft text. Pick one:

   **Anthropic (Claude)** — default, requires an API key from console.anthropic.com:
   ```
   LLM_PROVIDER=anthropic
   LLM_MODEL=claude-sonnet-4-6
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

   **Ollama (free, runs locally on the server)** — install Ollama first, then pull a model:
   ```
   LLM_PROVIDER=openai_compat
   LLM_MODEL=llama3.2
   LLM_BASE_URL=http://host.docker.internal:11434/v1
   LLM_API_KEY=
   ```

   **OpenAI (GPT):**
   ```
   LLM_PROVIDER=openai_compat
   LLM_MODEL=gpt-4o
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-your-key-here
   ```

   See `.env.example` for Gemini, Kimi K2, GLM, LM Studio, and vLLM options.

---

## Step 2 — Start the app

From the `proposal-pilot/` folder:

```
docker compose up --build
```

The first build takes 3–5 minutes (downloading base images and installing dependencies). Subsequent starts are fast.

You should see:
```
frontend  | ...nginx started
backend   | [startup] LLM provider: anthropic | model: claude-sonnet-4-6
backend   | Application startup complete.
```

---

## Step 3 — Open the app

On **any computer on your network**, open a browser and go to:

```
http://<server-ip>:3000
```

Replace `<server-ip>` with the IP address of the machine running Docker. You can find it with `ipconfig` (Windows) or `ip addr` (Linux).

**First visit:** you'll be redirected to the login page. Click "Register" to create your account.

---

## Step 4 — Load data

After logging in, go to **Admin** in the top navigation bar to:

1. **Run a scrape** — click "Run" under SBIR/DOD, Grants.gov, or SAM.gov to pull in solicitations
2. **Run Alignment** — scores all solicitations against your capability profile

This takes a few minutes. Status updates every 3 seconds.

---

## Stopping and restarting

```
docker compose down        # stop containers (data is preserved)
docker compose up          # restart (no rebuild needed)
docker compose up --build  # rebuild after code updates
```

---

## Data persistence

The database (`proposalpilot.db`) lives on the host machine in the `proposal-pilot/` folder. It is not deleted when containers stop. Back it up periodically:

```
cp proposalpilot.db proposalpilot.db.backup
```

---

## Troubleshooting

**App not loading?** Check that port 3000 is not blocked by a firewall on the server.

**"LLM API error" when generating drafts?** Your API key or LLM_BASE_URL in `.env` is wrong. Check the backend logs:
```
docker compose logs backend
```

**Scrapes return 0 results?** Keywords may need tuning. Go to the Keywords page and review active keywords, then re-run the scrape.

**Config changes not taking effect?** Restart the backend:
```
docker compose restart backend
```
