(() => {
  "use strict";

  const body = document.body;
  const section = body.dataset.section;
  const profileUsername = body.dataset.profile;
  const state = { me: null, conversations: [], socket: null, peer: null, localStream: null, activeConversation: null };
  const previewUrls = new Map();
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
  const initials = (name = "P") => name.split(/\s+/).slice(0, 2).map(p => p[0]).join("").toUpperCase();
  const avatar = user => `<span class="avatar">${user.avatar_url ? `<img src="${escapeHtml(user.avatar_url)}" alt="">` : initials(user.display_name || user.username)}</span>`;
  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || "";
  const formatDate = date => new Intl.DateTimeFormat("pt-BR", { day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit" }).format(new Date(date));
  const timeAgo = date => {
    const seconds = Math.floor((Date.now() - new Date(date)) / 1000);
    if (seconds < 60) return "agora";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h`;
    return `${Math.floor(seconds / 86400)} d`;
  };

  const savedTheme = localStorage.getItem("pulso-theme");
  const initialTheme = savedTheme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = initialTheme;

  async function api(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) headers["X-CSRFToken"] = csrf();
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const details = data.error?.details || data;
      const firstMessage = value => {
        if (typeof value === "string") return value;
        if (Array.isArray(value)) return value.map(firstMessage).find(Boolean);
        if (value && typeof value === "object") return Object.values(value).map(firstMessage).find(Boolean);
        return "";
      };
      const message = firstMessage(details) || "Não foi possível concluir.";
      throw new Error(message);
    }
    return data;
  }

  function toast(message, type = "") {
    const item = document.createElement("div");
    item.className = `toast ${type}`;
    item.textContent = message;
    $("#toast-stack")?.append(item);
    setTimeout(() => item.remove(), 3400);
  }

  function serialize(form) {
    return Object.fromEntries([...new FormData(form).entries()].filter(([, value]) => String(value).trim() !== ""));
  }


  function multipart(form) {
    const data = new FormData(form);
    for (const [key, value] of [...data.entries()]) {
      if ((typeof value === "string" && !value.trim()) || (value instanceof File && !value.size)) data.delete(key);
    }
    return data;
  }

  function renderError(error) {
    const box = $("#form-error");
    if (box) box.textContent = error.message;
    else toast(error.message, "error");
  }

  function showFormError(form, error) {
    const box = $(".modal-error", form);
    if (box) {
      box.textContent = error?.message || String(error);
      box.scrollIntoView({ block: "nearest", behavior: "smooth" });
    } else toast(error?.message || String(error), "error");
  }

  function clearFormError(form) {
    const box = $(".modal-error", form);
    if (box) box.textContent = "";
  }

  function setSubmitting(form, active, loadingLabel) {
    const button = $('button[type="submit"]', form);
    if (!button) return;
    button.disabled = active;
    button.textContent = active ? loadingLabel : button.dataset.submitLabel;
  }

  function closeModal(id) {
    const modal = $(`#${id}`);
    if (modal?.open) modal.close();
  }

  function validateImageFile(file) {
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) throw new Error("Selecione uma imagem JPG, PNG ou WebP.");
    if (file.size > 8 * 1024 * 1024) throw new Error("A imagem deve ter no máximo 8 MB.");
  }

  function renderImagePreview(file, container, options = {}) {
    validateImageFile(file);
    const previousUrl = previewUrls.get(container);
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    const url = URL.createObjectURL(file);
    previewUrls.set(container, url);
    container.innerHTML = `<img src="${url}" alt="${escapeHtml(options.alt || "Prévia da imagem selecionada")}">${options.removable ? '<button type="button" data-action="remove-post-image">Remover</button>' : ""}`;
    container.hidden = false;
  }

  async function initAuth() {
    const loginForm = $("#login-form");
    const registerForm = $("#register-form");
    for (const form of [loginForm, registerForm].filter(Boolean)) {
      form.addEventListener("submit", async event => {
        event.preventDefault();
        const button = $("button[type=submit]", form);
        button.disabled = true;
        button.textContent = "Entrando no pulso...";
        try {
          await api(form === loginForm ? "/api/v1/auth/login/" : "/api/v1/auth/register/", { method: "POST", body: JSON.stringify(serialize(form)) });
          window.location.assign("/app/");
        } catch (error) {
          renderError(error);
          button.disabled = false;
          button.innerHTML = form === loginForm ? "Entrar <span>↗</span>" : "Criar meu espaço <span>↗</span>";
        }
      });
    }
  }

  function renderAccount() {
    const chip = $("#account-chip");
    if (!chip || !state.me) return;
    chip.classList.remove("skeleton");
    chip.innerHTML = `${avatar(state.me)}<div><strong>${escapeHtml(state.me.display_name)}</strong><small>@${escapeHtml(state.me.username)}</small></div><span class="account-more">•••</span>`;
    $$('[data-action="my-profile"]').forEach(link => link.href = `/perfil/${state.me.username}/`);
  }

  function toggleMenu(id, trigger) {
    const menu = $(`#${id}`);
    if (!menu) return;
    const shouldOpen = menu.hidden;
    menu.hidden = !shouldOpen;
    trigger?.setAttribute("aria-expanded", String(shouldOpen));
  }

  function closeMenus() {
    for (const id of ["account-menu", "mobile-account-menu"]) {
      const menu = $(`#${id}`);
      if (menu) menu.hidden = true;
    }
    $('[data-action="toggle-account-menu"]')?.setAttribute("aria-expanded", "false");
    $('[data-action="toggle-mobile-menu"]')?.setAttribute("aria-expanded", "false");
  }

  function toggleTheme() {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("pulso-theme", theme);
    toast(theme === "dark" ? "Modo escuro ativado." : "Modo claro ativado.", "success");
  }

  async function logoutUser() {
    try {
      await api("/api/v1/auth/logout/", { method: "POST" });
      location.assign("/");
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function activateNav() {
    $$(`[data-nav="${section}"]`).forEach(link => link.classList.add("active"));
  }

  async function loadSuggestions() {
    const box = $("#creator-suggestions");
    if (!box) return;
    try {
      const data = await api("/api/v1/auth/creators/?page_size=4");
      const creators = data.results || data;
      box.innerHTML = creators.slice(0, 4).map(user => `
        <div class="suggestion">
          <a href="/perfil/${escapeHtml(user.username)}/">${avatar(user)}</a>
          <div><a href="/perfil/${escapeHtml(user.username)}/"><strong>${escapeHtml(user.display_name)}</strong></a><small>${escapeHtml(user.specialty)}</small></div>
          <button class="mini-follow ${user.is_following ? "following" : ""}" data-follow="${escapeHtml(user.username)}">${user.is_following ? "seguindo" : "seguir"}</button>
        </div>`).join("");
    } catch (_) { box.innerHTML = "<small>Gente nova aparece por aqui.</small>"; }
  }

  async function toggleFollow(username, button) {
    try {
      const result = await api(`/api/v1/auth/profiles/${encodeURIComponent(username)}/follow/`, { method: "POST" });
      if (button) {
        button.classList.toggle("following", result.following);
        button.textContent = result.following ? "seguindo" : "seguir";
      }
      toast(result.following ? `Você agora segue @${username}.` : `Você deixou de seguir @${username}.`, "success");
      if (section === "profile") loadProfile(username);
    } catch (error) { toast(error.message, "error"); }
  }

  function linkText(text) {
    return escapeHtml(text)
      .replace(/(https:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/(^|\s)#([\p{L}\p{N}_-]+)/gu, '$1<a href="/explorar/?q=$2">#$2</a>');
  }

  function postCard(post) {
    const comments = (post.latest_comments || []).map(comment => `<p><strong>@${escapeHtml(comment.author.username)}</strong>${escapeHtml(comment.body)}</p>`).join("");
    return `<article class="post-card" data-post="${post.id}">
      <a href="/perfil/${escapeHtml(post.author.username)}/">${avatar(post.author)}</a>
      <div>
        <header class="post-head"><a href="/perfil/${escapeHtml(post.author.username)}/"><strong>${escapeHtml(post.author.display_name)}</strong></a><small>@${escapeHtml(post.author.username)}</small><time title="${escapeHtml(formatDate(post.created_at))}">${timeAgo(post.created_at)}</time></header>
        <div class="post-body">${linkText(post.body)}</div>
        ${post.image_url ? `<img class="post-media" src="${escapeHtml(post.image_url)}" alt="Trabalho publicado por ${escapeHtml(post.author.display_name)}" loading="lazy">` : ""}
        ${post.video_url ? `<video class="post-media" src="${escapeHtml(post.video_url)}" controls preload="metadata"></video>` : ""}
        ${post.portfolio_url ? `<a class="portfolio-link" href="${escapeHtml(post.portfolio_url)}" target="_blank" rel="noopener noreferrer"><span>Ver projeto completo</span><b>↗</b></a>` : ""}
        ${post.tag_list?.length ? `<div class="tag-row">${post.tag_list.map(tag => `<span>#${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        <div class="post-actions">
          <button data-post-action="like" class="${post.is_liked ? "active-like" : ""}" aria-label="Curtir">${post.is_liked ? "♥" : "♡"} <span>${post.likes_count}</span></button>
          <button data-post-action="comment" aria-label="Comentar">◌ <span>${post.comments_count}</span></button>
          <button data-post-action="repost" class="${post.is_reposted ? "active-repost" : ""}" aria-label="Repostar">↻ <span>${post.reposts_count}</span></button>
          <button data-post-action="bookmark" class="${post.is_bookmarked ? "active-bookmark" : ""}" aria-label="Guardar">${post.is_bookmarked ? "◆" : "◇"}</button>
          <button data-post-action="share" aria-label="Compartilhar">↗</button>
        </div>
        <form class="inline-comment" data-comment-form hidden>
          ${avatar(state.me)}
          <label><span class="sr-only">Escreva um comentário</span><textarea name="body" maxlength="500" rows="1" placeholder="Deixe uma ideia, pergunta ou incentivo..." required></textarea></label>
          <div class="inline-comment-actions"><button type="button" data-action="cancel-comment">Cancelar</button><button type="submit">Comentar ↗</button></div>
          <p class="inline-comment-error" role="alert"></p>
        </form>
        ${post.pix_enabled ? `<button class="post-support" data-action="support" data-username="${escapeHtml(post.author.username)}" data-post-id="${post.id}"><span>♡</span> Apoiar este trabalho via Pix</button>` : ""}
        ${comments ? `<div class="comment-preview">${comments}</div>` : ""}
      </div>
    </article>`;
  }

  function feedHeader(title, subtitle) {
    return `<header class="page-header"><h1>${title}</h1><p>${subtitle}</p></header>`;
  }

  function emptyState(icon, title, copy, action = "") {
    return `<div class="empty-state"><div><div class="empty-orb">${icon}</div><h2>${title}</h2><p>${copy}</p>${action}</div></div>`;
  }

  async function loadPosts(url, title, subtitle, options = {}) {
    const content = $("#page-content");
    content.innerHTML = `${feedHeader(title, subtitle)}${options.composer ? `<div class="composer-inline" data-action="open-composer">${avatar(state.me)}<p>Compartilhe o que está tomando forma...</p><span>＋</span></div>` : ""}<div id="post-list"><div class="page-loader"><i></i></div></div>`;
    try {
      const data = await api(url);
      const posts = data.results || data;
      $("#post-list").innerHTML = posts.length ? posts.map(postCard).join("") : emptyState("✦", options.emptyTitle || "O silêncio também faz parte.", options.emptyCopy || "Quando houver novas criações, elas aparecem aqui.", options.emptyAction || "");
    } catch (error) { $("#post-list").innerHTML = emptyState("!", "Algo saiu do ritmo.", error.message); }
  }

  async function loadFeed() {
    await loadPosts("/api/v1/social/feed/", "Meu pulso", "Trabalhos e ideias das pessoas que você segue.", { composer: true, emptyTitle: "Seu pulso começa pelas conexões.", emptyCopy: "Siga criadores em Descobrir e o trabalho deles aparecerá aqui.", emptyAction: '<a class="button button--ink" href="/explorar/">Descobrir criadores</a>' });
  }

  async function loadExplore() {
    const query = new URLSearchParams(location.search).get("q") || "";
    const url = query ? `/api/v1/social/posts/?search=${encodeURIComponent(query)}` : "/api/v1/social/explore/";
    await loadPosts(url, query ? `Resultados para “${escapeHtml(query)}”` : "Descobrir", "Expressões, processos e pessoas fora da sua bolha criativa.");
  }

  async function loadBookmarks() {
    await loadPosts("/api/v1/social/bookmarks/", "Guardados", "Referências e ideias para voltar quando precisar.", { emptyTitle:"Nada guardado ainda.", emptyCopy:"Use o losango nas publicações para criar seu arquivo de referências." });
  }

  async function handlePostAction(button) {
    const card = button.closest("[data-post]");
    const postId = card.dataset.post;
    const action = button.dataset.postAction;
    try {
      if (action === "share") {
        const url = `${location.origin}/app/?post=${postId}`;
        if (navigator.share) await navigator.share({ title:"PULSO", url });
        else { await navigator.clipboard.writeText(url); toast("Link copiado.", "success"); }
        return;
      }
      if (action === "comment") {
        const form = $("[data-comment-form]", card);
        form.hidden = !form.hidden;
        if (!form.hidden) $("textarea", form).focus();
        return;
      }
      const result = await api(`/api/v1/social/posts/${postId}/${action}/`, { method:"POST" });
      button.classList.toggle(action === "like" ? "active-like" : action === "bookmark" ? "active-bookmark" : "active-repost", result[`${action}d`] ?? result.liked ?? result.bookmarked ?? result.reposted);
      const count = $("span", button); if (count && result.count !== undefined) count.textContent = result.count;
    } catch (error) { toast(error.message, "error"); }
  }

  async function submitComment(form) {
    const card = form.closest("[data-post]");
    const textarea = $("textarea", form);
    const errorBox = $(".inline-comment-error", form);
    const submit = $('button[type="submit"]', form);
    const body = textarea.value.trim();
    if (!body) return;
    errorBox.textContent = "";
    submit.disabled = true;
    submit.textContent = "Publicando...";
    try {
      const comment = await api(`/api/v1/social/posts/${card.dataset.post}/comments/`, { method:"POST", body:JSON.stringify({ body }) });
      let preview = $(".comment-preview", card);
      if (!preview) {
        preview = document.createElement("div");
        preview.className = "comment-preview";
        card.children[1]?.append(preview);
      }
      preview.insertAdjacentHTML("afterbegin", `<p><strong>@${escapeHtml(comment.author.username)}</strong>${escapeHtml(comment.content || comment.body || body)}</p>`);
      const count = $('[data-post-action="comment"] span', card);
      if (count) count.textContent = String(Number(count.textContent || 0) + 1);
      form.reset();
      form.hidden = true;
      toast("Comentário publicado.", "success");
    } catch (error) {
      errorBox.textContent = error.message;
    } finally {
      submit.disabled = false;
      submit.textContent = "Comentar ↗";
    }
  }

  async function loadProfile(username) {
    const content = $("#page-content");
    content.innerHTML = '<div class="page-loader"><i></i></div>';
    try {
      const profile = await api(`/api/v1/auth/profiles/${encodeURIComponent(username)}/`);
      const posts = await api(`/api/v1/social/posts/?author__username=${encodeURIComponent(username)}&page_size=30`);
      const networks = [["instagram_url","Instagram"],["github_url","GitHub"],["linkedin_url","LinkedIn"],["behance_url","Behance"]]
        .filter(([field]) => profile[field])
        .map(([field,label]) => `<a class="social-link" href="${escapeHtml(profile[field])}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`).join("");
      content.innerHTML = `<section class="profile-hero">
        <div class="profile-cover" ${profile.cover_url ? `style="background-image:url('${escapeHtml(profile.cover_url)}')"` : ""}>${profile.is_own ? '<button class="media-edit media-edit--cover" data-action="edit-cover" aria-label="Alterar apenas a imagem de capa">✎ <span>Alterar capa</span></button>' : ""}</div>
        <div class="profile-main">
          <div class="profile-avatar">${profile.avatar_url ? `<img src="${escapeHtml(profile.avatar_url)}" alt="">` : initials(profile.display_name)}${profile.is_own ? '<button class="media-edit media-edit--avatar" data-action="edit-avatar" aria-label="Alterar apenas a foto de perfil">✎</button>' : ""}</div>
          <div class="profile-actions">
            ${profile.is_own ? '<button class="outline-button" data-action="edit-profile">Editar perfil</button>' : `<button class="outline-button" data-action="message-user" data-username="${escapeHtml(profile.username)}">Mensagem</button>${profile.pix_enabled ? `<button class="outline-button outline-button--pink" data-action="support" data-username="${escapeHtml(profile.username)}">Apoiar</button>` : ""}<button class="button button--ink" data-follow="${escapeHtml(profile.username)}">${profile.is_following ? "Seguindo" : "Seguir"}</button>`}
          </div>
          <h1>${escapeHtml(profile.display_name)}</h1><span class="profile-handle">@${escapeHtml(profile.username)}</span>
          ${profile.is_available_for_work ? '<p><span class="available-pill">disponível para projetos</span></p>' : ""}
          <p class="profile-bio">${escapeHtml(profile.bio || "Este espaço ainda está ganhando forma.")}</p>
          <div class="profile-meta">${profile.specialty_label ? `<span>✦ ${escapeHtml(profile.specialty_label)}</span>` : ""}${profile.location ? `<span>⌖ ${escapeHtml(profile.location)}</span>` : ""}${profile.website ? `<a href="${escapeHtml(profile.website)}" target="_blank" rel="noopener noreferrer">Portfólio ↗</a>` : ""}</div>
          ${networks ? `<div class="social-links">${networks}</div>` : ""}
          <div class="profile-counts"><span><strong>${profile.following_count}</strong> seguindo</span><span><strong>${profile.followers_count}</strong> seguidores</span><span><strong>${profile.posts_count}</strong> publicações</span></div>
        </div></section><div id="post-list">${(posts.results || posts).length ? (posts.results || posts).map(postCard).join("") : emptyState("◌", "Espaço aberto.", "A primeira publicação desta pessoa ainda vai chegar.")}</div>`;
    } catch (error) { content.innerHTML = emptyState("!", "Perfil não encontrado.", error.message); }
  }

  async function loadCreators() {
    const content = $("#page-content");
    content.innerHTML = `${feedHeader("Descobrir pessoas", "Conheça repertórios e abra novas possibilidades.")}<div id="creator-grid" class="creator-grid"><div class="page-loader"><i></i></div></div>`;
    try {
      const data = await api("/api/v1/auth/creators/?page_size=30");
      const creators = data.results || data;
      $("#creator-grid").innerHTML = creators.map(user => `<article class="creator-card">${avatar(user)}<a href="/perfil/${escapeHtml(user.username)}/"><h3>${escapeHtml(user.display_name)}</h3></a><span class="specialty">${escapeHtml(user.specialty)}</span><p>@${escapeHtml(user.username)}</p><footer><a href="/perfil/${escapeHtml(user.username)}/">Ver espaço ↗</a><button class="mini-follow ${user.is_following ? "following" : ""}" data-follow="${escapeHtml(user.username)}">${user.is_following ? "seguindo" : "seguir"}</button></footer></article>`).join("");
    } catch (error) { $("#creator-grid").innerHTML = emptyState("!", "Não foi possível buscar pessoas.", error.message); }
  }

  async function loadNotifications() {
    const content = $("#page-content");
    content.innerHTML = `${feedHeader("Atividade", "O que reverberou no seu espaço.")}<div id="notifications"><div class="page-loader"><i></i></div></div>`;
    try {
      const data = await api("/api/v1/social/notifications/?page_size=40");
      const items = data.results || data;
      const labels = { follow:"começou a seguir você", like:"curtiu sua publicação", comment:"comentou na sua publicação", repost:"compartilhou sua publicação", message:"enviou uma mensagem" };
      $("#notifications").innerHTML = items.length ? items.map(item => `<div class="notification-item ${item.is_read ? "" : "unread"}">${avatar(item.actor)}<p><strong>${escapeHtml(item.actor.display_name)}</strong> ${labels[item.kind] || "interagiu com você"}${item.post_excerpt ? `<br><small>“${escapeHtml(item.post_excerpt)}”</small>` : ""}</p><time>${timeAgo(item.created_at)}</time></div>`).join("") : emptyState("♢", "Tudo quieto por aqui.", "Novas conexões e interações aparecerão neste espaço.");
      await api("/api/v1/social/notifications/read_all/", { method:"POST" });
    } catch (error) { $("#notifications").innerHTML = emptyState("!", "Não foi possível carregar.", error.message); }
  }

  function openComposer() {
    const form = $("#post-form");
    clearFormError(form);
    $("#composer-modal")?.showModal();
  }

  async function submitPost(event) {
    event.preventDefault();
    const form = event.currentTarget;
    clearFormError(form);
    const file = form.elements.image_upload.files[0];
    if (file) {
      try { validateImageFile(file); }
      catch (error) { showFormError(form, error); return; }
    }
    setSubmitting(form, true, file ? "Enviando imagem..." : "Publicando...");
    try {
      const data = multipart(form);
      data.set("accepts_support", String(form.elements.accepts_support.checked));
      await api("/api/v1/social/posts/", { method:"POST", body:data });
      form.reset(); $("#post-image-preview").hidden = true; $("#post-image-preview").innerHTML = ""; $("#composer-modal").close(); toast("Seu trabalho entrou no pulso.", "success"); reloadSection();
    } catch (error) { showFormError(form, error); }
    finally { setSubmitting(form, false); }
  }

  async function aiCaption() {
    const textarea = $("#post-body");
    const draft = textarea.value.trim();
    if (!draft) { toast("Escreva uma ideia inicial primeiro.", "error"); return; }
    const button = $('[data-action="ai-caption"]'); button.disabled = true; button.textContent = "✦ Lapidando sem apagar sua voz...";
    try {
      const category = $('#post-form select[name="category"]').value;
      const data = await api("/api/v1/ai/caption/", { method:"POST", body:JSON.stringify({ draft, category, tone:"autêntico e editorial" }) });
      textarea.value = data.suggestion; textarea.dispatchEvent(new Event("input")); toast(data.provider === "gemini" ? "Legenda lapidada com Gemini." : "Legenda lapidada pelo modo local.", "success");
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; button.innerHTML = "<span>✦</span> Lapidar com assistente"; }
  }

  function profileForm() {
    const p = state.me;
    return `<header class="modal-header"><div><span class="eyebrow">Seu espaço</span><h2>Edite apenas o que quiser.</h2></div><button type="button" class="icon-button" data-action="close-modal" data-modal="profile-modal" aria-label="Fechar editor de perfil">×</button></header><div class="modal-scroll"><div class="profile-fields">
      <label>Nome criativo<input name="display_name" value="${escapeHtml(p.display_name || "")}"></label><label>Usuário<input name="username" value="${escapeHtml(p.username)}"></label>
      <label class="wide">Bio<textarea name="bio" maxlength="220">${escapeHtml(p.bio || "")}</textarea></label>
      <label>Localização<input name="location" value="${escapeHtml(p.location || "")}"></label><label>Portfólio<input type="url" name="website" value="${escapeHtml(p.website || "")}"></label>
      <label>Expressão<select name="specialty">${[["photography","Fotografia"],["nail-art","Nail art"],["hair","Cabelo"],["painting","Pintura"],["digital-art","Arte digital"],["fashion","Moda"],["music","Música"],["design","Design"],["tattoo","Tatuagem"],["crafts","Artesanato"],["development","Desenvolvimento"],["other","Outra expressão"]].map(([v,l]) => `<option value="${v}" ${p.specialty===v?"selected":""}>${l}</option>`).join("")}</select></label>
      <label>Nova senha <small>(opcional)</small><input type="password" name="password" minlength="10" autocomplete="new-password"></label>
      <div class="divider">Redes e presença digital</div>
      <label>Instagram<input type="url" name="instagram_url" value="${escapeHtml(p.instagram_url || "")}" placeholder="https://instagram.com/..."></label><label>GitHub<input type="url" name="github_url" value="${escapeHtml(p.github_url || "")}" placeholder="https://github.com/..."></label>
      <label>LinkedIn<input type="url" name="linkedin_url" value="${escapeHtml(p.linkedin_url || "")}" placeholder="https://linkedin.com/in/..."></label><label>Behance<input type="url" name="behance_url" value="${escapeHtml(p.behance_url || "")}" placeholder="https://behance.net/..."></label>
      <div class="divider">Apoio direto por Pix <small>— a chave é cifrada no banco</small></div>
      <label>Tipo de chave<select name="pix_key_type"><option value="">Não alterar</option>${[["cpf","CPF"],["email","E-mail"],["phone","Celular"],["random","Aleatória"]].map(([v,l])=>`<option value="${v}" ${p.pix_key_type===v?"selected":""}>${l}</option>`).join("")}</select></label><label>Chave Pix<input name="pix_key" placeholder="Só preencha para alterar"></label>
      <label>Nome do recebedor<input name="pix_receiver_name" maxlength="25" value="${escapeHtml(p.pix_receiver_name || "")}" placeholder="Como consta no Pix"></label><label>Cidade<input name="pix_city" maxlength="15" value="${escapeHtml(p.pix_city || "")}" placeholder="Sua cidade"></label>
      <label class="wide"><span><input type="checkbox" name="is_available_for_work" ${p.is_available_for_work ? "checked" : ""}> Disponível para trabalhos</span></label>
    </div><p class="form-error modal-error" role="alert"></p></div><footer class="modal-footer"><span class="privacy-note">Foto e capa são alteradas pelos lápis do perfil.</span><button class="button button--ink" type="submit" data-submit-label="Salvar alterações">Salvar alterações</button></footer>`;
  }

  function openProfileEditor() { const form=$("#profile-form"); form.innerHTML=profileForm(); $("#profile-modal").showModal(); }

  async function submitProfile(event) {
    event.preventDefault();
    const form = event.currentTarget;
    clearFormError(form);
    const data = multipart(form);
    data.set("is_available_for_work", String(form.elements.is_available_for_work.checked));
    setSubmitting(form, true, "Salvando...");
    try {
      state.me = await api("/api/v1/auth/me/", { method:"PATCH", body:data });
      $("#profile-modal").close(); renderAccount(); toast("Perfil atualizado.", "success"); if (section === "profile") loadProfile(state.me.username);
    } catch (error) { showFormError(form, error); }
    finally { setSubmitting(form, false); }
  }

  function openProfileMedia(kind) {
    const form = $("#profile-media-form");
    form.reset();
    clearFormError(form);
    form.elements.media_kind.value = kind;
    $("#profile-media-title").textContent = kind === "avatar" ? "Alterar foto de perfil" : "Alterar imagem de capa";
    const preview = $("#profile-media-preview");
    const currentUrl = kind === "avatar" ? state.me.avatar_url : state.me.cover_url;
    preview.innerHTML = currentUrl ? `<img src="${escapeHtml(currentUrl)}" alt="Imagem atual">` : '<div class="media-placeholder">Sua prévia aparecerá aqui.</div>';
    preview.hidden = false;
    $("#profile-media-modal").showModal();
  }

  async function submitProfileMedia(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = form.elements.media_upload.files[0];
    clearFormError(form);
    if (!file) { showFormError(form, new Error("Selecione uma imagem antes de salvar.")); return; }
    try { validateImageFile(file); }
    catch (error) { showFormError(form, error); return; }
    const kind = form.elements.media_kind.value;
    const data = new FormData();
    data.set(kind === "cover" ? "cover_upload" : "avatar_upload", file);
    setSubmitting(form, true, "Enviando imagem...");
    try {
      state.me = await api("/api/v1/auth/me/", { method:"PATCH", body:data });
      closeModal("profile-media-modal");
      renderAccount();
      toast(kind === "cover" ? "Imagem de capa atualizada." : "Foto de perfil atualizada.", "success");
      if (section === "profile") loadProfile(state.me.username);
    } catch (error) { showFormError(form, error); }
    finally { setSubmitting(form, false); }
  }

  async function openSupport(username, postId = "", amount = "") {
    const modal=$("#support-modal"), box=$("#support-content"); box.innerHTML='<div class="page-loader"><i></i></div>'; if (!modal.open) modal.showModal();
    try {
      const query = amount ? `?amount=${encodeURIComponent(amount)}` : "";
      const data = await api(`/api/v1/support/${encodeURIComponent(username)}/pix/${query}`);
      box.innerHTML = `<header><div><span class="eyebrow">Apoio direto</span><h2>Apoie ${escapeHtml(data.creator)}.</h2></div><button type="button" class="icon-button" data-action="close-support">×</button></header><p>Escaneie no app do banco ou copie o código. O valor vai direto para a pessoa criadora; o PULSO não intermedeia o dinheiro.</p><div class="support-amount"><label>Valor opcional (R$)<input type="number" min="0.01" max="100000" step="0.01" value="${escapeHtml(amount)}" placeholder="25,00"></label><button type="button" data-action="refresh-pix" data-username="${escapeHtml(username)}" data-post-id="${escapeHtml(postId)}">Atualizar QR</button></div><div class="qr-wrap">${data.qr_svg}</div><div class="pix-code">${escapeHtml(data.payload)}</div><footer><button type="button" class="button button--ghost" data-action="copy-pix" data-payload="${escapeHtml(data.payload)}">Copiar código</button><button type="button" class="button button--ink" data-action="support-done" data-username="${escapeHtml(username)}" data-post-id="${escapeHtml(postId)}" data-amount="${escapeHtml(amount)}">Já apoiei ♡</button></footer>`;
    } catch (error) { box.innerHTML = `<header><h2>Apoio indisponível.</h2><button type="button" class="icon-button" data-action="close-support">×</button></header><p>${escapeHtml(error.message)}</p>`; }
  }

  async function startConversation(username) {
    try { await api("/api/v1/chat/conversations/", { method:"POST", body:JSON.stringify({ username }) }); window.location.assign("/mensagens/"); } catch (error) { toast(error.message,"error"); }
  }

  async function loadMessages() {
    const content=$("#page-content"); content.innerHTML='<div class="messages-layout"><aside class="conversation-list"><header><h1>Conversas</h1></header><div id="conversation-items"><div class="page-loader"><i></i></div></div></aside><section class="chat-panel" id="chat-panel"><div class="chat-placeholder"><div><div class="empty-orb">◫</div><h2>Conexões em movimento.</h2><p>Abra uma conversa para trocar ideias, áudio ou vídeo.</p></div></div></section></div>';
    try { const data=await api("/api/v1/chat/conversations/?page_size=40"); state.conversations=data.results||data; renderConversations(); if (state.conversations[0]) openConversation(state.conversations[0].id); } catch(error){$("#conversation-items").innerHTML=`<p>${escapeHtml(error.message)}</p>`}
  }

  function isMe(user){ return Boolean(user && state.me && ((state.me.id && user.id === state.me.id) || user.username === state.me.username)); }
  function otherParticipant(conversation){ return conversation.participants.find(participant=>!isMe(participant))||conversation.participants[0]; }
  function renderConversations(){ const box=$("#conversation-items"); box.innerHTML=state.conversations.length?state.conversations.map(c=>{const other=otherParticipant(c);return `<div class="conversation-item" data-conversation="${c.id}">${avatar(other)}<div><strong>${escapeHtml(other.display_name)}</strong><small>${escapeHtml(c.last_message?.content||"Comece a conversa")}</small></div></div>`}).join(""):emptyState("◫","Nenhuma conversa ainda.","Visite um perfil e envie uma mensagem."); }
  async function openConversation(id){
    state.activeConversation=state.conversations.find(c=>c.id===Number(id)); if(!state.activeConversation)return; const other=otherParticipant(state.activeConversation); $$(".conversation-item").forEach(x=>x.classList.toggle("active",x.dataset.conversation==id)); $(".conversation-list").classList.add("hidden-mobile"); const panel=$("#chat-panel");panel.classList.add("open-mobile");panel.innerHTML=`<header class="chat-header">${avatar(other)}<div><strong>${escapeHtml(other.display_name)}</strong><small>@${escapeHtml(other.username)}</small></div><div class="call-actions"><button data-call="audio" title="Ligação de áudio">⌕</button><button data-call="video" title="Ligação de vídeo">▣</button></div></header><div class="message-stream" id="message-stream"></div><div class="typing-indicator" id="typing"></div><form class="chat-form" id="chat-form"><input maxlength="2000" autocomplete="off" placeholder="Escreva uma mensagem protegida..."><button>↗</button></form>`;
    const messages=await api(`/api/v1/chat/conversations/${id}/messages/`); const stream=$("#message-stream");stream.innerHTML=messages.map(messageBubble).join("");stream.scrollTop=stream.scrollHeight; connectSocket(id); $("#chat-form").addEventListener("submit",sendMessage);
  }
  const messageBubble=m=>`<div class="message-bubble ${isMe(m.sender)?"mine":""}" aria-label="Mensagem de ${escapeHtml(m.sender?.display_name || m.sender?.username || "participante")}">${escapeHtml(m.content||m.body)}<time>${formatDate(m.created_at)}</time></div>`;
  function connectSocket(id){ if(state.socket)state.socket.close(); const scheme=location.protocol==="https:"?"wss":"ws";state.socket=new WebSocket(`${scheme}://${location.host}/ws/chat/${id}/`);state.socket.onmessage=event=>{const data=JSON.parse(event.data);if(data.type==="message"){const stream=$("#message-stream");stream.insertAdjacentHTML("beforeend",messageBubble({...data.message,content:data.message.body}));stream.scrollTop=stream.scrollHeight}else if(data.type==="typing"){$("#typing").textContent=data.active?"digitando...":""}else if(data.type==="signal")handleSignal(data.signal)}; }
  function sendMessage(event){event.preventDefault();const input=$("input",event.currentTarget);const body=input.value.trim();if(!body||state.socket?.readyState!==1)return;state.socket.send(JSON.stringify({type:"message",body}));input.value=""}

  async function startCall(kind){
    if(!state.activeConversation)return; try{const config=await api("/api/v1/chat/ice-servers/");state.localStream=await navigator.mediaDevices.getUserMedia({audio:true,video:kind==="video"});$("#call-modal").showModal();$("#local-video").srcObject=state.localStream;state.peer=new RTCPeerConnection(config);state.localStream.getTracks().forEach(track=>state.peer.addTrack(track,state.localStream));state.peer.ontrack=e=>$("#remote-video").srcObject=e.streams[0];state.peer.onicecandidate=e=>{if(e.candidate)sendSignal({candidate:e.candidate})};const offer=await state.peer.createOffer();await state.peer.setLocalDescription(offer);sendSignal({description:state.peer.localDescription,kind});await api(`/api/v1/chat/conversations/${state.activeConversation.id}/calls/`,{method:"POST",body:JSON.stringify({kind})});$("#call-status").textContent="Chamando..."}catch(error){toast(error.name==="NotAllowedError"?"Permita câmera e microfone para ligar.":error.message,"error");hangup()}}
  const sendSignal=signal=>state.socket?.send(JSON.stringify({type:"signal",signal}));
  async function handleSignal(signal){try{if(signal.description){if(!state.peer){const config=await api("/api/v1/chat/ice-servers/");state.localStream=await navigator.mediaDevices.getUserMedia({audio:true,video:signal.kind==="video"});$("#call-modal").showModal();$("#local-video").srcObject=state.localStream;state.peer=new RTCPeerConnection(config);state.localStream.getTracks().forEach(t=>state.peer.addTrack(t,state.localStream));state.peer.ontrack=e=>$("#remote-video").srcObject=e.streams[0];state.peer.onicecandidate=e=>{if(e.candidate)sendSignal({candidate:e.candidate})}}await state.peer.setRemoteDescription(signal.description);if(signal.description.type==="offer"){const answer=await state.peer.createAnswer();await state.peer.setLocalDescription(answer);sendSignal({description:state.peer.localDescription})}$("#call-status").textContent="Na chamada"}else if(signal.candidate&&state.peer)await state.peer.addIceCandidate(signal.candidate)}catch(error){toast("Não foi possível completar a chamada.","error")}}
  function hangup(){state.localStream?.getTracks().forEach(t=>t.stop());state.peer?.close();state.localStream=null;state.peer=null;$("#call-modal")?.close()}

  function reloadSection(){ if(section==="feed")loadFeed();else if(section==="explore")loadExplore();else if(section==="bookmarks")loadBookmarks();else if(section==="profile")loadProfile(profileUsername||state.me.username); }

  async function initApp(){
    activateNav(); try{state.me=await api("/api/v1/auth/me/");}catch(_){location.assign("/entrar/");return} renderAccount(); loadSuggestions();
    if(section==="feed")loadFeed(); else if(section==="explore")loadExplore(); else if(section==="bookmarks")loadBookmarks(); else if(section==="notifications")loadNotifications(); else if(section==="messages")loadMessages(); else if(section==="profile")loadProfile(profileUsername||state.me.username); else loadCreators();
    $("#post-form")?.addEventListener("submit",submitPost); $("#profile-form")?.addEventListener("submit",submitProfile); $("#profile-media-form")?.addEventListener("submit",submitProfileMedia); $("#post-body")?.addEventListener("input",e=>$("#char-counter").textContent=`${e.target.value.length} / 500`);
    $("#post-image-upload")?.addEventListener("change", event => {
      const file = event.target.files[0];
      const preview = $("#post-image-preview");
      if (!file) { preview.hidden = true; preview.innerHTML = ""; return; }
      try { renderImagePreview(file, preview, { removable:true }); }
      catch (error) { event.target.value = ""; showFormError($("#post-form"), error); }
    });
    $("#profile-media-upload")?.addEventListener("change", event => {
      const file = event.target.files[0];
      if (!file) return;
      try { renderImagePreview(file, $("#profile-media-preview"), { alt:"Prévia da nova imagem do perfil" }); clearFormError($("#profile-media-form")); }
      catch (error) { event.target.value = ""; showFormError($("#profile-media-form"), error); }
    });
    document.addEventListener("submit", event => {
      const commentForm = event.target.closest("[data-comment-form]");
      if (!commentForm) return;
      event.preventDefault();
      submitComment(commentForm);
    });
    document.addEventListener("click", async event => {
      const actionTarget = event.target.closest("[data-action]");
      const action = actionTarget?.dataset.action;
      const follow = event.target.closest("[data-follow]");
      const postAction = event.target.closest("[data-post-action]");
      const call = event.target.closest("[data-call]");
      if (follow) { event.preventDefault(); toggleFollow(follow.dataset.follow, follow); }
      else if (postAction) { event.preventDefault(); handlePostAction(postAction); }
      else if (call) startCall(call.dataset.call);
      else if (action === "open-composer") { closeMenus(); openComposer(); }
      else if (action === "ai-caption") aiCaption();
      else if (action === "edit-profile") { closeMenus(); openProfileEditor(); }
      else if (action === "edit-avatar") openProfileMedia("avatar");
      else if (action === "edit-cover") openProfileMedia("cover");
      else if (action === "close-modal") closeModal(actionTarget.dataset.modal);
      else if (action === "cancel-comment") { const form=actionTarget.closest("[data-comment-form]"); form.reset(); form.hidden=true; $(".inline-comment-error", form).textContent=""; }
      else if (action === "toggle-account-menu") toggleMenu("account-menu", actionTarget);
      else if (action === "toggle-mobile-menu") toggleMenu("mobile-account-menu", actionTarget);
      else if (action === "toggle-theme") { closeMenus(); toggleTheme(); }
      else if (action === "logout") { closeMenus(); await logoutUser(); }
      else if (action === "support") openSupport(actionTarget.dataset.username, actionTarget.dataset.postId || "");
      else if (action === "refresh-pix") { const value=$(".support-amount input", $("#support-content")).value; openSupport(actionTarget.dataset.username, actionTarget.dataset.postId || "", value); }
      else if (action === "close-support") $("#support-modal").close();
      else if (action === "copy-pix") { await navigator.clipboard.writeText(actionTarget.dataset.payload); toast("Código Pix copiado.", "success"); }
      else if (action === "support-done") {
        const payload = { message: "Apoio iniciado via QR Code" };
        if (actionTarget.dataset.postId) payload.post = Number(actionTarget.dataset.postId);
        if (actionTarget.dataset.amount) payload.amount = actionTarget.dataset.amount;
        await api(`/api/v1/support/${actionTarget.dataset.username}/intent/`, { method:"POST", body:JSON.stringify(payload) });
        $("#support-modal").close(); toast("Seu apoio faz a cultura circular ♡", "success");
      }
      else if (action === "message-user") startConversation(actionTarget.dataset.username);
      else if (action === "refresh-creators") loadSuggestions();
      else if (action === "remove-post-image") { $("#post-image-upload").value = ""; $("#post-image-preview").hidden = true; $("#post-image-preview").innerHTML = ""; }
      else if (action === "hangup") hangup();
      else if (!event.target.closest(".account-area,.mobile-header")) closeMenus();
    });
    $$("dialog.modal").forEach(modal => {
      modal.addEventListener("click", event => { if (event.target === modal) modal.close(); });
    });
    $("#global-search")?.addEventListener("keydown",e=>{if(e.key==="Enter"&&e.target.value.trim())location.assign(`/explorar/?q=${encodeURIComponent(e.target.value.trim())}`)});$("#page-content")?.addEventListener("click",e=>{const item=e.target.closest("[data-conversation]");if(item)openConversation(item.dataset.conversation)});
  }

  if(section === "auth") initAuth();
  else if($("#app-shell")) initApp();
})();
