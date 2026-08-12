(() => {
  "use strict";

  const body = document.body;
  const section = body.dataset.section;
  const profileUsername = body.dataset.profile;
  const state = { me: null, conversations: [], socket: null, peer: null, localStream: null, activeConversation: null };
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

  async function api(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) headers["X-CSRFToken"] = csrf();
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const details = data.error?.details || data;
      const message = details.detail || Object.values(details)[0]?.[0] || "Não foi possível concluir.";
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

  function renderError(error) {
    const box = $("#form-error");
    if (box) box.textContent = error.message;
    else toast(error.message, "error");
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
    chip.innerHTML = `${avatar(state.me)}<div><strong>${escapeHtml(state.me.display_name)}</strong><small>@${escapeHtml(state.me.username)}</small></div><span>•••</span>`;
    chip.addEventListener("click", openProfileEditor);
    $$('[data-action="my-profile"]').forEach(link => link.href = `/perfil/${state.me.username}/`);
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
        const text = prompt("Escreva seu comentário:");
        if (!text?.trim()) return;
        await api(`/api/v1/social/posts/${postId}/comments/`, { method:"POST", body:JSON.stringify({ body:text.trim() }) });
        toast("Comentário publicado.", "success");
        reloadSection();
        return;
      }
      const result = await api(`/api/v1/social/posts/${postId}/${action}/`, { method:"POST" });
      button.classList.toggle(action === "like" ? "active-like" : action === "bookmark" ? "active-bookmark" : "active-repost", result[`${action}d`] ?? result.liked ?? result.bookmarked ?? result.reposted);
      const count = $("span", button); if (count && result.count !== undefined) count.textContent = result.count;
    } catch (error) { toast(error.message, "error"); }
  }

  async function loadProfile(username) {
    const content = $("#page-content");
    content.innerHTML = '<div class="page-loader"><i></i></div>';
    try {
      const profile = await api(`/api/v1/auth/profiles/${encodeURIComponent(username)}/`);
      const posts = await api(`/api/v1/social/posts/?author__username=${encodeURIComponent(username)}&page_size=30`);
      content.innerHTML = `<section class="profile-hero">
        <div class="profile-cover" ${profile.cover_url ? `style="background-image:url('${escapeHtml(profile.cover_url)}')"` : ""}></div>
        <div class="profile-main">
          <div class="profile-avatar">${profile.avatar_url ? `<img src="${escapeHtml(profile.avatar_url)}" alt="">` : initials(profile.display_name)}</div>
          <div class="profile-actions">
            ${profile.is_own ? '<button class="outline-button" data-action="edit-profile">Editar perfil</button>' : `<button class="outline-button" data-action="message-user" data-username="${escapeHtml(profile.username)}">Mensagem</button>${profile.pix_enabled ? `<button class="outline-button outline-button--pink" data-action="support" data-username="${escapeHtml(profile.username)}">Apoiar</button>` : ""}<button class="button button--ink" data-follow="${escapeHtml(profile.username)}">${profile.is_following ? "Seguindo" : "Seguir"}</button>`}
          </div>
          <h1>${escapeHtml(profile.display_name)}</h1><span class="profile-handle">@${escapeHtml(profile.username)}</span>
          ${profile.is_available_for_work ? '<p><span class="available-pill">disponível para projetos</span></p>' : ""}
          <p class="profile-bio">${escapeHtml(profile.bio || "Este espaço ainda está ganhando forma.")}</p>
          <div class="profile-meta">${profile.specialty ? `<span>✦ ${escapeHtml(profile.specialty)}</span>` : ""}${profile.location ? `<span>⌖ ${escapeHtml(profile.location)}</span>` : ""}${profile.website ? `<a href="${escapeHtml(profile.website)}" target="_blank" rel="noopener">↗ portfólio</a>` : ""}</div>
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

  function openComposer() { $("#composer-modal")?.showModal(); }

  async function submitPost(event) {
    event.preventDefault();
    const form = event.currentTarget;
    try {
      await api("/api/v1/social/posts/", { method:"POST", body:JSON.stringify(serialize(form)) });
      form.reset(); $("#composer-modal").close(); toast("Seu trabalho entrou no pulso.", "success"); reloadSection();
    } catch (error) { toast(error.message, "error"); }
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
    return `<header><div><span class="eyebrow">Seu espaço</span><h2>Edite apenas o que quiser.</h2></div><button class="icon-button" value="cancel">×</button></header><div class="profile-fields">
      <label>Nome criativo<input name="display_name" value="${escapeHtml(p.display_name || "")}"></label><label>Usuário<input name="username" value="${escapeHtml(p.username)}"></label>
      <label class="wide">Bio<textarea name="bio" maxlength="220">${escapeHtml(p.bio || "")}</textarea></label>
      <label>Foto (URL HTTPS)<input type="url" name="avatar_url" value="${escapeHtml(p.avatar_url || "")}"></label><label>Capa (URL HTTPS)<input type="url" name="cover_url" value="${escapeHtml(p.cover_url || "")}"></label>
      <label>Localização<input name="location" value="${escapeHtml(p.location || "")}"></label><label>Portfólio<input type="url" name="website" value="${escapeHtml(p.website || "")}"></label>
      <label>Expressão<select name="specialty">${[["photography","Fotografia"],["nail-art","Nail art"],["hair","Cabelo"],["painting","Pintura"],["digital-art","Arte digital"],["fashion","Moda"],["music","Música"],["design","Design"],["tattoo","Tatuagem"],["crafts","Artesanato"],["other","Outra expressão"]].map(([v,l]) => `<option value="${v}" ${p.specialty===v?"selected":""}>${l}</option>`).join("")}</select></label>
      <label>Nova senha <small>(opcional)</small><input type="password" name="password" minlength="10" autocomplete="new-password"></label>
      <div class="divider">Apoio direto por Pix <small>— a chave é cifrada no banco</small></div>
      <label>Tipo de chave<select name="pix_key_type"><option value="">Não alterar</option><option value="cpf">CPF</option><option value="email">E-mail</option><option value="phone">Celular</option><option value="random">Aleatória</option></select></label><label>Chave Pix<input name="pix_key" placeholder="Só preencha para alterar"></label>
      <label>Nome do recebedor<input name="pix_receiver_name" maxlength="25" placeholder="Como consta no Pix"></label><label>Cidade<input name="pix_city" maxlength="15" placeholder="Sua cidade"></label>
      <label class="wide"><span><input type="checkbox" name="is_available_for_work" ${p.is_available_for_work ? "checked" : ""}> Disponível para trabalhos</span></label>
    </div><footer><span class="privacy-note">Todos os campos são opcionais.</span><button class="button button--ink" type="submit">Salvar alterações</button></footer>`;
  }

  function openProfileEditor() { const form=$("#profile-form"); form.innerHTML=profileForm(); $("#profile-modal").showModal(); }

  async function submitProfile(event) {
    event.preventDefault();
    const data = serialize(event.currentTarget);
    data.is_available_for_work = !!event.currentTarget.elements.is_available_for_work.checked;
    try {
      state.me = await api("/api/v1/auth/me/", { method:"PATCH", body:JSON.stringify(data) });
      $("#profile-modal").close(); renderAccount(); toast("Perfil atualizado.", "success"); if (section === "profile") loadProfile(state.me.username);
    } catch (error) { toast(error.message, "error"); }
  }

  async function openSupport(username) {
    const modal=$("#support-modal"), box=$("#support-content"); box.innerHTML='<div class="page-loader"><i></i></div>'; modal.showModal();
    try {
      const data = await api(`/api/v1/support/${encodeURIComponent(username)}/pix/`);
      box.innerHTML = `<header><div><span class="eyebrow">Apoio direto</span><h2>Apoie ${escapeHtml(data.creator)}.</h2></div><button class="icon-button" data-action="close-support">×</button></header><p>Escaneie no app do banco ou copie o código. A PULSO não toca no dinheiro.</p><div class="qr-wrap">${data.qr_svg}</div><div class="pix-code">${escapeHtml(data.payload)}</div><footer><button class="button button--ghost" data-action="copy-pix" data-payload="${escapeHtml(data.payload)}">Copiar código</button><button class="button button--ink" data-action="support-done" data-username="${escapeHtml(username)}">Já apoiei ♡</button></footer>`;
    } catch (error) { box.innerHTML = `<header><h2>Apoio indisponível.</h2><button class="icon-button" data-action="close-support">×</button></header><p>${escapeHtml(error.message)}</p>`; }
  }

  async function startConversation(username) {
    try { await api("/api/v1/chat/conversations/", { method:"POST", body:JSON.stringify({ username }) }); window.location.assign("/mensagens/"); } catch (error) { toast(error.message,"error"); }
  }

  async function loadMessages() {
    const content=$("#page-content"); content.innerHTML='<div class="messages-layout"><aside class="conversation-list"><header><h1>Conversas</h1></header><div id="conversation-items"><div class="page-loader"><i></i></div></div></aside><section class="chat-panel" id="chat-panel"><div class="chat-placeholder"><div><div class="empty-orb">◫</div><h2>Conexões em movimento.</h2><p>Abra uma conversa para trocar ideias, áudio ou vídeo.</p></div></div></section></div>';
    try { const data=await api("/api/v1/chat/conversations/?page_size=40"); state.conversations=data.results||data; renderConversations(); if (state.conversations[0]) openConversation(state.conversations[0].id); } catch(error){$("#conversation-items").innerHTML=`<p>${escapeHtml(error.message)}</p>`}
  }

  function otherParticipant(conversation){ return conversation.participants.find(p=>p.id!==state.me.id)||conversation.participants[0]; }
  function renderConversations(){ const box=$("#conversation-items"); box.innerHTML=state.conversations.length?state.conversations.map(c=>{const other=otherParticipant(c);return `<div class="conversation-item" data-conversation="${c.id}">${avatar(other)}<div><strong>${escapeHtml(other.display_name)}</strong><small>${escapeHtml(c.last_message?.content||"Comece a conversa")}</small></div></div>`}).join(""):emptyState("◫","Nenhuma conversa ainda.","Visite um perfil e envie uma mensagem."); }
  async function openConversation(id){
    state.activeConversation=state.conversations.find(c=>c.id===Number(id)); if(!state.activeConversation)return; const other=otherParticipant(state.activeConversation); $$(".conversation-item").forEach(x=>x.classList.toggle("active",x.dataset.conversation==id)); $(".conversation-list").classList.add("hidden-mobile"); const panel=$("#chat-panel");panel.classList.add("open-mobile");panel.innerHTML=`<header class="chat-header">${avatar(other)}<div><strong>${escapeHtml(other.display_name)}</strong><small>@${escapeHtml(other.username)}</small></div><div class="call-actions"><button data-call="audio" title="Ligação de áudio">⌕</button><button data-call="video" title="Ligação de vídeo">▣</button></div></header><div class="message-stream" id="message-stream"></div><div class="typing-indicator" id="typing"></div><form class="chat-form" id="chat-form"><input maxlength="2000" autocomplete="off" placeholder="Escreva uma mensagem protegida..."><button>↗</button></form>`;
    const messages=await api(`/api/v1/chat/conversations/${id}/messages/`); const stream=$("#message-stream");stream.innerHTML=messages.map(messageBubble).join("");stream.scrollTop=stream.scrollHeight; connectSocket(id); $("#chat-form").addEventListener("submit",sendMessage);
  }
  const messageBubble=m=>`<div class="message-bubble ${m.sender.id===state.me.id?"mine":""}">${escapeHtml(m.content||m.body)}<time>${formatDate(m.created_at)}</time></div>`;
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
    $("#post-form")?.addEventListener("submit",submitPost); $("#profile-form")?.addEventListener("submit",submitProfile); $("#post-body")?.addEventListener("input",e=>$("#char-counter").textContent=`${e.target.value.length} / 500`);
    document.addEventListener("click",async event=>{const action=event.target.closest("[data-action]")?.dataset.action;const follow=event.target.closest("[data-follow]");const postAction=event.target.closest("[data-post-action]");const call=event.target.closest("[data-call]");if(follow){event.preventDefault();toggleFollow(follow.dataset.follow,follow)}else if(postAction){event.preventDefault();handlePostAction(postAction)}else if(call)startCall(call.dataset.call);else if(action==="open-composer")openComposer();else if(action==="ai-caption")aiCaption();else if(action==="edit-profile")openProfileEditor();else if(action==="support")openSupport(event.target.closest("[data-username]").dataset.username);else if(action==="close-support")$("#support-modal").close();else if(action==="copy-pix"){await navigator.clipboard.writeText(event.target.closest("[data-payload]").dataset.payload);toast("Código Pix copiado.","success")}else if(action==="support-done"){const username=event.target.dataset.username;await api(`/api/v1/support/${username}/intent/`,{method:"POST",body:JSON.stringify({message:"Apoio iniciado via QR Code"})});$("#support-modal").close();toast("Seu apoio faz a cultura circular ♡","success")}else if(action==="message-user")startConversation(event.target.dataset.username);else if(action==="refresh-creators")loadSuggestions();else if(action==="hangup")hangup()});
    $("#global-search")?.addEventListener("keydown",e=>{if(e.key==="Enter"&&e.target.value.trim())location.assign(`/explorar/?q=${encodeURIComponent(e.target.value.trim())}`)});$("#page-content")?.addEventListener("click",e=>{const item=e.target.closest("[data-conversation]");if(item)openConversation(item.dataset.conversation)});
  }

  if(section === "auth") initAuth();
  else if($("#app-shell")) initApp();
})();
