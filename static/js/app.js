(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  let mode = "auto";
  let currentFile = null;

  const uploadZone = $("#uploadZone");
  const fileInput = $("#fileInput");
  const pickFileBtn = $("#pickFileBtn");
  const sourcePreview = $("#sourcePreview");
  const sourceImg = $("#sourceImg");
  const clearSource = $("#clearSource");
  const promptInput = $("#promptInput");
  const runBtn = $("#runBtn");
  const runSpinner = $("#runSpinner");
  const statusBar = $("#statusBar");
  const imageResult = $("#imageResult");
  const textResult = $("#textResult");
  const resultImg = $("#resultImg");
  const analysisText = $("#analysisText");
  const downloadBtn = $("#downloadBtn");
  const cmpSource = $("#cmpSource");
  const cmpSourceWrap = $("#cmpSourceWrap");
  const enhanceModeWrap = $("#enhanceModeWrap");
  const workPanel = $("#workPanel");
  const historyPanel = $("#historyPanel");
  const historyList = $("#historyList");
  const providerSelect = $("#providerSelect");
  const providerHint = $("#providerHint");
  const healthStatus = $("#healthStatus");

  $$(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".mode-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      mode = btn.dataset.mode;
      if (mode === "history") {
        workPanel.classList.add("hidden");
        historyPanel.classList.remove("hidden");
        loadHistory();
      } else {
        workPanel.classList.remove("hidden");
        historyPanel.classList.add("hidden");
        updateUIForMode();
      }
    });
  });

  function updateUIForMode() {
    enhanceModeWrap.hidden = mode !== "enhance";
    const placeholders = {
      auto: "e.g. Remove background, put the car on a Tokyo night street, enhance quality",
      generate: "Photorealistic sports car on a mountain road at sunset",
      edit: "Replace the background with a Tokyo night street, cinematic lighting",
      analyze: "What objects are in this photo?",
      enhance: "Leave empty for auto enhancement",
      remove_bg: "Leave empty",
    };
    promptInput.placeholder = placeholders[mode] || "Describe the task…";
  }

  pickFileBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });
  uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  clearSource.addEventListener("click", () => {
    currentFile = null;
    fileInput.value = "";
    sourcePreview.classList.add("hidden");
    uploadZone.querySelector(".upload-inner").classList.remove("hidden");
  });

  function setFile(file) {
    if (!file.type.match(/^image\/(jpeg|png|webp)$/)) {
      setStatus("Only JPEG, PNG, WEBP are supported", "error");
      return;
    }
    currentFile = file;
    const url = URL.createObjectURL(file);
    sourceImg.src = url;
    sourcePreview.classList.remove("hidden");
    uploadZone.querySelector(".upload-inner").classList.add("hidden");
  }

  runBtn.addEventListener("click", run);

  async function run() {
    setStatus("");
    imageResult.classList.add("hidden");
    textResult.classList.add("hidden");
    setLoading(true);

    try {
      let res;
      if (mode === "enhance") {
        res = await postForm("/api/enhance", {
          mode: $("#enhanceMode").value,
          image: currentFile,
        });
      } else if (mode === "remove_bg") {
        res = await postForm("/api/remove-background", {
          image: currentFile,
        });
      } else {
        res = await postForm("/api/auto-process", {
          prompt: promptInput.value.trim(),
          image: currentFile,
          provider: providerSelect.value || undefined,
        });
      }

      if (!res.success) {
        setStatus(res.error || res.message || "Error", "error");
        return;
      }

      if (res.result_url) {
        resultImg.src = res.result_url + "?t=" + Date.now();
        downloadBtn.href = res.result_url;
        downloadBtn.download = res.result_url.split("/").pop();
        imageResult.classList.remove("hidden");
        if (currentFile) {
          cmpSource.src = sourceImg.src;
          cmpSourceWrap.hidden = false;
        } else {
          cmpSourceWrap.hidden = true;
        }
      }
      if (res.analysis) {
        analysisText.textContent = res.analysis;
        textResult.classList.remove("hidden");
      }
      let msg = res.message || "Done";
      if (res.plan && res.plan.length) msg += " · plan: " + res.plan.join(" → ");
      setStatus(msg, "success");
    } catch (err) {
      setStatus(err.message || "Network error", "error");
    } finally {
      setLoading(false);
    }
  }

  function setLoading(on) {
    runBtn.disabled = on;
    runSpinner.classList.toggle("hidden", !on);
    $(".btn-text").textContent = on ? "Waiting (up to 2 min)…" : "Run";
    if (on) setStatus("Sending request to the model. Generation usually takes 20–90 seconds…", "");
  }

  function setStatus(text, type) {
    statusBar.textContent = text;
    statusBar.className = "status-bar" + (type ? " " + type : "");
  }

  async function fetchWithTimeout(url, options, ms = 150000) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), ms);
    try {
      const r = await fetch(url, { ...options, signal: ctrl.signal });
      return await r.json();
    } catch (e) {
      if (e.name === "AbortError") {
        throw new Error("Timed out (150s). The provider may be overloaded — try again.");
      }
      throw e;
    } finally {
      clearTimeout(t);
    }
  }

  async function postJSON(url, body) {
    return fetchWithTimeout(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function postForm(url, fields) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v === undefined || v === null) continue;
      if (k === "image" && !v) continue;
      fd.append(k, v);
    }
    return fetchWithTimeout(url, { method: "POST", body: fd });
  }

  async function loadProviders() {
    try {
      const r = await fetch("/api/providers");
      const data = await r.json();
      providerSelect.innerHTML = '<option value="">default</option>';
      (data.providers || []).forEach((p) => {
        if (p.name === "local") return;
        const opt = document.createElement("option");
        opt.value = p.name;
        opt.textContent = p.name + (p.configured ? "" : " (not configured)");
        providerSelect.appendChild(opt);
      });
      const configured = (data.providers || []).filter((p) => p.configured && p.name !== "local");
      providerHint.textContent = configured.length
        ? "Available: " + configured.map((p) => p.name).join(", ")
        : "No API keys set — local tools (background, enhance) still work";
    } catch (_) {
      providerHint.textContent = "Could not load providers";
    }
  }

  async function checkHealth() {
    try {
      const r = await fetch("/api/health");
      const data = await r.json();
      healthStatus.textContent = data.status === "ok" ? "online" : "degraded";
      healthStatus.className = "header-status " + (data.status === "ok" ? "ok" : "err");
    } catch (_) {
      healthStatus.textContent = "offline";
      healthStatus.className = "header-status err";
    }
  }

  async function loadHistory() {
    historyList.innerHTML = "<p class='hint'>Loading…</p>";
    try {
      const r = await fetch("/api/history?limit=30");
      const items = await r.json();
      if (!items.length) {
        historyList.innerHTML = "<p class='hint'>No history yet</p>";
        return;
      }
      historyList.innerHTML = items
        .map((it) => {
          const st =
            it.status === "completed"
              ? "status-completed"
              : it.status === "failed"
                ? "status-failed"
                : "";
          const link = it.result_url
            ? `<a href="${it.result_url}" target="_blank" class="link-btn">result</a>`
            : "";
          return `<div class="history-item">
            <div>
              <div><strong>${it.operation_type}</strong> <span class="${st}">${it.status}</span></div>
              <div class="meta">${(it.prompt || "").slice(0, 120)}</div>
              <div class="meta">${it.provider || ""} ${it.model || ""} · ${it.created_at}</div>
            </div>
            <div>${link}</div>
          </div>`;
        })
        .join("");
    } catch (_) {
      historyList.innerHTML = "<p class='hint'>Failed to load history</p>";
    }
  }

  updateUIForMode();
  loadProviders();
  checkHealth();
})();