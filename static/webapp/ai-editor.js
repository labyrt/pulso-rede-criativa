(() => {
  "use strict";

  const csrf = () => decodeURIComponent(
    document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || ""
  );

  function toast(message, type = "") {
    const stack = document.querySelector("#toast-stack");
    if (!stack) return;
    const item = document.createElement("div");
    item.className = `toast ${type}`.trim();
    item.textContent = message;
    stack.append(item);
    setTimeout(() => item.remove(), 4200);
  }

  async function requestCaption(payload) {
    const response = await fetch("/api/v1/ai/caption/", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrf(),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.error?.message || "Não foi possível revisar o texto agora.");
    return data;
  }

  async function editCaption(button) {
    const textarea = document.querySelector("#post-body");
    const form = document.querySelector("#post-form");
    if (!textarea || !form) return;
    const draft = textarea.value.trim();
    if (!draft) {
      toast("Escreva uma ideia inicial primeiro.", "error");
      return;
    }

    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.textContent = "✦ Revisando sem apagar sua voz...";
    try {
      const category = form.querySelector('select[name="category"]')?.value || "arte";
      const data = await requestCaption({
        draft,
        category,
        tone: "autêntico e editorial",
        mode: "natural",
      });
      textarea.value = data.suggestion || draft;
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
      if (data.provider === "gemini" && !data.degraded) {
        toast("Texto revisado pela IA, preservando sua voz.", "success");
      } else {
        toast("A IA generativa está indisponível agora. Seu texto foi preservado sem fórmulas automáticas.");
      }
    } catch (error) {
      toast(error.message, "error");
    } finally {
      button.disabled = false;
      button.innerHTML = originalHtml;
    }
  }

  document.addEventListener("click", event => {
    const button = event.target.closest('[data-action="ai-caption"]');
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    editCaption(button);
  }, true);
})();