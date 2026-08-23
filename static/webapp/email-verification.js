(() => {
  "use strict";

  const form = document.querySelector("#resend-verification-form");
  if (!form) return;
  const emailInput = form.querySelector('input[name="email"]');
  const status = document.querySelector("#verification-status");
  const remembered = sessionStorage.getItem("pulso-verification-email");
  if (remembered && emailInput && !emailInput.value) emailInput.value = remembered;

  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || "";
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    if (status) status.textContent = "Enviando...";
    try {
      const response = await fetch("/api/v1/auth/resend-verification/", {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRFToken": csrf() },
        body: JSON.stringify({ email: emailInput?.value || "" }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error("Não foi possível solicitar outro e-mail agora.");
      if (status) status.textContent = data.detail || "Se a conta estiver pendente, uma nova confirmação será enviada.";
    } catch (error) {
      if (status) status.textContent = error.message;
    } finally {
      if (button) button.disabled = false;
    }
  });
})();
