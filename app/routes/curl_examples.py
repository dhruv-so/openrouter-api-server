"""
Quick-reference /curl endpoint.

Renders a static HTML page with copyable curl examples for every common
/generate scenario. Aimed at humans poking at the API in a browser without
opening README on GitHub.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Docs"])


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>API curl examples</title>
<style>
  :root {
    --bg: #0d1117;
    --panel: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --muted: #8b949e;
    --accent: #58a6ff;
    --good: #3fb950;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
  header {
    padding: 40px 24px 20px;
    border-bottom: 1px solid var(--border);
    text-align: center;
  }
  header .inner {
    max-width: 900px;
    margin: 0 auto;
  }
  h1 { margin: 0 0 8px; font-size: 24px; font-weight: 600; }
  .lede { color: var(--muted); margin: 0; }
  .lede code { color: var(--accent); }
  main {
    padding: 24px 24px 80px;
    max-width: 900px;
    margin: 0 auto;
  }
  section { margin-top: 32px; }
  h2 {
    font-size: 16px;
    margin: 0 0 8px;
    font-weight: 600;
  }
  .desc { color: var(--muted); margin: 0 0 12px; }
  .code-wrap {
    position: relative;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  pre {
    margin: 0;
    padding: 16px 18px;
    overflow-x: auto;
    font: 13px/1.55 ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    color: var(--text);
  }
  button.copy {
    position: absolute;
    top: 8px;
    right: 8px;
    padding: 6px 12px;
    font: 12px/1 inherit;
    color: var(--muted);
    background: #21262d;
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    transition: all 120ms;
  }
  button.copy:hover { color: var(--text); border-color: var(--accent); }
  button.copy.copied { color: var(--good); border-color: var(--good); }
  .config {
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 8px;
    margin: 16px 0 24px;
    color: var(--muted);
    font-size: 13px;
  }
  .config code { color: var(--accent); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .nav { color: var(--muted); margin-top: 8px; font-size: 13px; }
</style>
</head>
<body>
<header>
  <div class="inner">
    <h1>curl quick reference</h1>
    <p class="lede">All examples assume base URL <code id="base">http://localhost:8000</code> and server key <code id="key">YOUR_SERVER_API_KEY</code>.</p>
    <p class="nav">Also see: <a href="/docs">/docs</a> (Swagger UI) · <a href="/health">/health</a> · <a href="/credits">/credits</a></p>
  </div>
</header>
<main>

<div class="config">
  Replace <code>YOUR_SERVER_API_KEY</code> with the value you set as <code>SERVER_API_KEY</code> in your <code>.env</code>. The server validates the <code>X-API-Key</code> header against that on every request.
</div>

<section>
  <h2>1. Health check (no auth)</h2>
  <p class="desc">Quick liveness probe. Returns server status, uptime, and the default model name.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS http://localhost:8000/health | jq</code></pre>
  </div>
</section>

<section>
  <h2>2. Plain text generation (default model = Flash)</h2>
  <p class="desc">Simplest call. Returns <code>output</code> as a string.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{"user_prompt": "Write a haiku about coding."}' | jq</code></pre>
  </div>
</section>

<section>
  <h2>3. With system prompt</h2>
  <p class="desc">Steer model behaviour. Both prompts default to <code>"text"</code> type.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Explain quantum computing.",
    "system_prompt": "You are a physics professor. Use simple analogies."
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>4. Load prompt(s) from URL</h2>
  <p class="desc">Set <code>*_prompt_type</code> to <code>"file"</code>; server fetches the URL (SSRF-checked, max 10MB).</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "https://example.com/prompts/task.txt",
    "user_prompt_type": "file",
    "system_prompt": "https://example.com/prompts/system.txt",
    "system_prompt_type": "file"
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>5. Image input via URL</h2>
  <p class="desc">Server downloads images (SSRF-checked, max 20MB), forwards as base64 with <code>detail: "high"</code>.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Describe this image.",
    "image_urls": ["https://picsum.photos/200/300"]
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>6. Multiple images</h2>
  <p class="desc">Up to 10. All embedded as base64 data URIs in a single request.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Compare these two images.",
    "image_urls": [
      "https://picsum.photos/200/300?random=1",
      "https://picsum.photos/200/300?random=2"
    ]
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>7. Structured JSON output (schema-enforced)</h2>
  <p class="desc"><code>output</code> arrives parsed as a dict/list. Pass any valid JSON Schema dict.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Generate a fictional person.",
    "json_schema": {
      "type": "object",
      "required": ["name", "age"],
      "properties": {
        "name": {"type": "string"},
        "age":  {"type": "integer"}
      }
    }
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>8. Pro model (alias routes to 3.1 Pro)</h2>
  <p class="desc">Public name <code>gemini-3-pro-preview</code> remaps to <code>google/gemini-3.1-pro-preview</code> upstream.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "How many r letters in strawberry?",
    "model": "gemini-3-pro-preview",
    "thinking_level": "low"
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>9. Explicit Gemini 3.1 Pro</h2>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Explain caching in one sentence.",
    "model": "gemini-3.1-pro-preview",
    "thinking_level": "high"
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>10. Gemini 3.1 Flash Lite (fastest, cheapest)</h2>
  <p class="desc">Supports the full <code>minimal | low | medium | high</code> thinking range.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Two-line poem about logs.",
    "model": "gemini-3.1-flash-lite-preview",
    "thinking_level": "minimal"
  }' | jq</code></pre>
  </div>
</section>

<section>
  <h2>11. All knobs at once</h2>
  <p class="desc">Reference payload showing every supported field.</p>
  <div class="code-wrap">
    <button class="copy">Copy</button>
    <pre><code>curl -sS -X POST http://localhost:8000/generate \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_SERVER_API_KEY" \\
  -d '{
    "user_prompt": "Extract product details.",
    "user_prompt_type": "text",
    "system_prompt": "You are a meticulous catalog parser.",
    "system_prompt_type": "text",
    "image_urls": ["https://picsum.photos/400/600"],
    "model": "gemini-3-flash-preview",
    "thinking_level": "high",
    "json_schema": {
      "type": "object",
      "required": ["name", "price"],
      "properties": {
        "name":        {"type": "string"},
        "price":       {"type": "number"},
        "description": {"type": "string"}
      }
    }
  }' | jq</code></pre>
  </div>
</section>

</main>

<script>
  document.querySelectorAll("button.copy").forEach(btn => {
    btn.addEventListener("click", async () => {
      const code = btn.parentElement.querySelector("code").innerText;
      try {
        await navigator.clipboard.writeText(code);
        btn.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(() => {
          btn.textContent = "Copy";
          btn.classList.remove("copied");
        }, 1500);
      } catch (e) {
        btn.textContent = "Copy failed";
        setTimeout(() => { btn.textContent = "Copy"; }, 1500);
      }
    });
  });
</script>
</body>
</html>
"""


@router.get("/curl", response_class=HTMLResponse, include_in_schema=False)
def curl_examples(request: Request) -> HTMLResponse:
    """Render copyable curl examples for every supported /generate scenario."""
    base = str(request.base_url).rstrip("/")
    page = _PAGE.replace("http://localhost:8000", base)
    return HTMLResponse(content=page)
