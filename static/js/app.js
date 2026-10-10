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

  // --- Mode switching ---
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
      auto: "Например: Удали фон, поставь автомобиль на ночную улицу Токио, улучши качество",
      generate: "Фотореалистичный спортивный автомобиль на горной дороге во время заката",
      edit: "Замени фон на ночную улицу Токио, сделай освещение кинематографичным",
      analyze: "Какие предметы находятся на фотографии?",
      enhance: "Можно оставить пустым — будет применено авто-улучшение",
      remove_bg: "Можно оставить пустым",
    };
    promptInput.placeholder = placeholders[mode] || "Опишите задачу…";
  }

  // --- File handling ---
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
      setStatus("Поддерживаются только JPEG, PNG, WEBP", "error");
      return;
    }
    currentFile = file;
    const url = URL.createObjectURL(file);
    sourceImg.src = url;
    sourcePreview.classList.remove("hidden");
    uploadZone.querySelector(".upload-inner").classList.add("hidden");
  }

  // --- Run ---
  runBtn.addEventListener("click", run);

  async function run() {
    setStatus("");
    imageResult.classList.add("hidden");
    textResult.classList.add("hidden");
    setLoading(true);

    try {
      let res;
      if (mode === "generate") {
        res = await postJSON("/api/generate", {
          prompt: promptInput.value.trim(),
          provider: providerSelect.value || undefined,
        });
      } else if (mode === "edit") {
        res = await postForm("/api/edit", {
          prompt: promptInput.value.trim(),
          image: currentFile,
          provider: providerSelect.value || undefined,
        });
      } else if (mode === "analyze") {
        res = await postForm("/api/analyze", {
          question: promptInput.value.trim() || "Опиши подробно содержимое этого изображения.",
          image: currentFile,
          provider: providerSelect.value || undefined,
        });
      } else if (mode === "enhance") {
        res = await postForm("/api/enhance", {
          mode: $("#enhanceMode").value,
          image: currentFile,
        });
      } else if (mode === "remove_bg") {
        res = await postForm("/api/remove-background", {
          image: currentFile,
        });
      } else {
        // auto
        res = await postForm("/api/auto-process", {
          prompt: promptInput.value.trim(),
          image: currentFile,
          provider: providerSelect.value || undefined,
        });
      }

      if (!res.success) {
        setStatus(res.error || res.message || "Ошибка", "error");
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
      let msg = res.message || "Готово";
      if (res.plan && res.plan.length) msg += " · план: " + res.plan.join(" → ");
      setStatus(msg, "success");
    } catch (err) {
      setStatus(err.message || "Сетевая ошибка", "error");
    } finally {
      setLoading(false);
    }
  }

  function setLoading(on) {
    runBtn.disabled = on;
    runSpinner.classList.toggle("hidden", !on);
    $(".btn-text").textContent = on ? "Обработка…" : "Запустить";
  }

  function setStatus(text, type) {
    statusBar.textContent = text;
    statusBar.className = "status-bar" + (type ? " " + type : "");
  }

  async function postJSON(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }

  async function postForm(url, fields) {
    const fd = new FormData();
    for (const [k, v] of Object.entries(fields)) {
      if (v === undefined || v === null) continue;
      if (k === "image" && !v) continue;
      fd.append(k, v);
    }
    const r = await fetch(url, { method: "POST", body: fd });
    return r.json();
  }

  // --- Providers & health ---
  async function loadProviders() {
    try {
      const r = await fetch("/api/providers");
      const data = await r.json();
      providerSelect.innerHTML = '<option value="">по умолчанию</option>';
      (data.providers || []).forEach((p) => {
        if (p.name === "local") return;
        const opt = document.createElement("option");
        opt.value = p.name;
        opt.textContent = p.name + (p.configured ? "" : " (не настроен)");
        providerSelect.appendChild(opt);
      });
      const configured = (data.providers || []).filter((p) => p.configured && p.name !== "local");
      providerHint.textContent = configured.length
        ? "Доступно: " + configured.map((p) => p.name).join(", ")
        : "API-ключи не заданы — локальные функции (фон, улучшение) работают";
    } catch (_) {
      providerHint.textContent = "Не удалось загрузить список провайдеров";
    }
  }

  async function checkHealth() {
    try {
      const r = await fetch("/api/health");
      const data = await r.json();
      healthStatus.textContent = data.status === "ok" ? "онлайн" : "частично";
      healthStatus.className = "header-status " + (data.status === "ok" ? "ok" : "err");
    } catch (_) {
      healthStatus.textContent = "офлайн";
      healthStatus.className = "header-status err";
    }
  }

  async function loadHistory() {
    historyList.innerHTML = "<p class='hint'>Загрузка…</p>";
    try {
      const r = await fetch("/api/history?limit=30");
      const items = await r.json();
      if (!items.length) {
        historyList.innerHTML = "<p class='hint'>История пуста</p>";
        return;
      }
      historyList.innerHTML = items
        .map((it) => {
          const st = it.status === "completed" ? "status-completed" : it.status === "failed" ? "status-failed" : "";
          const link = it.result_url
            ? `<a href="${it.result_url}" target="_blank" class="link-btn">результат</a>`
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
      historyList.innerHTML = "<p class='hint'>Ошибка загрузки истории</p>";
    }
  }

  updateUIForMode();
  loadProviders();
  checkHealth();
})();
