(() => {
  "use strict";

  const body = document.body;
  const username = body.dataset.profile?.trim();
  if (!username) return;

  const csrf = () => document.cookie
    .split("; ")
    .find(row => row.startsWith("csrftoken="))
    ?.split("=")[1] || "";

  async function request(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) {
      headers["X-CSRFToken"] = csrf();
    }
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Não foi possível concluir esta ação.");
    return data;
  }

  function setPeerActions(actions, blocked) {
    actions.querySelectorAll('[data-action="message-user"], [data-action="support"], [data-follow]')
      .forEach(control => {
        control.hidden = blocked;
      });
  }

  function renderBlockButton(button, blocked) {
    button.dataset.blocked = String(blocked);
    button.textContent = blocked ? "Desbloquear" : "Bloquear";
    button.setAttribute(
      "aria-label",
      blocked ? `Desbloquear @${username}` : `Bloquear @${username}`,
    );
  }

  async function enhanceProfileActions(actions) {
    if (!actions || actions.dataset.privacyReady === "true") return;
    actions.dataset.privacyReady = "true";

    let profile;
    try {
      profile = await request(`/api/v1/auth/profiles/${encodeURIComponent(username)}/`);
    } catch (_) {
      return;
    }
    if (profile.is_own) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "outline-button profile-block-action";
    button.dataset.action = "privacy-block";
    renderBlockButton(button, Boolean(profile.is_blocked));
    setPeerActions(actions, Boolean(profile.is_blocked));
    actions.append(button);

    button.addEventListener("click", async () => {
      const currentlyBlocked = button.dataset.blocked === "true";
      if (!currentlyBlocked) {
        const confirmed = window.confirm(
          `Bloquear @${username}? Vocês deixarão de se seguir e não poderão trocar novas mensagens ou chamadas enquanto o bloqueio estiver ativo.`,
        );
        if (!confirmed) return;
      }

      button.disabled = true;
      const previousLabel = button.textContent;
      button.textContent = currentlyBlocked ? "Desbloqueando..." : "Bloqueando...";
      try {
        const result = await request(
          `/api/v1/auth/profiles/${encodeURIComponent(username)}/block/`,
          { method: "POST" },
        );
        renderBlockButton(button, Boolean(result.blocked));
        setPeerActions(actions, Boolean(result.blocked));
      } catch (error) {
        button.textContent = previousLabel;
        window.alert(error.message);
      } finally {
        button.disabled = false;
      }
    });
  }

  function scan() {
    const actions = document.querySelector(".profile-actions");
    if (actions) enhanceProfileActions(actions);
  }

  scan();
  const observer = new MutationObserver(scan);
  observer.observe(document.body, { childList: true, subtree: true });
})();
