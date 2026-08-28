(() => {
  "use strict";
  if (document.body.dataset.section !== "notifications" || !document.querySelector("#app-shell")) return;

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));
  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || "";
  const timeAgo = date => {
    const seconds = Math.floor((Date.now() - new Date(date)) / 1000);
    if (seconds < 60) return "agora";
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} h`;
    return `${Math.floor(seconds / 86400)} d`;
  };
  const labels = {
    follow: "começou a seguir você",
    like: "curtiu sua publicação",
    comment: "comentou na sua publicação",
    repost: "compartilhou sua publicação",
    post: "publicou algo novo",
    message: "enviou uma mensagem",
    call: "ligou para você",
  };

  function avatar(actor) {
    if (actor.avatar_url) return `<span class="avatar"><img src="${escapeHtml(actor.avatar_url)}" alt=""></span>`;
    const initials = (actor.display_name || actor.username || "P").split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
    return `<span class="avatar">${escapeHtml(initials)}</span>`;
  }

  async function fetchJson(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) headers["X-CSRFToken"] = csrf();
    const response = await fetch(url, { credentials: "same-origin", cache: "no-store", ...options, headers });
    return response.ok ? response.json().catch(() => ({})) : null;
  }

  async function enhance() {
    const data = await fetchJson("/api/v1/social/notifications/?page_size=40");
    const list = document.querySelector("#notifications");
    if (!data || !list) return;
    const items = data.results || data;
    list.innerHTML = items.length ? items.map(item => `
      <div class="notification-item ${item.is_read ? "" : "unread"}">
        ${avatar(item.actor)}
        <p><strong>${escapeHtml(item.actor.display_name)}</strong> ${escapeHtml(labels[item.kind] || "interagiu com você")}${item.post_excerpt ? `<br><small>“${escapeHtml(item.post_excerpt)}”</small>` : ""}</p>
        <time>${timeAgo(item.created_at)}</time>
      </div>`).join("") : '<div class="empty-state"><div><div class="empty-orb">♢</div><h2>Tudo quieto por aqui.</h2><p>Novas conexões e interações aparecerão neste espaço.</p></div></div>';
    await fetchJson("/api/v1/social/notifications/read_all/", { method: "POST" });
  }

  let attempts = 0;
  const timer = setInterval(() => {
    attempts += 1;
    const list = document.querySelector("#notifications");
    if ((list && !list.querySelector(".page-loader")) || attempts > 50) {
      clearInterval(timer);
      enhance();
    }
  }, 100);
})();
