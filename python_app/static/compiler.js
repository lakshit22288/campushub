(function () {
  "use strict";

  const page = document.getElementById("compiler-page");
  if (!page) return;

  const languages = JSON.parse(document.getElementById("compiler-languages").textContent);
  const languageSelect = document.getElementById("compiler-language");
  const fileName = document.getElementById("compiler-file");
  const codeEditor = document.getElementById("compiler-code");
  const inputEditor = document.getElementById("compiler-stdin");
  const gutter = document.getElementById("compiler-gutter");
  const output = document.getElementById("compiler-output");
  const outputText = document.getElementById("compiler-output-text");
  const outputStatus = document.getElementById("compiler-output-status");
  const runButton = document.getElementById("compiler-run");
  const stopButton = document.getElementById("compiler-stop");
  const resetButton = document.getElementById("compiler-reset");
  const livePanel = document.getElementById("compiler-live-input");
  const stdinLabel = document.getElementById("compiler-stdin-label");
  const liveForm = document.getElementById("compiler-live-form");
  const livePrompt = document.getElementById("compiler-live-prompt");
  const liveResponse = document.getElementById("compiler-live-response");
  const runnerStatus = document.getElementById("compiler-runner-status");
  const privacyNote = document.getElementById("compiler-privacy-note");
  const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || "";

  const MAX_OUTPUT_LENGTH = 100_000;
  const PYTHON_RUN_TIMEOUT_MS = 20_000;
  const PYTHON_LOAD_TIMEOUT_MS = 120_000;
  let language = "python";
  let activeWorker = null;
  let controller = null;
  let timer = null;
  let runStartedAt = 0;
  let liveOutput = "";
  let result = null;
  let error = "";
  let running = false;
  let inputRequest = null;

  function updateGutter() {
    const lines = codeEditor.value.split("\n").length;
    gutter.textContent = Array.from({ length: lines }, (_, index) => index + 1).join("\n");
    gutter.scrollTop = codeEditor.scrollTop;
  }

  function combinedOutput() {
    if (language === "python") {
      return `${liveOutput}${result?.exception ? `${liveOutput ? "\n" : ""}${result.exception}` : ""}`.trimEnd();
    }
    return result
      ? [result.stdout, result.stderr, result.exception].filter(Boolean).join("\n").trimEnd()
      : liveOutput;
  }

  function render() {
    const config = languages[language];
    fileName.textContent = config.file;
    codeEditor.setAttribute("aria-label", `${config.label} source code`);
    livePanel.hidden = language !== "python";
    stdinLabel.hidden = language === "python";
    privacyNote.textContent = language === "python"
      ? "Python runs in your browser; input() pauses for your response. The Pyodide runtime downloads from jsDelivr on first use; your code stays in this browser."
      : "Your source code and pre-entered input are sent to OneCompiler through CampusHub. Do not include passwords, keys, or private data.";
    languageSelect.disabled = running;
    runButton.hidden = running;
    stopButton.hidden = !running;
    resetButton.disabled = running;
    output.classList.toggle("has-error", Boolean(error || result?.stderr || result?.exception));
    if (error) {
      outputStatus.textContent = "Run failed";
      outputText.textContent = error;
    } else if (result) {
      const failed = Boolean(result.stderr || result.exception);
      const timedOut = /\b(time limit exceeded|timed out|timeout)\b/i.test(
        [result.stderr, result.exception].filter(Boolean).join("\n")
      );
      outputStatus.textContent = timedOut
        ? "Time limit exceeded"
        : failed
          ? "Finished with errors"
          : result.executionTime == null
            ? "Finished"
            : `Finished · ${result.executionTime} ms`;
      outputText.textContent = combinedOutput() || (failed
        ? "The program did not produce output."
        : "Program completed with no output.");
    } else if (running) {
      outputStatus.textContent = language === "python" ? "Running in browser…" : "Running code with your input…";
      outputText.textContent = language === "python"
        ? liveOutput || "Run your code. Any input() call will pause here for your response."
        : "Running your program…";
    } else {
      outputStatus.textContent = "Waiting to run";
      outputText.textContent = language === "python"
        ? liveOutput || "Run your code. Any input() call will pause here for your response."
        : "Run your code to see the result here.";
    }
    liveForm.hidden = inputRequest === null;
    runnerStatus.hidden = inputRequest !== null;
    if (inputRequest !== null) livePrompt.textContent = inputRequest;
    updateGutter();
  }

  function clearTimer() {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  }

  function finishRun(nextResult, nextError = "") {
    clearTimer();
    running = false;
    inputRequest = null;
    result = nextResult;
    error = nextError;
    activeWorker = null;
    controller = null;
    runnerStatus.textContent = "";
    render();
  }

  function stopRun(message) {
    clearTimer();
    if (activeWorker) activeWorker.terminate();
    if (controller) controller.abort();
    activeWorker = null;
    controller = null;
    running = false;
    inputRequest = null;
    runnerStatus.textContent = "";
    result = null;
    error = message || "";
    render();
  }

  function appendOutput(text) {
    liveOutput += text;
    if (liveOutput.length > MAX_OUTPUT_LENGTH) {
      liveOutput = liveOutput.slice(0, MAX_OUTPUT_LENGTH);
      stopRun("Output exceeded the 100,000 character safety limit. Reduce the program's output and try again.");
      return false;
    }
    render();
    return true;
  }

  function runPython() {
    running = true;
    result = null;
    error = "";
    liveOutput = "";
    inputRequest = null;
    runnerStatus.textContent = "Starting Python in your browser…";
    runStartedAt = Date.now();

    try {
      activeWorker = new Worker("/static/python/compiler.worker.js?v=2", { type: "module" });
    } catch (workerError) {
      finishRun(null, workerError.message || "The browser Python runtime could not start.");
      return;
    }
    activeWorker.onmessage = event => {
      const message = event.data || {};
      if (message.type === "loading") {
        runnerStatus.textContent = "Loading Python runtime in your browser (first run may take a little longer)…";
        clearTimer();
        timer = window.setTimeout(
          () => stopRun("Python could not load in time. Check your connection and try again."),
          PYTHON_LOAD_TIMEOUT_MS
        );
      } else if (message.type === "running") {
        clearTimer();
        runStartedAt = Date.now();
        runnerStatus.textContent = "Running in your browser…";
        timer = window.setTimeout(
          () => stopRun("Program stopped after 20 seconds. Check for an infinite loop, then run it again."),
          PYTHON_RUN_TIMEOUT_MS
        );
      } else if (message.type === "stdout" || message.type === "stderr") {
        if (typeof message.text === "string") appendOutput(message.text);
      } else if (message.type === "input-request") {
        clearTimer();
        inputRequest = String(message.prompt || "");
        runnerStatus.textContent = "";
        render();
        liveResponse.focus();
        timer = window.setTimeout(
          () => stopRun("Program stopped after waiting two minutes for input."),
          PYTHON_LOAD_TIMEOUT_MS
        );
      } else if (message.type === "done") {
        finishRun({ executionTime: Date.now() - runStartedAt });
      } else if (message.type === "error") {
        finishRun({ exception: message.message || "Python could not run this program.", executionTime: Date.now() - runStartedAt });
      }
    };
    activeWorker.onerror = event => {
      stopRun(event.message || "The browser Python runtime failed.");
    };
    timer = window.setTimeout(
      () => stopRun("Python is taking too long to start. Check your connection and try again."),
      PYTHON_LOAD_TIMEOUT_MS
    );
    activeWorker.postMessage({ type: "run", code: codeEditor.value });
    render();
  }

  async function runCloudCode() {
    const code = codeEditor.value;
    const stdin = inputEditor.value;
    if (code.length > 50_000) {
      error = "Keep the code under 50,000 characters.";
      render();
      return;
    }
    if (stdin.length > 10_000) {
      error = "Keep standard input under 10,000 characters.";
      render();
      return;
    }
    running = true;
    result = null;
    error = "";
    liveOutput = "";
    controller = new AbortController();
    timer = window.setTimeout(() => controller?.abort(), PYTHON_RUN_TIMEOUT_MS + 2_000);
    render();
    try {
      const response = await fetch(page.dataset.executeUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({ language, code, stdin }),
        signal: controller.signal
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(payload?.message || "Could not run this program. Please try again.");
      }
      finishRun(payload);
    } catch (runError) {
      if (runError.name === "AbortError" && !running) return;
      if (runError.name === "AbortError") {
        finishRun(null, "The compiler did not respond within 20 seconds. Try a smaller program or check for an infinite loop.");
      } else {
        finishRun(null, runError.message || "Could not reach the compiler service. Please try again.");
      }
    }
  }

  function runCode() {
    if (running) return;
    if (!codeEditor.value.trim()) {
      error = "Add some code before running the program.";
      render();
      return;
    }
    error = "";
    result = null;
    liveOutput = "";
    if (language === "python") runPython();
    else runCloudCode();
  }

  languageSelect.addEventListener("change", () => {
    language = languageSelect.value;
    codeEditor.value = languages[language].template;
    inputEditor.value = "CampusHub\n";
    result = null;
    error = "";
    liveOutput = "";
    render();
  });
  codeEditor.addEventListener("input", updateGutter);
  codeEditor.addEventListener("scroll", () => { gutter.scrollTop = codeEditor.scrollTop; });
  codeEditor.addEventListener("keydown", event => {
    if (event.key === "Tab") {
      event.preventDefault();
      const start = codeEditor.selectionStart;
      const end = codeEditor.selectionEnd;
      codeEditor.setRangeText("    ", start, end, "end");
      updateGutter();
    }
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      runCode();
    }
  });
  resetButton.addEventListener("click", () => {
    codeEditor.value = languages[language].template;
    inputEditor.value = "CampusHub\n";
    result = null;
    error = "";
    liveOutput = "";
    render();
    codeEditor.focus();
  });
  runButton.addEventListener("click", runCode);
  stopButton.addEventListener("click", () => stopRun("Run stopped."));
  liveForm.addEventListener("submit", event => {
    event.preventDefault();
    if (inputRequest === null || !activeWorker) return;
    activeWorker.postMessage({ type: "input", value: liveResponse.value });
    inputRequest = null;
    liveResponse.value = "";
    runnerStatus.textContent = "Running in your browser…";
    clearTimer();
    timer = window.setTimeout(
      () => stopRun("Program stopped after 20 seconds. Check for an infinite loop, then run it again."),
      PYTHON_RUN_TIMEOUT_MS
    );
    render();
  });

  languageSelect.value = language;
  codeEditor.value = languages[language].template;
  render();
})();
