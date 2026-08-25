/**
 * AI Tool-Calling Assistant - Frontend Application Controller
 * Handles SSE chat streaming, tool telemetry, document analysis, and settings.
 */

// Application State
const state = {
  activeView: "chat-view",
  currentProvider: "mock",
  currentModel: "Heuristic Engine",
  messages: [],
  registeredTools: [],
  activeDoc: null,
  isGenerating: false,
};

// DOM Elements
const elements = {
  // Navigation & Views
  navTabs: document.querySelectorAll(".nav-tab"),
  views: document.querySelectorAll(".view-panel"),
  sidebar: document.getElementById("sidebar"),
  btnToggleSidebar: document.getElementById("btn-toggle-sidebar"),
  btnThemeToggle: document.getElementById("btn-theme-toggle"),
  themeIcon: document.getElementById("theme-icon"),
  headerProviderName: document.getElementById("header-provider-name"),
  headerModelName: document.getElementById("header-model-name"),
  providerBadge: document.getElementById("provider-badge"),

  // Chat Elements
  chatThread: document.getElementById("chat-thread"),
  welcomeHero: document.getElementById("welcome-hero"),
  messagesList: document.getElementById("messages-list"),
  chatForm: document.getElementById("chat-form"),
  chatInput: document.getElementById("chat-input"),
  btnSend: document.getElementById("btn-send-message"),
  sendIcon: document.getElementById("send-icon"),
  liveProgressBar: document.getElementById("live-progress-bar"),
  liveProgressText: document.getElementById("live-progress-text"),
  inputProviderIndicator: document.getElementById("input-provider-indicator"),
  fileUploadInput: document.getElementById("file-upload-input"),
  promptChips: document.querySelectorAll(".prompt-chip"),
  btnNewChat: document.getElementById("btn-new-chat"),
  btnClearChat: document.getElementById("btn-clear-chat"),
  btnExportChat: document.getElementById("btn-export-chat"),

  // Quick Currency Widget
  qcAmount: document.getElementById("qc-amount"),
  qcFrom: document.getElementById("qc-from"),
  qcTo: document.getElementById("qc-to"),
  btnQuickConvert: document.getElementById("btn-quick-convert"),
  qcResult: document.getElementById("qc-result"),

  // Document Deck Elements
  docDropzone: document.getElementById("doc-dropzone"),
  docDeckFileInput: document.getElementById("doc-deck-file-input"),
  btnBrowseDoc: document.getElementById("btn-browse-doc"),
  docAnalysisResults: document.getElementById("doc-analysis-results"),
  resFilename: document.getElementById("res-filename"),
  resDoctype: document.getElementById("res-doctype"),
  resWordcount: document.getElementById("res-wordcount"),
  resReadtime: document.getElementById("res-readtime"),
  resSummaryContent: document.getElementById("res-summary-content"),
  resHighlightsContent: document.getElementById("res-highlights-content"),
  docQueryInput: document.getElementById("doc-query-input"),
  btnDocQuery: document.getElementById("btn-doc-query"),

  // Playground Elements
  btnRefreshTools: document.getElementById("btn-refresh-tools"),
  toolPickerList: document.getElementById("tool-picker-list"),
  toolSchemaJson: document.getElementById("tool-schema-json"),
  playgroundExecForm: document.getElementById("playground-exec-form"),
  playgroundParamsFields: document.getElementById("playground-params-fields"),
  playgroundExecOutput: document.getElementById("playground-exec-output"),
  playgroundExecDuration: document.getElementById("playground-exec-duration"),

  // Settings Modal
  settingsModal: document.getElementById("settings-modal"),
  btnOpenSettings: document.getElementById("btn-open-settings"),
  btnCloseSettings: document.getElementById("btn-close-settings"),
  btnCancelSettings: document.getElementById("btn-cancel-settings"),
  btnSaveSettings: document.getElementById("btn-save-settings"),
  settingsProvider: document.getElementById("settings-provider"),
  groupGemini: document.getElementById("group-gemini"),
  groupOpenai: document.getElementById("group-openai"),
  settingsGeminiKey: document.getElementById("settings-gemini-key"),
  settingsGeminiModel: document.getElementById("settings-gemini-model"),
  settingsOpenaiKey: document.getElementById("settings-openai-key"),
  settingsOpenaiModel: document.getElementById("settings-openai-model"),
  settingsOpenaiBase: document.getElementById("settings-openai-base"),
  settingsTemp: document.getElementById("settings-temp"),
  tempValDisplay: document.getElementById("temp-val-display"),
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  initIcons();
  initTheme();
  setupEventListeners();
  loadServerSettings();
  loadToolsRegistry();
});

function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// Theme Management
function initTheme() {
  const savedTheme = localStorage.getItem("ai_agent_theme") || "dark";
  document.body.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);
}

function updateThemeIcon(theme) {
  if (elements.themeIcon) {
    elements.themeIcon.setAttribute("data-lucide", theme === "dark" ? "sun" : "moon");
    initIcons();
  }
}

function toggleTheme() {
  const current = document.body.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.body.setAttribute("data-theme", next);
  localStorage.setItem("ai_agent_theme", next);
  updateThemeIcon(next);
}

// Event Listeners Setup
function setupEventListeners() {
  // View Navigation Tabs
  elements.navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const viewId = tab.getAttribute("data-view");
      switchView(viewId);
    });
  });

  // Theme & Sidebar
  elements.btnThemeToggle.addEventListener("click", toggleTheme);
  if (elements.btnToggleSidebar) {
    elements.btnToggleSidebar.addEventListener("click", () => {
      elements.sidebar.classList.toggle("open");
    });
  }

  // Chat Form & Textarea Auto-Resize
  elements.chatForm.addEventListener("submit", handleChatSubmit);
  elements.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      elements.chatForm.dispatchEvent(new Event("submit"));
    }
  });
  elements.chatInput.addEventListener("input", () => {
    elements.chatInput.style.height = "auto";
    elements.chatInput.style.height = Math.min(elements.chatInput.scrollHeight, 120) + "px";
  });

  // Prompt Chips
  elements.promptChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const text = chip.getAttribute("data-prompt");
      elements.chatInput.value = text;
      elements.chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // New Chat & Clear History
  elements.btnNewChat.addEventListener("click", resetConversation);
  elements.btnClearChat.addEventListener("click", clearConversationMemory);
  elements.btnExportChat.addEventListener("click", exportConversationMarkdown);

  // File Upload Attachments in Chat
  elements.fileUploadInput.addEventListener("change", handleChatFileUpload);

  // Quick Currency Converter
  elements.btnQuickConvert.addEventListener("click", handleQuickCurrencyConvert);

  // Document Deck Dropzone & Upload
  elements.btnBrowseDoc.addEventListener("click", () => elements.docDeckFileInput.click());
  elements.docDeckFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) uploadDocumentFile(e.target.files[0]);
  });
  elements.docDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    elements.docDropzone.classList.add("drag-over");
  });
  elements.docDropzone.addEventListener("dragleave", () => {
    elements.docDropzone.classList.remove("drag-over");
  });
  elements.docDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    elements.docDropzone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) uploadDocumentFile(e.dataTransfer.files[0]);
  });
  elements.btnDocQuery.addEventListener("click", handleDocQuery);

  // Tool Playground
  elements.btnRefreshTools.addEventListener("click", loadToolsRegistry);
  elements.playgroundExecForm.addEventListener("submit", handlePlaygroundExecute);

  // Settings Modal
  elements.btnOpenSettings.addEventListener("click", openSettingsModal);
  elements.providerBadge.addEventListener("click", openSettingsModal);
  elements.btnCloseSettings.addEventListener("click", closeSettingsModal);
  elements.btnCancelSettings.addEventListener("click", closeSettingsModal);
  elements.btnSaveSettings.addEventListener("click", saveServerSettings);
  elements.settingsProvider.addEventListener("change", handleProviderSelectChange);
  elements.settingsTemp.addEventListener("input", (e) => {
    elements.tempValDisplay.textContent = e.target.value;
  });

  // Password visibility eye toggles
  document.querySelectorAll(".toggle-pwd-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.previousElementSibling;
      input.type = input.type === "password" ? "text" : "password";
    });
  });
}

// Switch Active View
function switchView(viewId) {
  state.activeView = viewId;
  elements.navTabs.forEach((t) => {
    t.classList.toggle("active", t.getAttribute("data-view") === viewId);
  });
  elements.views.forEach((v) => {
    v.classList.toggle("active-view", v.id === viewId);
  });
  initIcons();
}

// Load Server Settings
async function loadServerSettings() {
  try {
    const res = await fetch("/api/settings");
    if (res.ok) {
      const data = await res.json();
      state.currentProvider = data.llm_provider || "mock";
      elements.headerProviderName.textContent = state.currentProvider.toUpperCase();
      elements.settingsProvider.value = state.currentProvider;

      if (state.currentProvider === "gemini") {
        state.currentModel = data.gemini_model;
        elements.settingsGeminiModel.value = data.gemini_model;
      } else if (state.currentProvider === "openai") {
        state.currentModel = data.openai_model;
        elements.settingsOpenaiModel.value = data.openai_model;
      } else {
        state.currentModel = "Heuristic Engine";
      }

      elements.headerModelName.textContent = state.currentModel;
      elements.inputProviderIndicator.textContent = `Running on: ${state.currentProvider.toUpperCase()} (${state.currentModel})`;
      elements.settingsTemp.value = data.temperature;
      elements.tempValDisplay.textContent = data.temperature;
      updateProviderConfigVisibility(state.currentProvider);
    }
  } catch (err) {
    console.warn("Could not connect to backend settings API; running in standalone mode.", err);
  }
}

// Settings Modal Handlers
function openSettingsModal() {
  elements.settingsModal.style.display = "flex";
  initIcons();
}

function closeSettingsModal() {
  elements.settingsModal.style.display = "none";
}

function handleProviderSelectChange() {
  updateProviderConfigVisibility(elements.settingsProvider.value);
}

function updateProviderConfigVisibility(provider) {
  elements.groupGemini.style.display = provider === "gemini" ? "block" : "none";
  elements.groupOpenai.style.display = provider === "openai" ? "block" : "none";
  initIcons();
}

async function saveServerSettings() {
  const payload = {
    llm_provider: elements.settingsProvider.value,
    temperature: parseFloat(elements.settingsTemp.value),
  };

  if (payload.llm_provider === "gemini") {
    if (elements.settingsGeminiKey.value.trim()) payload.gemini_api_key = elements.settingsGeminiKey.value.trim();
    payload.gemini_model = elements.settingsGeminiModel.value;
  } else if (payload.llm_provider === "openai") {
    if (elements.settingsOpenaiKey.value.trim()) payload.openai_api_key = elements.settingsOpenaiKey.value.trim();
    payload.openai_model = elements.settingsOpenaiModel.value;
    if (elements.settingsOpenaiBase.value.trim()) payload.openai_base_url = elements.settingsOpenaiBase.value.trim();
  }

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      closeSettingsModal();
      await loadServerSettings();
    }
  } catch (err) {
    alert("Error saving settings: " + err.message);
  }
}

// Load Tools Registry
async function loadToolsRegistry() {
  try {
    const res = await fetch("/api/tools");
    if (res.ok) {
      const data = await res.json();
      state.registeredTools = data.tools || [];
      renderToolPickerList();
    }
  } catch (err) {
    console.error("Error loading tools:", err);
  }
}

function renderToolPickerList() {
  elements.toolPickerList.innerHTML = "";
  if (!state.registeredTools.length) return;

  state.registeredTools.forEach((tool, index) => {
    const item = document.createElement("div");
    item.className = `tool-picker-item ${index === 0 ? "active" : ""}`;
    item.innerHTML = `
      <div>
        <strong>${tool.name}</strong>
        <p style="font-size: 0.75rem; color: var(--text-dim);">${tool.description.slice(0, 50)}...</p>
      </div>
      <i data-lucide="chevron-right" style="width: 16px; height: 16px; color: var(--text-dim);"></i>
    `;
    item.addEventListener("click", () => {
      document.querySelectorAll(".tool-picker-item").forEach((el) => el.classList.remove("active"));
      item.classList.add("active");
      selectToolInPlayground(tool);
    });
    elements.toolPickerList.appendChild(item);
  });

  selectToolInPlayground(state.registeredTools[0]);
  initIcons();
}

function selectToolInPlayground(tool) {
  elements.toolSchemaJson.textContent = JSON.stringify(tool, null, 2);
  elements.playgroundParamsFields.innerHTML = "";

  const properties = tool.parameters.properties || {};
  const required = tool.parameters.required || [];

  for (const [propName, propInfo] of Object.entries(properties)) {
    const formGroup = document.createElement("div");
    formGroup.className = "form-group";
    formGroup.style.marginBottom = "0.75rem";

    const isReq = required.includes(propName);
    const label = document.createElement("label");
    label.innerHTML = `${propName} ${isReq ? '<span style="color: var(--rose-glow)">*</span>' : ""}`;

    const input = document.createElement("input");
    input.className = "form-control";
    input.name = propName;
    input.placeholder = propInfo.description || `Enter ${propName}`;
    input.required = isReq;

    // Default sample values for ease of testing
    if (propName === "expression") input.value = "(15 * 4) + sqrt(256)";
    if (propName === "amount") input.value = "500";
    if (propName === "from_currency") input.value = "USD";
    if (propName === "to_currency") input.value = "EUR";
    if (propName === "location") input.value = "Tokyo";
    if (propName === "query") input.value = "latest tech news";
    if (propName === "document_ref") input.value = state.activeDoc?.filename || "Sample Document";

    formGroup.appendChild(label);
    formGroup.appendChild(input);
    elements.playgroundParamsFields.appendChild(formGroup);
  }
}

async function handlePlaygroundExecute(e) {
  e.preventDefault();
  const activeItem = document.querySelector(".tool-picker-item.active strong");
  if (!activeItem) return;

  const toolName = activeItem.textContent.trim();
  const formData = new FormData(elements.playgroundExecForm);
  const args = {};

  formData.forEach((val, key) => {
    if (!isNaN(val) && val.trim() !== "") {
      args[key] = Number(val);
    } else {
      args[key] = val;
    }
  });

  elements.playgroundExecOutput.textContent = "Executing tool...";
  elements.playgroundExecDuration.textContent = "Duration: ...";

  try {
    const res = await fetch("/api/tools/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tool_name: toolName, arguments: args }),
    });
    if (res.ok) {
      const data = await res.json();
      elements.playgroundExecOutput.textContent = data.result;
      elements.playgroundExecDuration.textContent = `Duration: ${data.duration_ms}ms`;
    } else {
      elements.playgroundExecOutput.textContent = "Error executing tool: " + res.statusText;
    }
  } catch (err) {
    elements.playgroundExecOutput.textContent = "Network error: " + err.message;
  }
}

// Quick Currency Converter in Sidebar
async function handleQuickCurrencyConvert() {
  const amount = parseFloat(elements.qcAmount.value) || 100;
  const fromCurr = elements.qcFrom.value;
  const toCurr = elements.qcTo.value;

  elements.qcResult.textContent = "Converting...";

  try {
    const res = await fetch("/api/tools/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool_name: "convert_currency",
        arguments: { amount: amount, from_currency: fromCurr, to_currency: toCurr },
      }),
    });
    if (res.ok) {
      const data = await res.json();
      const lines = data.result.split("\n");
      const summaryLine = lines.find((l) => l.includes("=")) || data.result;
      elements.qcResult.textContent = summaryLine.replace("•", "").trim();
    }
  } catch (err) {
    elements.qcResult.textContent = "Conversion error";
  }
}

// Document Upload & Analysis Deck
async function uploadDocumentFile(file) {
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  elements.docDropzone.style.display = "none";
  elements.docAnalysisResults.style.display = "block";
  elements.resSummaryContent.textContent = "Analyzing document content and extracting key highlights...";
  elements.resHighlightsContent.innerHTML = '<div class="progress-spinner" style="margin: 2rem auto;"></div>';

  try {
    const res = await fetch("/api/upload-doc", {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      state.activeDoc = data;
      renderDocumentAnalysis(data);
    } else {
      alert("Failed to process document: " + res.statusText);
      elements.docDropzone.style.display = "flex";
      elements.docAnalysisResults.style.display = "none";
    }
  } catch (err) {
    alert("Network error: " + err.message);
  }
}

function renderDocumentAnalysis(data) {
  const an = data.analysis;
  elements.resFilename.textContent = data.filename;
  elements.resDoctype.textContent = (data.doc_type || "TEXT").toUpperCase();
  elements.resWordcount.textContent = `${an.word_count.toLocaleString()} words`;
  elements.resReadtime.textContent = `~${an.reading_time_min} mins`;

  elements.resSummaryContent.innerHTML = `<p>${an.summary}</p>`;
  elements.resHighlightsContent.innerHTML = "";

  if (an.highlights && an.highlights.length) {
    an.highlights.forEach((hl) => {
      const div = document.createElement("div");
      div.className = "highlight-item";
      div.innerHTML = `
        <span class="highlight-category">${hl.category} (Score: ${hl.score})</span>
        <p class="highlight-text">"${hl.text}"</p>
      `;
      elements.resHighlightsContent.appendChild(div);
    });
  } else {
    elements.resHighlightsContent.innerHTML = '<p class="text-dim">No specific quotes highlighted.</p>';
  }

  initIcons();
}

function handleDocQuery() {
  const query = elements.docQueryInput.value.trim();
  if (!query || !state.activeDoc) return;

  // Switch to Chat view and send query referencing this document
  switchView("chat-view");
  const prompt = `Based on document '${state.activeDoc.filename}': ${query}`;
  elements.chatInput.value = prompt;
  elements.chatForm.dispatchEvent(new Event("submit"));
}

function handleChatFileUpload(e) {
  if (e.target.files.length > 0) {
    const file = e.target.files[0];
    uploadDocumentFile(file).then(() => {
      elements.chatInput.value = `Summarize and extract key highlights from the uploaded document '${file.name}'`;
    });
  }
}

// Chat Submission & SSE Streaming
async function handleChatSubmit(e) {
  e.preventDefault();
  const text = elements.chatInput.value.trim();
  if (!text || state.isGenerating) return;

  elements.welcomeHero.style.display = "none";
  elements.chatInput.value = "";
  elements.chatInput.style.height = "auto";

  // Append User Message
  appendMessage({ role: "user", content: text });

  // Assistant Container with Step Visualizer
  const assistantMsgObj = {
    role: "assistant",
    content: "",
    steps: [],
  };
  const msgEl = appendAssistantPlaceholder(assistantMsgObj);

  state.isGenerating = true;
  elements.liveProgressBar.style.display = "flex";
  elements.liveProgressText.textContent = "Agent is reasoning & selecting tools...";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, provider: state.currentProvider }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // keep remaining unfinished line

      for (const block of lines) {
        if (!block.startsWith("data:")) continue;
        const jsonStr = block.replace("data:", "").trim();
        if (jsonStr === "[DONE]") break;

        try {
          const event = JSON.parse(jsonStr);
          handleStreamEvent(event, assistantMsgObj, msgEl);
        } catch (parseErr) {
          console.warn("SSE parse error:", parseErr);
        }
      }
    }
  } catch (err) {
    assistantMsgObj.content = `⚠ Connection Error: ${err.message}`;
    updateAssistantMessageDOM(assistantMsgObj, msgEl);
  } finally {
    state.isGenerating = false;
    elements.liveProgressBar.style.display = "none";
    initIcons();
  }
}

function handleStreamEvent(event, msgObj, msgEl) {
  if (event.type === "tool_call") {
    elements.liveProgressText.textContent = `Executing tool: ${event.tool}...`;
    msgObj.steps.push({
      tool: event.tool,
      args: event.args,
      status: "running",
      result: null,
    });
    updateAssistantMessageDOM(msgObj, msgEl);
  } else if (event.type === "tool_result") {
    const currentStep = msgObj.steps.find((s) => s.tool === event.tool && !s.result);
    if (currentStep) {
      currentStep.status = "completed";
      currentStep.result = event.result;
    }
    elements.liveProgressText.textContent = `Tool '${event.tool}' finished. Synthesizing response...`;
    updateAssistantMessageDOM(msgObj, msgEl);
  } else if (event.type === "provider_fallback") {
    elements.liveProgressText.textContent = `Provider failover: ${event.failed_provider} -> ${event.next_provider}`;
  } else if (event.type === "final_response") {
    msgObj.content = event.content;
    msgObj.provider = event.provider;
    msgObj.latency_ms = event.latency_ms;
    updateAssistantMessageDOM(msgObj, msgEl);
  }
  elements.chatThread.scrollTop = elements.chatThread.scrollHeight;
}

function appendMessage(msg) {
  state.messages.push(msg);
  const wrap = document.createElement("div");
  wrap.className = `message-wrap user-wrap`;
  wrap.innerHTML = `
    <div class="message-avatar user-avatar"><i data-lucide="user"></i></div>
    <div class="message-body">
      <div class="message-meta">
        <span class="sender-name">You</span>
        <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="message-bubble">${escapeHtml(msg.content)}</div>
    </div>
  `;
  elements.messagesList.appendChild(wrap);
  elements.chatThread.scrollTop = elements.chatThread.scrollHeight;
  initIcons();
}

function appendAssistantPlaceholder(msgObj) {
  state.messages.push(msgObj);
  const wrap = document.createElement("div");
  wrap.className = "message-wrap assistant-wrap";
  wrap.innerHTML = `
    <div class="message-avatar assistant-avatar"><i data-lucide="bot"></i></div>
    <div class="message-body">
      <div class="message-meta">
        <span class="sender-name">AI Assistant</span>
        <span class="message-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="steps-container"></div>
      <div class="message-bubble assistant-text-bubble">
        <div class="progress-spinner" style="width: 18px; height: 18px; border-width: 2px;"></div>
      </div>
    </div>
  `;
  elements.messagesList.appendChild(wrap);
  elements.chatThread.scrollTop = elements.chatThread.scrollHeight;
  initIcons();
  return wrap;
}

function updateAssistantMessageDOM(msgObj, msgEl) {
  const stepsContainer = msgEl.querySelector(".steps-container");
  const bubble = msgEl.querySelector(".assistant-text-bubble");

  // Render Step Cards
  stepsContainer.innerHTML = "";
  msgObj.steps.forEach((step) => {
    const stepCard = document.createElement("div");
    stepCard.className = "tool-step-card";
    const toolIcon = getToolIconName(step.tool);

    stepCard.innerHTML = `
      <div class="tool-step-header">
        <div class="tool-step-title">
          <i data-lucide="${toolIcon}"></i>
          <span>${step.tool}</span>
        </div>
        <span class="badge-pill ${step.status === 'running' ? 'new-pill' : 'badge-pill'}" style="background: rgba(0, 240, 255, 0.1); color: var(--cyan-glow);">
          ${step.status === 'running' ? 'Executing...' : 'Completed'}
        </span>
      </div>
      <div class="tool-step-args"><strong>Input:</strong> ${JSON.stringify(step.args)}</div>
      ${step.result ? `<div class="tool-step-result">${escapeHtml(step.result)}</div>` : ''}
    `;
    stepsContainer.appendChild(stepCard);
  });

  // Render Final Markdown Content
  if (msgObj.content) {
    const rawHtml = marked.parse(msgObj.content);
    bubble.innerHTML = DOMPurify.sanitize(rawHtml);
  }
  initIcons();
}

function getToolIconName(toolName) {
  switch (toolName) {
    case "calculate": return "calculator";
    case "convert_currency": return "coins";
    case "read_document": return "file-text";
    case "get_weather": return "cloud-sun";
    case "search_web": return "globe";
    default: return "wrench";
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function resetConversation() {
  elements.messagesList.innerHTML = "";
  elements.welcomeHero.style.display = "flex";
  state.messages = [];
  elements.chatInput.value = "";
}

async function clearConversationMemory() {
  if (confirm("Reset conversation history?")) {
    try {
      await fetch("/api/clear", { method: "POST" });
      resetConversation();
    } catch (e) {
      resetConversation();
    }
  }
}

function exportConversationMarkdown() {
  if (!state.messages.length) {
    alert("No messages to export.");
    return;
  }
  let doc = "# AI Tool-Calling Assistant - Conversation Log\n\n";
  state.messages.forEach((m) => {
    doc += `### ${m.role === "user" ? "User" : "Assistant"}\n\n${m.content}\n\n---\n\n`;
  });

  const blob = new Blob([doc], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `ai-chat-export-${Date.now()}.md`;
  a.click();
}
