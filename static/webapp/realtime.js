(() => {
  "use strict";

  const appShell = document.querySelector("#app-shell");
  if (!appShell) return;

  const section = document.body.dataset.section || "";
  const live = {
    eventsSocket: null,
    reconnectTimer: null,
    notificationCount: 0,
    messageCount: 0,
    peer: null,
    localStream: null,
    callId: null,
    conversationId: null,
    callKind: null,
    incoming: null,
    pendingSignals: [],
    pendingCandidates: [],
  };

  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));

  const csrf = () => document.cookie.split("; ").find(row => row.startsWith("csrftoken="))?.split("=")[1] || "";

  async function requestJson(url, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body && typeof options.body === "string") headers["Content-Type"] = "application/json";
    if (!/^(GET|HEAD|OPTIONS)$/i.test(options.method || "GET")) headers["X-CSRFToken"] = csrf();
    const response = await fetch(url, { credentials: "same-origin", cache: "no-store", ...options, headers });
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.error?.message || "Não foi possível concluir.");
    return data;
  }

  function toast(message) {
    const stack = document.querySelector("#toast-stack");
    if (!stack) return;
    const item = document.createElement("div");
    item.className = "toast live-toast";
    item.textContent = message;
    stack.append(item);
    setTimeout(() => item.remove(), 3800);
  }

  function setBadge(selector, count) {
    const node = document.querySelector(selector);
    if (!node) return;
    const safeCount = Math.max(0, Number(count) || 0);
    node.textContent = safeCount > 99 ? "99+" : safeCount ? String(safeCount) : "";
    node.toggleAttribute("data-has-count", safeCount > 0);
  }

  function renderBadges() {
    setBadge("#notification-badge", live.notificationCount);
    setBadge("#mobile-notification-badge", live.notificationCount);
    setBadge("#message-badge", live.messageCount);
    setBadge("#mobile-message-badge", live.messageCount);
  }

  function ensureMobileLiveControls() {
    const headerActions = document.querySelector(".mobile-header-actions");
    if (headerActions && !document.querySelector("#mobile-notification-link")) {
      const link = document.createElement("a");
      link.id = "mobile-notification-link";
      link.className = "mobile-live-link";
      link.href = "/notificacoes/";
      link.setAttribute("aria-label", "Atividade");
      link.innerHTML = '<span aria-hidden="true">♢</span><i id="mobile-notification-badge"></i>';
      headerActions.prepend(link);
    }
    const messageLink = document.querySelector('.mobile-nav [data-nav="messages"]');
    if (messageLink && !messageLink.querySelector("#mobile-message-badge")) {
      const badge = document.createElement("i");
      badge.id = "mobile-message-badge";
      messageLink.append(badge);
    }
  }

  async function syncBadges() {
    try {
      const [notifications, conversations] = await Promise.all([
        requestJson("/api/v1/social/notifications/?page_size=100"),
        requestJson("/api/v1/chat/conversations/?page_size=100"),
      ]);
      const activityItems = notifications?.results || notifications || [];
      const conversationItems = conversations?.results || conversations || [];
      live.notificationCount = section === "notifications" ? 0 : activityItems.filter(item => !item.is_read).length;
      live.messageCount = conversationItems.reduce((total, item) => total + Number(item.unread_count || 0), 0);
      renderBadges();
    } catch (_) {
      renderBadges();
    }
  }

  function ensureMobilePeopleSection() {
    if (!["feed", "explore"].includes(section) || document.querySelector("#mobile-people")) return;
    const pageContent = document.querySelector("#page-content");
    if (!pageContent) return;
    const sectionNode = document.createElement("section");
    sectionNode.className = "mobile-people";
    sectionNode.id = "mobile-people";
    sectionNode.innerHTML = `
      <header>
        <div><span class="mini-label">CONEXÕES</span><h2>Gente para conhecer</h2></div>
        <button type="button" data-live-action="refresh-people" aria-label="Atualizar sugestões">↻</button>
      </header>
      <div class="mobile-people-track" id="mobile-people-track"><div class="mobile-people-loading">Buscando novos repertórios...</div></div>`;
    pageContent.before(sectionNode);
    loadMobilePeople();
  }

  async function loadMobilePeople() {
    const track = document.querySelector("#mobile-people-track");
    if (!track) return;
    track.innerHTML = '<div class="mobile-people-loading">Buscando novos repertórios...</div>';
    try {
      const data = await requestJson("/api/v1/auth/creators/?page_size=6");
      const creators = (data.results || data || []).slice(0, 6);
      track.innerHTML = creators.length ? creators.map(user => `
        <article class="mobile-person-card">
          <a class="mobile-person-avatar" href="/perfil/${encodeURIComponent(user.username)}/">
            ${user.avatar_url ? `<img src="${escapeHtml(user.avatar_url)}" alt="">` : `<span>${escapeHtml((user.display_name || user.username || "P").slice(0, 2).toUpperCase())}</span>`}
          </a>
          <a class="mobile-person-copy" href="/perfil/${encodeURIComponent(user.username)}/">
            <strong>${escapeHtml(user.display_name || user.username)}</strong>
            <small>${escapeHtml(user.specialty || `@${user.username}`)}</small>
          </a>
          <button class="mini-follow ${user.is_following ? "following" : ""}" data-follow="${escapeHtml(user.username)}">${user.is_following ? "seguindo" : "seguir"}</button>
        </article>`).join("") : '<div class="mobile-people-loading">Novas conexões aparecem por aqui.</div>';
    } catch (_) {
      track.innerHTML = '<div class="mobile-people-loading">Não foi possível atualizar as sugestões agora.</div>';
    }
  }

  function connectEvents() {
    clearTimeout(live.reconnectTimer);
    if (live.eventsSocket && [WebSocket.OPEN, WebSocket.CONNECTING].includes(live.eventsSocket.readyState)) return;
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${scheme}://${location.host}/ws/events/`);
    live.eventsSocket = socket;
    socket.onmessage = event => {
      try { handleLiveEvent(JSON.parse(event.data)); } catch (_) { /* ignore malformed event */ }
    };
    socket.onclose = () => {
      if (live.eventsSocket === socket) live.reconnectTimer = setTimeout(connectEvents, 2500);
    };
  }

  async function waitForEventsSocket(timeoutMs = 5000) {
    connectEvents();
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      if (live.eventsSocket?.readyState === WebSocket.OPEN) return true;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error("A conexão de chamada ainda não está pronta. Tente novamente.");
  }

  function sendEvent(payload) {
    if (live.eventsSocket?.readyState !== WebSocket.OPEN) return false;
    live.eventsSocket.send(JSON.stringify(payload));
    return true;
  }

  function currentConversationId() {
    const active = document.querySelector(".conversation-item.active[data-conversation]");
    return active ? Number(active.dataset.conversation) : null;
  }

  function actorName(actor) {
    return actor?.display_name || actor?.username || "Alguém";
  }

  function activityAction(kind) {
    return {
      follow: "começou a seguir você",
      like: "curtiu sua publicação",
      comment: "comentou na sua publicação",
      repost: "compartilhou sua publicação",
      post: "publicou algo novo",
      call: "ligou para você",
      message: "enviou uma mensagem",
    }[kind] || "interagiu com você";
  }

  function notificationCopy(kind, actor) {
    return `${actorName(actor)} ${activityAction(kind)}.`;
  }

  async function showSystemNotification(title, body, url, options = {}) {
    if (!window.PulsoPWA?.showNotification) return;
    await window.PulsoPWA.showNotification(title, {
      body,
      url,
      tag: options.tag,
      renotify: options.renotify,
      requireInteraction: options.requireInteraction,
    }).catch(() => null);
  }

  function markActivityReadIfOpen() {
    if (section !== "notifications" || document.hidden) return;
    live.notificationCount = 0;
    renderBadges();
    setTimeout(() => requestJson("/api/v1/social/notifications/read_all/", { method: "POST" }).catch(() => null), 250);
  }

  function prependActivity(data) {
    if (section !== "notifications") return;
    const list = document.querySelector("#notifications");
    if (!list || list.querySelector(".page-loader")) return;
    if (list.querySelector(".empty-state")) list.innerHTML = "";
    const item = document.createElement("div");
    item.className = "notification-item unread live-arrival";
    const initials = (actorName(data.actor) || "P").split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
    const avatar = data.actor?.avatar_url
      ? `<span class="avatar"><img src="${escapeHtml(data.actor.avatar_url)}" alt=""></span>`
      : `<span class="avatar">${escapeHtml(initials)}</span>`;
    item.innerHTML = `${avatar}<p><strong>${escapeHtml(actorName(data.actor))}</strong> ${escapeHtml(activityAction(data.kind))}${data.post_excerpt ? `<br><small>“${escapeHtml(data.post_excerpt)}”</small>` : ""}</p><time>agora</time>`;
    list.prepend(item);
  }

  function handleLiveEvent(data) {
    if (data.type === "notification") {
      live.notificationCount += 1;
      renderBadges();
      prependActivity(data);
      const copy = notificationCopy(data.kind, data.actor);
      if (!document.hidden) toast(copy);
      else showSystemNotification("PULSO", copy, data.url || "/notificacoes/", { tag: `pulso-${data.kind || "activity"}` });
      markActivityReadIfOpen();
      return;
    }

    if (data.type === "message") {
      live.notificationCount += 1;
      const activeId = currentConversationId();
      const isReadingConversation = !document.hidden && section === "messages" && activeId === Number(data.conversation_id);
      if (!isReadingConversation) live.messageCount += 1;
      else requestJson(`/api/v1/chat/conversations/${data.conversation_id}/messages/?limit=20`).catch(() => null);
      renderBadges();
      const copy = `${actorName(data.actor)} enviou uma mensagem.`;
      if (!document.hidden && !isReadingConversation) toast(copy);
      if (document.hidden) showSystemNotification("Nova mensagem no PULSO", "Abra o PULSO para ver a mensagem.", data.url || "/mensagens/", { tag: `pulso-message-${data.conversation_id}`, renotify: true });
      markActivityReadIfOpen();
      return;
    }

    if (data.type === "incoming_call") {
      live.notificationCount += 1;
      renderBadges();
      receiveIncomingCall(data);
      showSystemNotification(
        `${data.kind === "video" ? "Videochamada" : "Ligação"} no PULSO`,
        `${actorName(data.actor)} está ligando.`,
        data.url || "/mensagens/",
        { tag: `pulso-call-${data.call_id}`, renotify: true, requireInteraction: true }
      );
      return;
    }

    if (data.type === "call_signal") handleCallSignal(data);
  }

  function callModal() { return document.querySelector("#call-modal"); }
  function setCallStatus(message) { const status = document.querySelector("#call-status"); if (status) status.textContent = message; }

  async function openLocalMedia(kind) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: kind === "video" });
    live.localStream = stream;
    const localVideo = document.querySelector("#local-video");
    if (localVideo) {
      localVideo.srcObject = stream;
      localVideo.hidden = kind !== "video";
    }
    return stream;
  }

  function createPeer(kind) {
    return requestJson("/api/v1/chat/ice-servers/").then(config => {
      const peer = new RTCPeerConnection(config);
      live.peer = peer;
      live.localStream?.getTracks().forEach(track => peer.addTrack(track, live.localStream));
      peer.ontrack = event => {
        const remote = document.querySelector("#remote-video");
        if (remote) remote.srcObject = event.streams[0];
      };
      peer.onicecandidate = event => {
        if (event.candidate) sendCallSignal({ candidate: event.candidate.toJSON?.() || event.candidate, kind });
      };
      peer.onconnectionstatechange = () => {
        if (peer.connectionState === "connected") setCallStatus("Na chamada");
        if (["failed", "closed"].includes(peer.connectionState)) cleanupCall(true);
      };
      return peer;
    });
  }

  function sendCallSignal(signal) {
    if (!live.conversationId) return false;
    return sendEvent({ type: "call.signal", conversation_id: live.conversationId, signal: { ...signal, call_id: live.callId } });
  }

  async function startLiveCall(kind) {
    const conversationId = currentConversationId();
    if (!conversationId) { toast("Abra uma conversa antes de ligar."); return; }
    try {
      await waitForEventsSocket();
      live.conversationId = conversationId;
      live.callKind = kind;
      await openLocalMedia(kind);
      const call = await requestJson(`/api/v1/chat/conversations/${conversationId}/calls/`, {
        method: "POST",
        body: JSON.stringify({ kind }),
      });
      live.callId = call.id;
      const modal = callModal();
      if (modal && !modal.open) modal.showModal();
      setCallStatus("Chamando...");
      const peer = await createPeer(kind);
      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      if (!sendCallSignal({ description: peer.localDescription, kind })) throw new Error("A sinalização da chamada foi interrompida.");
    } catch (error) {
      toast(error.name === "NotAllowedError" ? "Permita câmera e microfone para ligar." : error.message);
      cleanupCall(true);
    }
  }

  function receiveIncomingCall(data) {
    if (live.peer || live.incoming) return;
    live.incoming = data;
    live.callId = data.call_id;
    live.conversationId = Number(data.conversation_id);
    live.callKind = data.kind;
    document.querySelector("#incoming-call-card")?.remove();
    const card = document.createElement("section");
    card.id = "incoming-call-card";
    card.className = "incoming-call-card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-label", "Ligação recebida");
    card.innerHTML = `
      <div class="incoming-call-pulse"><i></i><i></i><i></i></div>
      <div class="incoming-call-copy"><small>${data.kind === "video" ? "VIDEOCHAMADA" : "LIGAÇÃO"}</small><strong>${escapeHtml(actorName(data.actor))}</strong><span>quer falar com você agora</span></div>
      <div class="incoming-call-actions"><button type="button" data-live-action="decline-call" aria-label="Recusar">×</button><button type="button" data-live-action="accept-call" aria-label="Atender">✓</button></div>`;
    document.body.append(card);
  }

  async function acceptIncomingCall() {
    const incoming = live.incoming;
    if (!incoming) return;
    document.querySelector("#incoming-call-card")?.remove();
    try {
      await waitForEventsSocket();
      await openLocalMedia(incoming.kind);
      const modal = callModal();
      if (modal && !modal.open) modal.showModal();
      setCallStatus("Conectando...");
      await createPeer(incoming.kind);
      await requestJson(`/api/v1/chat/calls/${incoming.call_id}/status/`, { method: "POST", body: JSON.stringify({ status: "active" }) });
      live.incoming = null;
      const queued = [...live.pendingSignals];
      live.pendingSignals.length = 0;
      for (const signal of queued) await applyCallSignal(signal);
    } catch (error) {
      toast(error.name === "NotAllowedError" ? "Permita câmera e microfone para atender." : error.message);
      await declineIncomingCall();
    }
  }

  async function declineIncomingCall() {
    const incoming = live.incoming;
    document.querySelector("#incoming-call-card")?.remove();
    if (incoming?.call_id) {
      await requestJson(`/api/v1/chat/calls/${incoming.call_id}/status/`, { method: "POST", body: JSON.stringify({ status: "declined" }) }).catch(() => null);
      sendCallSignal({ hangup: true, reason: "declined" });
    }
    cleanupCall(true);
  }

  async function applyCallSignal(signal) {
    if (signal.hangup) {
      cleanupCall(true);
      toast(signal.reason === "declined" ? "A ligação foi recusada." : "A ligação terminou.");
      return;
    }
    if (!live.peer) {
      live.pendingSignals.push(signal);
      return;
    }
    if (signal.description) {
      await live.peer.setRemoteDescription(signal.description);
      const queuedCandidates = [...live.pendingCandidates];
      live.pendingCandidates.length = 0;
      for (const candidate of queuedCandidates) await live.peer.addIceCandidate(candidate).catch(() => null);
      if (signal.description.type === "offer") {
        const answer = await live.peer.createAnswer();
        await live.peer.setLocalDescription(answer);
        sendCallSignal({ description: live.peer.localDescription, kind: live.callKind });
      }
      return;
    }
    if (signal.candidate) {
      if (live.peer.remoteDescription) await live.peer.addIceCandidate(signal.candidate).catch(() => null);
      else live.pendingCandidates.push(signal.candidate);
    }
  }

  function handleCallSignal(data) {
    const conversationId = Number(data.conversation_id);
    if (live.conversationId && conversationId !== Number(live.conversationId)) return;
    const signal = data.signal || {};
    if (signal.call_id && live.callId && Number(signal.call_id) !== Number(live.callId)) return;
    applyCallSignal(signal).catch(() => toast("Não foi possível completar a chamada."));
  }

  function cleanupCall(closeModal = true) {
    live.localStream?.getTracks().forEach(track => track.stop());
    live.peer?.close();
    live.localStream = null;
    live.peer = null;
    live.pendingCandidates.length = 0;
    live.pendingSignals.length = 0;
    document.querySelector("#incoming-call-card")?.remove();
    const modal = callModal();
    if (closeModal && modal?.open) modal.close();
    const localVideo = document.querySelector("#local-video");
    const remoteVideo = document.querySelector("#remote-video");
    if (localVideo) localVideo.srcObject = null;
    if (remoteVideo) remoteVideo.srcObject = null;
    live.callId = null;
    live.conversationId = null;
    live.callKind = null;
    live.incoming = null;
  }

  async function endLiveCall() {
    const callId = live.callId;
    sendCallSignal({ hangup: true, reason: "ended" });
    if (callId) {
      await requestJson(`/api/v1/chat/calls/${callId}/status/`, { method: "POST", body: JSON.stringify({ status: "ended" }) }).catch(() => null);
    }
    cleanupCall(true);
  }

  document.addEventListener("click", event => {
    const modal = callModal();
    if (modal && event.target === modal && modal.open && (live.peer || live.callId || live.incoming)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      endLiveCall();
      return;
    }

    const callButton = event.target.closest("[data-call]");
    if (callButton) {
      event.preventDefault();
      event.stopImmediatePropagation();
      startLiveCall(callButton.dataset.call);
      return;
    }

    const liveAction = event.target.closest("[data-live-action]");
    if (liveAction) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (liveAction.dataset.liveAction === "refresh-people") loadMobilePeople();
      if (liveAction.dataset.liveAction === "accept-call") acceptIncomingCall();
      if (liveAction.dataset.liveAction === "decline-call") declineIncomingCall();
      return;
    }

    const hangup = event.target.closest('[data-action="hangup"]');
    if (hangup && (live.peer || live.callId || live.incoming)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      endLiveCall();
    }
  }, true);

  window.addEventListener("pagehide", () => clearTimeout(live.reconnectTimer));

  ensureMobileLiveControls();
  ensureMobilePeopleSection();
  renderBadges();
  syncBadges();
  connectEvents();
})();
