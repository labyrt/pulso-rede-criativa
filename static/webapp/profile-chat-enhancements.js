(() => {
  "use strict";

  const shell = document.querySelector("#app-shell");
  const pageContent = document.querySelector("#page-content");
  if (!shell || !pageContent) return;

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[character]));

  const initials = (name = "P") => name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part[0] || "")
    .join("")
    .toUpperCase() || "P";

  const csrf = () => decodeURIComponent(
    document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || ""
  );

  async function requestJson(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) headers["X-CSRFToken"] = csrf();
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const details = data.error?.details || data;
      const firstMessage = value => {
        if (typeof value === "string") return value;
        if (Array.isArray(value)) return value.map(firstMessage).find(Boolean);
        if (value && typeof value === "object") return Object.values(value).map(firstMessage).find(Boolean);
        return "";
      };
      throw new Error(firstMessage(details) || "Não foi possível concluir esta ação.");
    }
    return data;
  }

  function avatarMarkup(user, className = "") {
    const label = user.display_name || user.username || "Perfil";
    const classes = ["enhancement-avatar", className].filter(Boolean).join(" ");
    if (user.avatar_url) {
      return `<span class="${classes}" aria-hidden="true"><img src="${escapeHtml(user.avatar_url)}" alt="" loading="lazy"></span>`;
    }
    return `<span class="${classes}" aria-hidden="true">${escapeHtml(initials(label))}</span>`;
  }

  function profileUsernameFromDom() {
    return document.querySelector(".profile-handle")?.textContent?.trim().replace(/^@/, "") || document.body.dataset.profile || "";
  }

  function ensureConnectionsModal() {
    let dialog = document.querySelector("#connections-modal");
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.className = "modal connections-modal";
    dialog.id = "connections-modal";
    dialog.innerHTML = `
      <div class="modal-card connections-card">
        <header class="modal-header connections-header">
          <div><span class="eyebrow">Conexões</span><h2 id="connections-title">Pessoas</h2></div>
          <button type="button" class="icon-button" data-enhancement-action="close-connections" aria-label="Fechar lista">×</button>
        </header>
        <div class="connections-list" id="connections-list" role="list" aria-live="polite"></div>
        <footer class="connections-pagination" id="connections-pagination" hidden>
          <button type="button" data-connections-page="previous">← Anterior</button>
          <span id="connections-page-label"></span>
          <button type="button" data-connections-page="next">Próxima →</button>
        </footer>
      </div>`;
    document.body.append(dialog);
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });
    return dialog;
  }

  const connectionsState = { username: "", kind: "followers", page: 1, next: null, previous: null };

  function renderConnectionsLoading() {
    document.querySelector("#connections-list").innerHTML = '<div class="connections-loading"><i></i><span>Carregando conexões...</span></div>';
    document.querySelector("#connections-pagination").hidden = true;
  }

  function renderConnections(data) {
    const people = data.results || data || [];
    const list = document.querySelector("#connections-list");
    connectionsState.next = data.next || null;
    connectionsState.previous = data.previous || null;
    const label = connectionsState.kind === "followers" ? "Seguidores" : "Seguindo";
    document.querySelector("#connections-title").textContent = data.count === 1 ? `${label} · 1 pessoa` : `${label} · ${Number(data.count ?? people.length)} pessoas`;

    if (!people.length) {
      list.innerHTML = `<div class="connections-empty"><span>○</span><strong>Nenhuma pessoa visível aqui.</strong><small>As conexões deste perfil aparecerão nesta lista.</small></div>`;
    } else {
      list.innerHTML = people.map(user => `
        <a class="connections-person" href="/perfil/${encodeURIComponent(user.username)}/" role="listitem">
          ${avatarMarkup(user, "connections-person-avatar")}
          <span class="connections-person-copy">
            <strong>${escapeHtml(user.display_name || user.username)}</strong>
            <small>@${escapeHtml(user.username)}${user.specialty ? ` · ${escapeHtml(user.specialty)}` : ""}</small>
          </span>
          <span aria-hidden="true">↗</span>
        </a>`).join("");
    }

    const pagination = document.querySelector("#connections-pagination");
    pagination.querySelector('[data-connections-page="previous"]').disabled = !connectionsState.previous;
    pagination.querySelector('[data-connections-page="next"]').disabled = !connectionsState.next;
    document.querySelector("#connections-page-label").textContent = `Página ${connectionsState.page}`;
    pagination.hidden = !connectionsState.previous && !connectionsState.next;
  }

  async function loadConnections(username, kind, page = 1) {
    const dialog = ensureConnectionsModal();
    connectionsState.username = username;
    connectionsState.kind = kind;
    connectionsState.page = page;
    renderConnectionsLoading();
    if (!dialog.open) dialog.showModal();
    try {
      const data = await requestJson(`/api/v1/auth/profiles/${encodeURIComponent(username)}/${kind}/?page=${page}&page_size=20`);
      renderConnections(data);
    } catch (error) {
      document.querySelector("#connections-list").innerHTML = `<div class="connections-empty"><span>!</span><strong>Não foi possível carregar.</strong><small>${escapeHtml(error.message)}</small></div>`;
    }
  }

  function ensureCoverDialog() {
    let dialog = document.querySelector("#cover-framing-modal");
    if (dialog) return dialog;
    dialog = document.createElement("dialog");
    dialog.className = "modal cover-framing-modal";
    dialog.id = "cover-framing-modal";
    dialog.innerHTML = `
      <div class="modal-card cover-framing-card">
        <header class="modal-header">
          <div><span class="eyebrow">Imagem de capa</span><h2>Ajustar enquadramento</h2></div>
          <button type="button" class="icon-button" data-enhancement-action="close-cover-framing" aria-label="Fechar ajuste de capa">×</button>
        </header>
        <div class="cover-framing-body">
          <div class="cover-framing-preview" id="cover-framing-preview" role="img" aria-label="Prévia do enquadramento da capa"></div>
          <label class="cover-position-control">
            <span>Posição vertical</span>
            <input id="cover-position-range" type="range" min="0" max="100" step="1" value="50">
            <small><span>topo</span><span>centro</span><span>base</span></small>
          </label>
          <p class="cover-framing-help">Mova o controle até a parte importante da imagem ficar visível. A imagem original não é recortada novamente.</p>
          <p class="form-error cover-framing-error" id="cover-framing-error" role="alert"></p>
        </div>
        <footer class="modal-footer">
          <button type="button" class="button button--ghost" data-enhancement-action="close-cover-framing">Cancelar</button>
          <button type="button" class="button button--ink" data-enhancement-action="save-cover-framing">Salvar enquadramento</button>
        </footer>
      </div>`;
    document.body.append(dialog);
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });
    dialog.querySelector("#cover-position-range").addEventListener("input", event => {
      dialog.querySelector("#cover-framing-preview").style.backgroundPosition = `center ${event.target.value}%`;
    });
    return dialog;
  }

  let currentOwnProfile = null;

  async function openCoverFraming() {
    const dialog = ensureCoverDialog();
    const error = dialog.querySelector("#cover-framing-error");
    error.textContent = "";
    try {
      currentOwnProfile = await requestJson("/api/v1/auth/me/");
      if (!currentOwnProfile.cover_url) throw new Error("Adicione uma imagem de capa antes de ajustar o enquadramento.");
      const range = dialog.querySelector("#cover-position-range");
      range.value = String(currentOwnProfile.cover_position_y ?? 50);
      const preview = dialog.querySelector("#cover-framing-preview");
      preview.style.backgroundImage = `url("${String(currentOwnProfile.cover_url).replace(/"/g, "%22")}")`;
      preview.style.backgroundPosition = `center ${range.value}%`;
      if (!dialog.open) dialog.showModal();
    } catch (err) {
      error.textContent = err.message;
      if (!dialog.open) dialog.showModal();
    }
  }

  async function saveCoverFraming(button) {
    const dialog = ensureCoverDialog();
    const range = dialog.querySelector("#cover-position-range");
    const error = dialog.querySelector("#cover-framing-error");
    error.textContent = "";
    button.disabled = true;
    const original = button.textContent;
    button.textContent = "Salvando...";
    try {
      currentOwnProfile = await requestJson("/api/v1/auth/me/", {
        method: "PATCH",
        body: JSON.stringify({ cover_position_y: Number(range.value) }),
      });
      const cover = document.querySelector(".profile-cover");
      if (cover) cover.style.backgroundPosition = `center ${currentOwnProfile.cover_position_y}%`;
      dialog.close();
    } catch (err) {
      error.textContent = err.message;
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  async function enhanceProfile(hero) {
    if (!(hero instanceof Element) || hero.dataset.profileEnhancing === "true") return;
    hero.dataset.profileEnhancing = "true";
    const username = profileUsernameFromDom();
    if (!username) return;
    try {
      const profile = await requestJson(`/api/v1/auth/profiles/${encodeURIComponent(username)}/`);
      const cover = hero.querySelector(".profile-cover");
      if (cover && profile.cover_url) {
        cover.style.backgroundPosition = `center ${profile.cover_position_y ?? 50}%`;
        if (profile.is_own && !cover.querySelector('[data-enhancement-action="open-cover-framing"]')) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "cover-position-button";
          button.dataset.enhancementAction = "open-cover-framing";
          button.innerHTML = '<span aria-hidden="true">↕</span> Ajustar enquadramento';
          cover.append(button);
        }
      }

      const counts = hero.querySelectorAll(".profile-counts > span");
      [[counts[0], "following"], [counts[1], "followers"]].forEach(([node, kind]) => {
        if (!node) return;
        node.classList.add("connection-count");
        node.dataset.profileConnections = kind;
        node.dataset.username = profile.username;
        node.setAttribute("role", "button");
        node.setAttribute("tabindex", "0");
        node.setAttribute("aria-label", kind === "followers" ? "Ver seguidores" : "Ver perfis que esta pessoa segue");
      });
    } catch (_) {
      // O perfil principal continua funcional mesmo se esta camada progressiva falhar.
    } finally {
      hero.dataset.profileEnhancing = "false";
      hero.dataset.profileEnhanced = "true";
    }
  }

  let explicitConversation = false;

  function formatConversationTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const today = new Date();
    if (date.toDateString() === today.toDateString()) {
      return new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" }).format(date);
    }
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(date);
  }

  async function decorateConversationMetadata(layout) {
    if (layout.dataset.chatMetadataRequested === "true") return;
    layout.dataset.chatMetadataRequested = "true";
    try {
      const data = await requestJson("/api/v1/chat/conversations/?page_size=40");
      const conversations = data.results || data || [];
      const byId = new Map(conversations.map(item => [String(item.id), item]));
      layout.querySelectorAll(".conversation-item[data-conversation]").forEach(item => {
        const conversation = byId.get(item.dataset.conversation);
        if (!conversation) return;
        const copy = item.querySelector(":scope > div");
        if (copy && !copy.querySelector(".conversation-meta")) {
          const meta = document.createElement("span");
          meta.className = "conversation-meta";
          const when = formatConversationTime(conversation.last_message?.created_at || conversation.updated_at);
          meta.innerHTML = `${when ? `<time>${escapeHtml(when)}</time>` : ""}${conversation.unread_count ? `<b aria-label="${conversation.unread_count} mensagens não lidas">${conversation.unread_count > 99 ? "99+" : conversation.unread_count}</b>` : ""}`;
          copy.append(meta);
        }
      });
    } catch (_) {
      // Metadados são complementares e não bloqueiam o chat.
    }
  }

  function addChatBackButton(panel) {
    const header = panel.querySelector(".chat-header");
    if (!header || header.querySelector(".chat-back")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "chat-back";
    button.dataset.enhancementAction = "chat-back";
    button.setAttribute("aria-label", "Voltar para a lista de conversas");
    button.textContent = "←";
    header.prepend(button);
  }

  function addChatLoader(panel) {
    const stream = panel.querySelector("#message-stream");
    if (!stream || stream.children.length) return;
    stream.innerHTML = '<div class="chat-loading" aria-live="polite"><i></i><span>Carregando mensagens...</span></div>';
  }

  function enhanceConversationItems(layout) {
    layout.querySelectorAll(".conversation-item[data-conversation]").forEach(item => {
      if (item.dataset.keyboardReady === "true") return;
      item.dataset.keyboardReady = "true";
      item.setAttribute("role", "button");
      item.setAttribute("tabindex", "0");
      item.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          explicitConversation = true;
          item.click();
        }
      });
    });
  }

  function enhanceMessagesLayout(layout) {
    if (!(layout instanceof Element)) return;
    const list = layout.querySelector(".conversation-list");
    if (list) {
      const header = list.querySelector("header");
      if (header && !header.querySelector(".conversation-search")) {
        const label = document.createElement("label");
        label.className = "conversation-search";
        label.innerHTML = '<span aria-hidden="true">⌕</span><input type="search" placeholder="Buscar conversa" aria-label="Buscar conversa">';
        header.append(label);
        label.querySelector("input").addEventListener("input", event => {
          const query = event.target.value.trim().toLocaleLowerCase("pt-BR");
          layout.querySelectorAll(".conversation-item").forEach(item => {
            item.hidden = Boolean(query) && !item.textContent.toLocaleLowerCase("pt-BR").includes(query);
          });
        });
      }
    }

    enhanceConversationItems(layout);
    const panel = layout.querySelector("#chat-panel");
    if (panel) {
      addChatBackButton(panel);
      addChatLoader(panel);
    }

    const idle = window.requestIdleCallback || (callback => window.setTimeout(callback, 120));
    idle(() => decorateConversationMetadata(layout));

    if (window.matchMedia("(max-width: 640px)").matches) {
      [80, 240, 600].forEach(delay => window.setTimeout(() => {
        if (explicitConversation) return;
        layout.querySelector(".conversation-list")?.classList.remove("hidden-mobile");
        layout.querySelector("#chat-panel")?.classList.remove("open-mobile");
      }, delay));
    }
  }

  function enhanceWithin(root) {
    if (!(root instanceof Element)) return;
    if (root.matches(".profile-hero")) enhanceProfile(root);
    root.querySelectorAll?.(".profile-hero").forEach(enhanceProfile);
    if (root.matches(".messages-layout")) enhanceMessagesLayout(root);
    root.querySelectorAll?.(".messages-layout").forEach(enhanceMessagesLayout);
    const layout = root.closest?.(".messages-layout");
    if (layout) {
      enhanceConversationItems(layout);
      addChatBackButton(layout.querySelector("#chat-panel"));
      addChatLoader(layout.querySelector("#chat-panel"));
    }
  }

  const observer = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node instanceof Element) enhanceWithin(node);
      }
    }
  });
  observer.observe(pageContent, { childList: true, subtree: true });
  enhanceWithin(pageContent);

  document.addEventListener("click", event => {
    if (event.target.closest?.(".conversation-item[data-conversation]")) explicitConversation = true;

    const connection = event.target.closest?.("[data-profile-connections]");
    if (connection) {
      event.preventDefault();
      loadConnections(connection.dataset.username, connection.dataset.profileConnections, 1);
      return;
    }

    const actionTarget = event.target.closest?.("[data-enhancement-action]");
    if (!actionTarget) return;
    const action = actionTarget.dataset.enhancementAction;
    if (action === "close-connections") ensureConnectionsModal().close();
    else if (action === "open-cover-framing") openCoverFraming();
    else if (action === "close-cover-framing") ensureCoverDialog().close();
    else if (action === "save-cover-framing") saveCoverFraming(actionTarget);
    else if (action === "chat-back") {
      const layout = actionTarget.closest(".messages-layout");
      layout?.querySelector(".conversation-list")?.classList.remove("hidden-mobile");
      layout?.querySelector("#chat-panel")?.classList.remove("open-mobile");
    }
  }, true);

  document.addEventListener("keydown", event => {
    const connection = event.target.closest?.("[data-profile-connections]");
    if (!connection || !["Enter", " "].includes(event.key)) return;
    event.preventDefault();
    loadConnections(connection.dataset.username, connection.dataset.profileConnections, 1);
  });

  document.addEventListener("click", event => {
    const pageButton = event.target.closest?.("[data-connections-page]");
    if (!pageButton || pageButton.disabled || !connectionsState.username) return;
    const nextPage = pageButton.dataset.connectionsPage === "next"
      ? connectionsState.page + 1
      : Math.max(1, connectionsState.page - 1);
    loadConnections(connectionsState.username, connectionsState.kind, nextPage);
  });
})();
