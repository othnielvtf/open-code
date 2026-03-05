# Agent Task Chat UI

A lightweight web UI that behaves like a chat client for your general-purpose agent endpoint:

- `POST http://52.77.216.135:8080/task`
- Request body:
  ```json
  {
    "prompt": "Get me BTC price as of 3rd march 2026",
    "max_steps": 8
  }
  ```

The UI is route-agnostic and renders a digest from structured responses (status, notes, selected result object, provider comparisons when present, and LLM trace when present).

## Files

- `index.html` - app shell and chat layout
- `styles.css` - dark mode visual theme
- `app.js` - request handling + response rendering

## Run locally

From this folder:

```bash
python3 -m http.server 5173
```

Open:

- `http://localhost:5173`

## Notes

- The endpoint is currently hardcoded in `app.js` as:
  - `const API_URL = "http://52.77.216.135:8080/task";`
- If you serve this UI over HTTPS, browsers can block HTTP API calls (mixed content). Use HTTP for local testing, or expose the API over HTTPS.

## Expected response shape

The UI can handle generic payloads but is optimized for responses like:

```json
{
  "task_id": "...",
  "route": "...",
  "steps_taken": 3,
  "done": true,
  "blocked": false,
  "notes": ["..."],
  "data": {
    "provider_result": { "provider": "...", "confidence": "..." },
    "provider_results": [{ "provider": "...", "price": 123 }],
    "llm_trace": [{ "stage": "...", "model": "...", "total_tokens": 1000 }]
  }
}
```

## Customize

- Change default prompt in `index.html` (`#prompt` value/placeholder)
- Change max step bounds in `index.html` (`#maxSteps`)
- Adjust summary cards/sections in `app.js` (`renderDigest`)
- Tune dark palette in `styles.css` (`:root` variables)
