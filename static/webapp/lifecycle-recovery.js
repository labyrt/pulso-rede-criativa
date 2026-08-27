(() => {
  "use strict";

  const shell = document.querySelector("#app-shell");
  const pageContent = document.querySelector("#page-content");
  const section = document.body.dataset.section;
  if (!shell || !pageContent || section !== "feed") return;

  const diagnostic = (event, detail = "") => {
    const params = new URLSearchParams({ event });
    if (detail) params.set("detail", String(detail).slice(0, 160));
    fetch(`/api/v1/client-diagnostic/?${params}`, {
      method: "GET",
      credentials: "omit",
      cache: "no-store",
      keepalive: true,
      headers: { Accept: "text/plain" },
    }).catch(() => {});
  };

  diagnostic("watchdog_loaded", `visibility=${document.visibilityState}`);
  window.addEventListener("error", event => {
    const source = String(event.filename || "unknown").split("/").pop();
    diagnostic("window_error", `${source}:${event.lineno || 0}:${event.colno || 0}`);
  });
  window.addEventListener("unhandledrejection", event => {
    const reason = event.reason;
    diagnostic("unhandled_rejection", reason?.name || reason?.constructor?.name || typeof reason);
  });

  const stallDelayMs = 3500;
  const requestTimeoutMs = 10000;
  let recoveryTimer = null;
  let recovering = false;

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
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
    .trim().split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase() || "P";

  function loader() {
    return pageContent.querySelector(".page-loader");
  }

  function avatar(user = {}) {
    const label = user.display_name || user.username || "P";
    const image = safeUrl(user.avatar_url);
    return `<span class="avatar">${image ? `<img src="${escapeHtml(image)}" alt="">` : escapeHtml(initials(label))}</span>`;
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

    return `<article class="post-card" data-post="${escapeHtml(post.id ?? "")}">
      <a href="${profileHref}">${avatar(author)}</a>
      <div>
        <header class="post-head">
          <a href="${profileHref}"><strong>${escapeHtml(author.display_name || username || "Criador")}</strong></a>
          ${username ? `<small>@${escapeHtml(username)}</small>` : ""}
          <time>${escapeHtml(timeAgo(post.created_at))}</time>
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
        throw new Error(data?.error?.message || data?.detail || "Não foi possível carregar seu feed.");
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
      : emptyState("✦", "Seu pulso começa pelas conexões.", "Siga criadores em Descobrir e o trabalho deles aparecerá aqui.", '<a class="button button--ink" href="/explorar/">Descobrir criadores</a>');

    pageContent.innerHTML = `${feedHeader()}${composer}<div id="post-list">${body}</div>`;
    pageContent.dataset.feedRecovered = "true";
    window.dispatchEvent(new CustomEvent("pulso:feed-ready"));
  }

  function renderRetry(error) {
    diagnostic("retry_rendered", error?.name || "Error");
    const message = error?.name === "AbortError"
      ? "A conexão demorou mais que o esperado."
      : (error?.message || "Não foi possível carregar seu feed.");
    pageContent.innerHTML = `${feedHeader()}${emptyState("↻", "Não consegui mostrar seu feed.", message, '<button type="button" class="button button--ink" data-pulso-retry>Tentar novamente</button>')}`;
    pageContent.querySelector("[data-pulso-retry]")?.addEventListener("click", () => {
      pageContent.innerHTML = `${feedHeader()}<div class="page-loader"><i></i><span>Carregando seu feed...</span></div>`;
      scheduleRecovery(0, true);
    });
  }

  async function recoverStalledFeed() {
    recoveryTimer = null;
    diagnostic("recovery_deadline", `visibility=${document.visibilityState}`);
    if (recovering || !loader()) {
      diagnostic("recovery_skipped", recovering ? "already_running" : "loader_gone");
      return;
    }

    recovering = true;
    diagnostic("recovery_started");
    try {
      const feedPromise = requestJson(`/api/v1/social/feed/?_pulso=${Date.now()}`).then(data => {
        diagnostic("feed_response_ok");
        return data;
      });
      const mePromise = requestJson(`/api/v1/auth/me/?_pulso=${Date.now()}`)
        .then(data => {
          diagnostic("me_response_ok");
          return data;
        })
        .catch(error => {
          diagnostic("me_response_error", error?.name || "Error");
          return {};
        });
      const [feed, me] = await Promise.all([feedPromise, mePromise]);
      renderFeed(feed, me || {});
      diagnostic("render_success");
    } catch (error) {
      diagnostic("render_error", error?.name || "Error");
      renderRetry(error);
    } finally {
      recovering = false;
    }
  }

  function scheduleRecovery(delay = stallDelayMs, replace = false) {
    if (!loader() || recovering) return;
    if (recoveryTimer !== null && !replace) return;
    if (recoveryTimer !== null) window.clearTimeout(recoveryTimer);
    diagnostic("recovery_armed", `delay=${delay};visibility=${document.visibilityState}`);
    recoveryTimer = window.setTimeout(recoverStalledFeed, delay);
  }

  // Important: DOM mutations must never postpone the absolute recovery deadline.
  // The main application can replace the loading markup while it initializes;
  // the watchdog simply keeps its original timer and checks the DOM at deadline.
  const observer = new MutationObserver(() => {
    if (loader() && recoveryTimer === null && !recovering) scheduleRecovery();
  });
  observer.observe(pageContent, { childList: true, subtree: true });

  window.addEventListener("pageshow", event => {
    if (event.persisted) diagnostic("pageshow_persisted");
    if (loader()) scheduleRecovery(event.persisted ? 100 : stallDelayMs, event.persisted);
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && loader()) scheduleRecovery(100, true);
  });

  window.addEventListener("online", () => {
    if (loader()) scheduleRecovery(100, true);
  });

  // One absolute deadline is armed before app.js. It is not cancelled by DOM
  // churn and it is allowed to complete while the page is backgrounded. Only
  // idempotent GET requests are used by this recovery path.
  scheduleRecovery();
})();
