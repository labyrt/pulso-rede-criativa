(() => {
  "use strict";

  const shell = document.querySelector("#app-shell");
  const pageContent = document.querySelector("#page-content");
  const section = document.body.dataset.section;
  if (!shell || !pageContent || section !== "feed") return;

  const stallDelayMs = 3500;
  const requestTimeoutMs = 10000;
  let stallTimer = null;
  let recovering = false;

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  }[character]));

  const safeUrl = value => {
    const url = String(value || "").trim();
    if (!url) return "";
    if (url.startsWith("/")) return url;
    try {
      const parsed = new URL(url, window.location.origin);
      return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "";
    } catch (_) {
      return "";
    }
  };

  const initials = (name = "P") => String(name || "P")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part[0] || "")
    .join("")
    .toUpperCase() || "P";

  function loader() {
    return pageContent.querySelector(".page-loader");
  }

  function avatar(user = {}) {
    const label = user.display_name || user.username || "P";
    const image = safeUrl(user.avatar_url);
    return `<span class="avatar">${image ? `<img src="${escapeHtml(image)}" alt="">` : escapeHtml(initials(label))}</span>`;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function timeAgo(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (seconds < 60) return "agora";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h`;
    return `${Math.floor(seconds / 86400)} d`;
  }

  function feedHeader() {
    return '<header class="page-header"><h1>Meu pulso</h1><p>Trabalhos e ideias das pessoas que você segue.</p></header>';
  }

  function emptyState(icon, title, copy, action = "") {
    return `<div class="empty-state"><div><div class="empty-orb">${escapeHtml(icon)}</div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(copy)}</p>${action}</div></div>`;
  }

  function commentsMarkup(post) {
    const comments = Array.isArray(post.latest_comments) ? post.latest_comments : [];
    return comments.map(comment => {
      const author = comment?.author || {};
      return `<p><strong>@${escapeHtml(author.username || "criador")}</strong>${escapeHtml(comment?.body || "")}</p>`;
    }).join("");
  }

  function postCard(post = {}, me = {}) {
    const author = post.author || {};
    const username = author.username || "";
    const profileHref = username ? `/perfil/${encodeURIComponent(username)}/` : "#";
    const imageUrl = safeUrl(post.image_url);
    const videoUrl = safeUrl(post.video_url);
    const portfolioUrl = safeUrl(post.portfolio_url);
    const tags = Array.isArray(post.tag_list) ? post.tag_list : [];
    const comments = commentsMarkup(post);
    const createdAt = formatDate(post.created_at);

    return `<article class="post-card" data-post="${escapeHtml(post.id ?? "")}">
      <a href="${profileHref}">${avatar(author)}</a>
      <div>
        <header class="post-head">
          <a href="${profileHref}"><strong>${escapeHtml(author.display_name || username || "Criador")}</strong></a>
          ${username ? `<small>@${escapeHtml(username)}</small>` : ""}
          <time title="${escapeHtml(createdAt)}">${escapeHtml(timeAgo(post.created_at))}</time>
        </header>
        <div class="post-body">${escapeHtml(post.body || "")}</div>
        ${imageUrl ? `<img class="post-media" src="${escapeHtml(imageUrl)}" alt="Trabalho publicado por ${escapeHtml(author.display_name || username || "criador")}" loading="lazy">` : ""}
        ${videoUrl ? `<video class="post-media" src="${escapeHtml(videoUrl)}" controls preload="metadata"></video>` : ""}
        ${portfolioUrl ? `<a class="portfolio-link" href="${escapeHtml(portfolioUrl)}" target="_blank" rel="noopener noreferrer"><span>Ver projeto completo</span><b>↗</b></a>` : ""}
        ${tags.length ? `<div class="tag-row">${tags.map(tag => `<span>#${escapeHtml(tag)}</span>`).join("")}</div>` : ""}
        <div class="post-actions">
          <button data-post-action="like" class="${post.is_liked ? "active-like" : ""}" aria-label="Curtir">${post.is_liked ? "♥" : "♡"} <span>${Number(post.likes_count || 0)}</span></button>
          <button data-post-action="comment" aria-label="Comentar">◌ <span>${Number(post.comments_count || 0)}</span></button>
          <button data-post-action="repost" class="${post.is_reposted ? "active-repost" : ""}" aria-label="Repostar">↻ <span>${Number(post.reposts_count || 0)}</span></button>
          <button data-post-action="bookmark" class="${post.is_bookmarked ? "active-bookmark" : ""}" aria-label="Guardar">${post.is_bookmarked ? "◆" : "◇"}</button>
          <button data-post-action="share" aria-label="Compartilhar">↗</button>
        </div>
        <form class="inline-comment" data-comment-form hidden>
          ${avatar(me)}
          <label><span class="sr-only">Escreva um comentário</span><textarea name="body" maxlength="500" rows="1" placeholder="Deixe uma ideia, pergunta ou incentivo..." required></textarea></label>
          <div class="inline-comment-actions"><button type="button" data-action="cancel-comment">Cancelar</button><button type="submit">Comentar ↗</button></div>
          <p class="inline-comment-error" role="alert"></p>
        </form>
        ${post.pix_enabled ? `<button class="post-support" data-action="support" data-username="${escapeHtml(username)}" data-post-id="${escapeHtml(post.id ?? "")}"><span>♡</span> Apoiar este trabalho via Pix</button>` : ""}
        ${comments ? `<div class="comment-preview">${comments}</div>` : ""}
      </div>
    </article>`;
  }

  async function requestJson(url) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), requestTimeoutMs);
    try {
      const response = await fetch(url, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const message = data?.error?.message || data?.detail || "Não foi possível carregar seu feed.";
        throw new Error(message);
      }
      return data;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function renderFeed(data, me) {
    const posts = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
    const composer = `<div class="composer-inline" data-action="open-composer">${avatar(me)}<p>Compartilhe o que está tomando forma...</p><span>＋</span></div>`;
    const body = posts.length
      ? posts.map(post => postCard(post, me)).join("")
      : emptyState(
          "✦",
          "Seu pulso começa pelas conexões.",
          "Siga criadores em Descobrir e o trabalho deles aparecerá aqui.",
          '<a class="button button--ink" href="/explorar/">Descobrir criadores</a>'
        );

    pageContent.innerHTML = `${feedHeader()}${composer}<div id="post-list">${body}</div>`;
    pageContent.dataset.feedRecovered = "true";
    window.dispatchEvent(new CustomEvent("pulso:feed-ready"));
  }

  function renderRetry(error) {
    const message = error?.name === "AbortError"
      ? "A conexão demorou mais que o esperado."
      : (error?.message || "Não foi possível carregar seu feed.");

    pageContent.innerHTML = `${feedHeader()}${emptyState("↻", "Não consegui mostrar seu feed.", message, '<button type="button" class="button button--ink" data-pulso-retry>Tentar novamente</button>')}`;
    pageContent.querySelector("[data-pulso-retry]")?.addEventListener("click", () => {
      pageContent.innerHTML = `${feedHeader()}<div class="page-loader"><i></i><span>Carregando seu feed...</span></div>`;
      recoverStalledFeed();
    });
  }

  async function recoverStalledFeed() {
    if (recovering || document.hidden || !loader()) return;
    recovering = true;
    window.clearTimeout(stallTimer);
    stallTimer = null;

    try {
      const [feed, me] = await Promise.all([
        requestJson(`/api/v1/social/feed/?_pulso=${Date.now()}`),
        requestJson(`/api/v1/auth/me/?_pulso=${Date.now()}`).catch(() => ({})),
      ]);
      renderFeed(feed, me || {});
    } catch (error) {
      renderRetry(error);
    } finally {
      recovering = false;
    }
  }

  function armRecovery(delay = stallDelayMs) {
    window.clearTimeout(stallTimer);
    if (!loader() || document.hidden) return;
    stallTimer = window.setTimeout(() => recoverStalledFeed(), delay);
  }

  const observer = new MutationObserver(() => {
    if (loader()) armRecovery();
    else window.clearTimeout(stallTimer);
  });
  observer.observe(pageContent, { childList: true, subtree: true });

  window.addEventListener("pageshow", event => {
    if (event.persisted && loader()) armRecovery(100);
    else armRecovery();
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && loader()) armRecovery(250);
  });

  window.addEventListener("online", () => {
    if (loader()) armRecovery(100);
  });

  // The normal app renderer always gets the first chance. This watchdog only
  // intervenes when the API has completed but the loading element is still on
  // screen, or when a restored mobile tab kept stale DOM. It never reloads the
  // document and never repeats mutating requests.
  armRecovery();
})();
