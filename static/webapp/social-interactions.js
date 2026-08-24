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

  const profileUrl = username => `/perfil/${encodeURIComponent(username)}/`;

  function avatarMarkup(user, className = "") {
    const label = user.display_name || user.username || "Criador";
    const classes = ["social-avatar", className].filter(Boolean).join(" ");
    if (user.avatar_url) {
      return `<span class="${classes}" aria-hidden="true"><img src="${escapeHtml(user.avatar_url)}" alt="" loading="lazy"></span>`;
    }
    return `<span class="${classes}" aria-hidden="true">${escapeHtml(initials(label))}</span>`;
  }

  async function getJson(url) {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data.detail || data.error?.message || "Não foi possível carregar esta interação.";
      throw new Error(message);
    }
    return data;
  }

  function ensureLikesModal() {
    let dialog = document.querySelector("#likes-modal");
    if (dialog) return dialog;

    dialog = document.createElement("dialog");
    dialog.className = "modal likes-modal";
    dialog.id = "likes-modal";
    dialog.innerHTML = `
      <div class="modal-card likes-card">
        <header class="modal-header likes-header">
          <div>
            <span class="eyebrow">Interações</span>
            <h2 id="likes-title">Quem curtiu</h2>
          </div>
          <button type="button" class="icon-button" data-social-action="close-likes" aria-label="Fechar lista de curtidas">×</button>
        </header>
        <div class="likes-list" id="likes-list" role="list" aria-live="polite"></div>
        <footer class="likes-pagination" id="likes-pagination" hidden>
          <button type="button" data-social-page="previous">← Anterior</button>
          <span id="likes-page-label"></span>
          <button type="button" data-social-page="next">Próxima →</button>
        </footer>
      </div>`;
    document.body.append(dialog);
    dialog.addEventListener("click", event => {
      if (event.target === dialog) dialog.close();
    });
    return dialog;
  }

  const likesState = { postId: null, page: 1, next: null, previous: null, count: 0 };

  function renderLikesLoading() {
    document.querySelector("#likes-list").innerHTML = '<div class="likes-loading"><i></i><span>Buscando quem curtiu...</span></div>';
    document.querySelector("#likes-pagination").hidden = true;
  }

  function renderLikesPeople(data) {
    const list = document.querySelector("#likes-list");
    const people = data.results || [];
    likesState.next = data.next || null;
    likesState.previous = data.previous || null;
    likesState.count = Number(data.count || people.length || 0);

    document.querySelector("#likes-title").textContent = likesState.count === 1 ? "1 pessoa curtiu" : `${likesState.count} pessoas curtiram`;

    if (!people.length) {
      list.innerHTML = '<div class="likes-empty"><span>♡</span><strong>Nenhuma curtida visível.</strong><small>As interações aparecem aqui quando alguém curte a publicação.</small></div>';
    } else {
      list.innerHTML = people.map(user => {
        const username = escapeHtml(user.username);
        const url = profileUrl(user.username);
        return `<a class="likes-person" href="${url}" role="listitem" aria-label="Abrir perfil de ${escapeHtml(user.display_name || user.username)}">
          ${avatarMarkup(user, "likes-person-avatar")}
          <span class="likes-person-copy">
            <strong>${escapeHtml(user.display_name || user.username)}</strong>
            <small>@${username}${user.specialty ? ` · ${escapeHtml(user.specialty)}` : ""}</small>
          </span>
          <span class="likes-person-arrow" aria-hidden="true">↗</span>
        </a>`;
      }).join("");
    }

    const pagination = document.querySelector("#likes-pagination");
    const previous = pagination.querySelector('[data-social-page="previous"]');
    const next = pagination.querySelector('[data-social-page="next"]');
    previous.disabled = !likesState.previous;
    next.disabled = !likesState.next;
    document.querySelector("#likes-page-label").textContent = `Página ${likesState.page}`;
    pagination.hidden = !likesState.previous && !likesState.next;
  }

  async function loadLikes(postId, page = 1) {
    const dialog = ensureLikesModal();
    likesState.postId = postId;
    likesState.page = page;
    renderLikesLoading();
    if (!dialog.open) dialog.showModal();

    try {
      const data = await getJson(`/api/v1/social/posts/${encodeURIComponent(postId)}/likes/?page=${page}&page_size=20`);
      renderLikesPeople(data);
    } catch (error) {
      document.querySelector("#likes-title").textContent = "Quem curtiu";
      document.querySelector("#likes-list").innerHTML = `<div class="likes-empty"><span>!</span><strong>Não foi possível carregar.</strong><small>${escapeHtml(error.message)}</small></div>`;
    }
  }

  function likeCountFor(card) {
    const value = card.querySelector('[data-post-action="like"] span')?.textContent || "0";
    const count = Number.parseInt(value, 10);
    return Number.isFinite(count) && count > 0 ? count : 0;
  }

  function syncLikesViewer(card) {
    const viewer = card.querySelector("[data-social-action='show-likes']");
    if (!viewer) return;
    const count = likeCountFor(card);
    const countNode = viewer.querySelector("[data-social-like-count]");
    if (countNode) countNode.textContent = String(count);
    const labelNode = viewer.querySelector("[data-social-like-label]");
    if (labelNode) labelNode.textContent = count === 1 ? "Ver quem curtiu" : "Ver quem curtiu";
    viewer.disabled = count === 0;
    viewer.setAttribute("aria-label", count === 0 ? "Nenhuma curtida nesta publicação" : `Ver as ${count} curtidas desta publicação`);
  }

  function addLikesViewer(card) {
    if (card.querySelector("[data-social-action='show-likes']")) {
      syncLikesViewer(card);
      return;
    }
    const actions = card.querySelector(".post-actions");
    if (!actions) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "post-likes-view";
    button.dataset.socialAction = "show-likes";
    button.dataset.postId = card.dataset.post;
    button.innerHTML = '<span data-social-like-count>0</span> <span data-social-like-label>Ver quem curtiu</span> <span aria-hidden="true">↗</span>';
    actions.insertAdjacentElement("afterend", button);
    syncLikesViewer(card);
  }

  function renderComment(comment) {
    const user = comment.author || {};
    const username = user.username || "";
    const url = profileUrl(username);
    return `<div class="social-comment" data-comment-id="${escapeHtml(comment.id)}">
      <a class="social-comment-avatar-link" href="${url}" aria-label="Abrir perfil de ${escapeHtml(user.display_name || username)}">
        ${avatarMarkup(user, "social-comment-avatar")}
      </a>
      <div class="social-comment-copy">
        <a class="social-comment-author" href="${url}">
          <strong>${escapeHtml(user.display_name || username)}</strong>
          <span>@${escapeHtml(username)}</span>
        </a>
        <p>${escapeHtml(comment.body || "")}</p>
      </div>
    </div>`;
  }

  async function refreshCommentPreview(card) {
    const preview = card.querySelector(".comment-preview");
    if (!preview || preview.dataset.socialLoading === "true") return;
    preview.dataset.socialLoading = "true";
    try {
      const comments = await getJson(`/api/v1/social/posts/${encodeURIComponent(card.dataset.post)}/comment-preview/`);
      if (comments.length) {
        preview.innerHTML = comments.map(renderComment).join("");
        preview.dataset.socialLoaded = "true";
      } else {
        preview.remove();
      }
    } catch (_) {
      // Mantém o fallback original da aplicação caso a melhoria visual falhe.
    } finally {
      if (preview.isConnected) preview.dataset.socialLoading = "false";
    }
  }

  const commentVisibilityObserver = "IntersectionObserver" in window
    ? new IntersectionObserver(entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const card = entry.target;
          commentVisibilityObserver.unobserve(card);
          refreshCommentPreview(card);
        }
      }, { rootMargin: "280px 0px" })
    : null;

  function watchCommentPreview(card) {
    const preview = card.querySelector(".comment-preview");
    if (!preview || card.dataset.socialCommentsObserved === "true") return;
    card.dataset.socialCommentsObserved = "true";
    if (commentVisibilityObserver) commentVisibilityObserver.observe(card);
    else refreshCommentPreview(card);
  }

  function enhanceCard(card) {
    if (!(card instanceof Element) || !card.matches("[data-post]")) return;
    addLikesViewer(card);
    watchCommentPreview(card);
    card.dataset.socialIdentityEnhanced = "true";
  }

  function enhanceWithin(root) {
    if (!(root instanceof Element)) return;
    if (root.matches("[data-post]")) enhanceCard(root);
    root.querySelectorAll?.("[data-post]").forEach(enhanceCard);
  }

  function refreshAfterInlineComment(node) {
    if (!(node instanceof Element) || !node.matches(".comment-preview > p")) return;
    const card = node.closest("[data-post]");
    if (!card) return;
    window.setTimeout(() => refreshCommentPreview(card), 80);
  }

  const mutationObserver = new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (!(node instanceof Element)) continue;
        enhanceWithin(node);
        refreshAfterInlineComment(node);
      }
      const card = record.target instanceof Element ? record.target.closest?.("[data-post]") : null;
      if (card) syncLikesViewer(card);
    }
  });

  mutationObserver.observe(pageContent, { childList: true, subtree: true, characterData: true });
  pageContent.querySelectorAll("[data-post]").forEach(enhanceCard);

  document.addEventListener("click", event => {
    const target = event.target.closest?.("[data-social-action]");
    if (!target) return;
    const action = target.dataset.socialAction;
    if (action === "show-likes") {
      event.preventDefault();
      if (!target.disabled) loadLikes(target.dataset.postId, 1);
    } else if (action === "close-likes") {
      ensureLikesModal().close();
    }
  });

  document.addEventListener("click", event => {
    const pageButton = event.target.closest?.("[data-social-page]");
    if (!pageButton || pageButton.disabled || !likesState.postId) return;
    const direction = pageButton.dataset.socialPage;
    const nextPage = direction === "next" ? likesState.page + 1 : Math.max(1, likesState.page - 1);
    loadLikes(likesState.postId, nextPage);
  });
})();
