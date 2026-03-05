const DEFAULT_API_URL = "http://localhost:8080/task";
const API_URL_STORAGE_KEY = "agent_task_api_url";

const chat = document.getElementById("chat");
const composer = document.getElementById("composer");
const serverUrlInput = document.getElementById("serverUrl");
const promptInput = document.getElementById("prompt");
const maxStepsInput = document.getElementById("maxSteps");
const sendBtn = document.getElementById("sendBtn");

const userTemplate = document.getElementById("userMessageTemplate");
const botTemplate = document.getElementById("botMessageTemplate");

function appendUserMessage(text) {
  const node = userTemplate.content.cloneNode(true);
  node.querySelector(".bubble-text").textContent = text;
  chat.appendChild(node);
  scrollToBottom();
}

function appendBotHtml(html) {
  const node = botTemplate.content.cloneNode(true);
  node.querySelector(".bubble-content").innerHTML = html;
  chat.appendChild(node);
  scrollToBottom();
}

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function money(v, currency = "USD") {
  if (typeof v !== "number" || Number.isNaN(v)) return "n/a";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(v);
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return "n/a";
  if (typeof v === "number" && Number.isFinite(v)) {
    return new Intl.NumberFormat("en-US").format(v);
  }
  if (typeof v === "boolean") return v ? "yes" : "no";
  return String(v);
}

function providerTable(rows = []) {
  if (!rows.length) return "<p>No provider rows.</p>";

  const body = rows
    .map(
      (r) => `
      <tr>
        <td>${r.provider ?? "-"}</td>
        <td>${r.date ?? "-"}</td>
        <td>${r.currency ?? "USD"}</td>
        <td>${money(r.price, r.currency ?? "USD")}</td>
      </tr>`
    )
    .join("");

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Provider</th><th>Date</th><th>Currency</th><th>Price</th></tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function traceTable(rows = []) {
  if (!rows.length) return "<p>No LLM trace rows.</p>";

  const body = rows
    .map(
      (r) => `
      <tr>
        <td>${r.stage ?? "-"}</td>
        <td>${r.model ?? "-"}</td>
        <td>${r.total_tokens ?? "-"}</td>
      </tr>`
    )
    .join("");

  return `
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Stage</th><th>Model</th><th>Total Tokens</th></tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

function notesList(notes = []) {
  if (!notes.length) return "<p>No notes.</p>";
  const items = notes
    .map((n) => {
      const isError = /failed|error|blocked|payment required/i.test(n);
      return `<li class="${isError ? "error" : ""}">${n}</li>`;
    })
    .join("");
  return `<ul class="note-list">${items}</ul>`;
}

function topStats(payload, data) {
  const base = [
    { k: "Task ID", v: payload.task_id },
    { k: "Status", v: payload.done ? "done" : "running" },
    { k: "Blocked", v: payload.blocked },
    { k: "Route", v: payload.route },
    { k: "Steps Taken", v: payload.steps_taken },
  ];

  const result = data.provider_result || {};
  if (Object.keys(result).length) {
    base.push(
      { k: "Selected Provider", v: result.provider },
      { k: "Confidence", v: result.confidence },
      { k: "Consensus", v: result.consensus },
      { k: "Sample Size", v: result.sample_size }
    );
  }

  return base;
}

function keyValueGrid(items = []) {
  return `
    <section class="kv-grid">
      ${items
        .map((i) => `<div class="kv-item"><strong>${i.k}</strong>${fmt(i.v)}</div>`)
        .join("")}
    </section>
  `;
}

function renderDigest(payload) {
  const d = payload?.data || {};
  const result = d.provider_result || {};
  const hasProviderRows = Array.isArray(d.provider_results) && d.provider_results.length > 0;
  const hasTrace = Array.isArray(d.llm_trace) && d.llm_trace.length > 0;
  const hasNotes = Array.isArray(payload.notes) && payload.notes.length > 0;

  const summaryParts = [];
  if (result.provider) summaryParts.push(`selected by <b>${result.provider}</b>`);
  if (result.date) summaryParts.push(`for ${result.date}`);
  if (typeof result.price === "number") {
    summaryParts.push(`value ${money(result.price, result.currency || "USD")}`);
  }
  if (result.confidence) summaryParts.push(`confidence: ${result.confidence}`);

  const summaryText =
    summaryParts.length > 0
      ? `Task completed with ${summaryParts.join(" | ")}.`
      : "Task completed. See structured output sections below.";

  return `
    <section class="summary">
      <strong>Result Digest</strong>
      <p style="margin: .35rem 0 0;">${summaryText}</p>
    </section>

    ${keyValueGrid(topStats(payload, d))}

    ${
      Object.keys(result).length
        ? `
    <section>
      <strong>Selected Result Object</strong>
      ${keyValueGrid(
        Object.entries(result).map(([k, v]) => ({
          k: k.replaceAll("_", " "),
          v: typeof v === "number" && /price|spread|value/.test(k) ? money(v, result.currency || "USD") : v,
        }))
      )}
    </section>`
        : ""
    }

    ${
      hasProviderRows
        ? `
    <section>
      <strong>Provider Comparison</strong>
      ${providerTable(d.provider_results)}
    </section>`
        : ""
    }

    ${
      hasNotes
        ? `
    <section>
      <strong>Execution Notes</strong>
      ${notesList(payload.notes)}
    </section>`
        : ""
    }

    ${
      hasTrace
        ? `
    <section>
      <strong>LLM Trace (Token Cost Hotspots)</strong>
      ${traceTable(d.llm_trace)}
    </section>`
        : ""
    }

    <section>
      <button type="button" class="raw-toggle" data-toggle="raw">Toggle Raw JSON</button>
      <pre hidden>${JSON.stringify(payload, null, 2)}</pre>
    </section>
  `;
}

chat.addEventListener("click", (e) => {
  const button = e.target.closest("[data-toggle='raw']");
  if (!button) return;
  const pre = button.parentElement.querySelector("pre");
  if (!pre) return;
  pre.hidden = !pre.hidden;
});

async function runTask(prompt, maxSteps) {
  const apiUrl = serverUrlInput.value.trim();
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, max_steps: maxSteps }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json();
}

composer.addEventListener("submit", async (e) => {
  e.preventDefault();

  const apiUrl = serverUrlInput.value.trim();
  const prompt = promptInput.value.trim();
  const maxSteps = Number(maxStepsInput.value || 8);
  if (!prompt) return;
  if (!apiUrl) return;

  try {
    const parsed = new URL(apiUrl);
    if (!/^https?:$/.test(parsed.protocol)) {
      throw new Error("Server URL must use http or https.");
    }
  } catch (err) {
    appendBotHtml(`<p><strong>Invalid server URL.</strong></p><p>${err.message}</p>`);
    return;
  }

  appendUserMessage(prompt);
  appendBotHtml("<p>Running task and collecting structured outputs...</p>");

  sendBtn.disabled = true;
  sendBtn.textContent = "Running...";

  try {
    const result = await runTask(prompt, maxSteps);
    chat.lastElementChild?.remove();
    appendBotHtml(renderDigest(result));
  } catch (err) {
    chat.lastElementChild?.remove();
    appendBotHtml(
      `<p><strong>Request failed.</strong></p><p>${err.message}</p><p>If this page is served over HTTPS, a HTTP endpoint may be blocked as mixed content. Serve this UI over HTTP for testing.</p>`
    );
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
});

function initializeApiUrl() {
  const savedUrl = localStorage.getItem(API_URL_STORAGE_KEY);
  serverUrlInput.value = savedUrl || DEFAULT_API_URL;
}

serverUrlInput.addEventListener("change", () => {
  localStorage.setItem(API_URL_STORAGE_KEY, serverUrlInput.value.trim() || DEFAULT_API_URL);
});

initializeApiUrl();

appendBotHtml(
  `<p>Ready. Set your server URL and submit a prompt to call <code>POST /task</code>.</p>`
);
