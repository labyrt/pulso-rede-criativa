(() => {
  "use strict";

  const shell = document.querySelector("#app-shell");
  if (!shell) return;

  const section = document.body.dataset.section;
  const reloadKey = "pulso:lifecycle-reload-at";
  const reloadWindowMs = 120000;
  const stallDelayMs = 9000;
  const healthTimeoutMs = 8000;
  const retryDelayMs = 5000;

  let stallTimer = null;
  let retryTimer = null;
  let recovering = false;
  let hiddenAt = document.hidden ? Date.now() : null;

  function loader() {
    return document.querySelector("#page-content .page-loader");
  }

  function clearTimer(timer) {
    if (timer) window.clearTimeout(timer);
  }

  function clearRecoveryStateWhenReady() {
    if (loader()) return;
    clearTimer(stallTimer);
    clearTimer(retryTimer);
    stallTimer = null;
    retryTimer = null;
    recovering = false;
    sessionStorage.removeItem(reloadKey);
  }

  function lastReloadAt() {
    const value = Number(sessionStorage.getItem(reloadKey) || 0);
    return Number.isFinite(value) ? value : 0;
  }

  function reloadOnce() {
    const now = Date.now();
    if (now - lastReloadAt() < reloadWindowMs) return false;
    sessionStorage.setItem(reloadKey, String(now));
    window.location.reload();
    return true;
  }

  function showRetryState() {
    const currentLoader = loader();
    if (!currentLoader || document.querySelector("[data-pulso-recovery]")) return;

    const retry = document.createElement("div");
    retry.dataset.pulsoRecovery = "1";
    retry.className = "empty-state";
    retry.innerHTML = `
      <div>
        <div class="empty-orb">↻</div>
        <h2>O PULSO demorou para acordar.</h2>
        <p>O servidor gratuito já foi acionado. Tente novamente para carregar seu feed.</p>
        <button type="button" class="button button--ink" data-pulso-retry>Tentar novamente</button>
      </div>`;

    currentLoader.replaceWith(retry);
    retry.querySelector("[data-pulso-retry]")?.addEventListener("click", () => {
      sessionStorage.removeItem(reloadKey);
      window.location.reload();
    });
  }

  async function healthIsReady() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), healthTimeoutMs);
    try {
      const response = await fetch(`/health/?_pulso=${Date.now()}`, {
        method: "GET",
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      return response.ok;
    } catch (_) {
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function scheduleRetry() {
    clearTimer(retryTimer);
    retryTimer = window.setTimeout(() => recoverStalledLoader(), retryDelayMs);
  }

  async function recoverStalledLoader() {
    if (recovering || document.hidden || !loader()) return;
    recovering = true;

    const ready = await healthIsReady();
    recovering = false;

    if (!loader()) {
      clearRecoveryStateWhenReady();
      return;
    }

    if (ready) {
      if (!reloadOnce()) showRetryState();
      return;
    }

    scheduleRetry();
  }

  function armRecovery() {
    if (!loader() || document.hidden) return;
    clearTimer(stallTimer);
    stallTimer = window.setTimeout(() => recoverStalledLoader(), stallDelayMs);
  }

  const observer = new MutationObserver(() => {
    if (loader()) armRecovery();
    else clearRecoveryStateWhenReady();
  });
  observer.observe(document.querySelector("#page-content"), { childList: true, subtree: true });

  window.addEventListener("pageshow", event => {
    if (event.persisted) {
      if (!reloadOnce()) armRecovery();
      return;
    }
    armRecovery();
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      hiddenAt = Date.now();
      return;
    }

    const hiddenFor = hiddenAt ? Date.now() - hiddenAt : 0;
    hiddenAt = null;
    if (loader() && hiddenFor >= 15000) recoverStalledLoader();
    else armRecovery();
  });

  window.addEventListener("online", () => {
    if (loader()) recoverStalledLoader();
  });

  // On a fresh navigation the document is only served after Render has woken.
  // On mobile BFCache/tab restoration, this timer detects the stale shell that
  // can otherwise keep showing a spinner while no feed request reaches Django.
  if (section === "feed") armRecovery();
})();
