(() => {
  "use strict";

  const pendingChatSubmits = new WeakSet();

  function statusFor(form) {
    let status = form.previousElementSibling;
    if (!status?.classList.contains("chat-connection-status")) {
      status = document.createElement("p");
      status.className = "chat-connection-status";
      status.setAttribute("aria-live", "polite");
      form.before(status);
    }
    return status;
  }

  function retryUntilSocketIsReady(form) {
    if (pendingChatSubmits.has(form)) return;
    const input = form.querySelector("input");
    const original = input?.value.trim();
    if (!input || !original) return;

    pendingChatSubmits.add(form);
    const status = statusFor(form);
    let attempt = 0;

    const check = () => {
      if (!form.isConnected || input.value.trim() !== original) {
        pendingChatSubmits.delete(form);
        status.textContent = "";
        status.classList.remove("is-error");
        return;
      }

      attempt += 1;
      if (attempt > 20) {
        pendingChatSubmits.delete(form);
        status.textContent = "A conexão com o chat demorou mais que o esperado. Tente enviar novamente.";
        status.classList.add("is-error");
        return;
      }

      if (attempt > 1) status.textContent = "Conectando ao chat…";
      form.requestSubmit();
      window.setTimeout(check, 220);
    };

    window.setTimeout(check, 220);
  }

  document.addEventListener("keydown", event => {
    const input = event.target.closest?.("#chat-form input");
    if (!input || event.key !== "Enter" || event.isComposing || event.ctrlKey || event.altKey || event.metaKey) return;
    event.preventDefault();
    input.closest("form")?.requestSubmit();
  }, true);

  document.addEventListener("submit", event => {
    const form = event.target.closest?.("#chat-form");
    if (form) retryUntilSocketIsReady(form);
  }, true);
})();
