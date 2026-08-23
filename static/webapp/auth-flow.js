(() => {
  "use strict";

  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || "";
  const firstMessage = value => {
    if (typeof value === "string") return value;
    if (Array.isArray(value)) return value.map(firstMessage).find(Boolean);
    if (value && typeof value === "object") return Object.values(value).map(firstMessage).find(Boolean);
    return "";
  };

  async function submitAuth(form, endpoint) {
    const button = form.querySelector('button[type="submit"]');
    const errorBox = document.querySelector("#form-error");
    const payload = Object.fromEntries(
      [...new FormData(form).entries()].filter(([, value]) => String(value).trim() !== "")
    );
    if (errorBox) errorBox.textContent = "";
    if (button) {
      button.disabled = true;
      button.textContent = endpoint.includes("register") ? "Criando seu espaço..." : "Entrando no pulso...";
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": csrf(),
        },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (data.requires_email_verification) {
          window.location.assign("/accounts/confirm-email/");
          return;
        }
        throw new Error(firstMessage(data.error?.details || data) || "Não foi possível concluir.");
      }
      if (data.requires_email_verification) {
        if (payload.email) sessionStorage.setItem("pulso-verification-email", payload.email);
        window.location.assign("/accounts/confirm-email/");
        return;
      }
      window.location.assign("/app/");
    } catch (error) {
      if (errorBox) errorBox.textContent = error.message;
      if (button) {
        button.disabled = false;
        button.innerHTML = endpoint.includes("register") ? "Criar meu espaço <span>↗</span>" : "Entrar <span>↗</span>";
      }
    }
  }

  for (const [selector, endpoint] of [
    ["#login-form", "/api/v1/auth/login/"],
    ["#register-form", "/api/v1/auth/register/"],
  ]) {
    const form = document.querySelector(selector);
    if (!form) continue;
    form.addEventListener(
      "submit",
      event => {
        event.preventDefault();
        event.stopImmediatePropagation();
        submitAuth(form, endpoint);
      },
      true
    );
  }
})();
