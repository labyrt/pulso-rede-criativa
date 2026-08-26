(() => {
  "use strict";

  const nativeFetch = window.fetch.bind(window);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const transientStatuses = new Set([502, 503, 504]);

  function requestUrl(input) {
    try {
      return new URL(typeof input === "string" ? input : input.url, window.location.href);
    } catch (_) {
      return null;
    }
  }

  function showConnectionBanner(message) {
    let banner = document.getElementById("pulso-connection-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "pulso-connection-banner";
      banner.setAttribute("role", "alert");
      Object.assign(banner.style, {
        position: "fixed",
        left: "16px",
        right: "16px",
        bottom: "88px",
        zIndex: "9999",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "12px",
        padding: "14px 16px",
        borderRadius: "16px",
        background: "#f4f3ef",
        color: "#111214",
        boxShadow: "0 12px 34px rgba(0,0,0,.22)",
        fontSize: "14px",
        lineHeight: "1.35"
      });
      const text = document.createElement("span");
      text.dataset.connectionMessage = "1";
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Tentar de novo";
      Object.assign(button.style, {
        flex: "0 0 auto",
        border: "0",
        borderRadius: "999px",
        padding: "9px 12px",
        background: "#0b0b0c",
        color: "#fff",
        fontWeight: "700"
      });
      button.addEventListener("click", () => window.location.reload());
      banner.append(text, button);
      document.body.append(banner);
    }
    const text = banner.querySelector("[data-connection-message]");
    if (text) text.textContent = message;
  }

  window.fetch = async function pulsoFetch(input, init = {}) {
    const url = requestUrl(input);
    const method = String(init.method || (typeof input !== "string" && input.method) || "GET").toUpperCase();
    const isSameOriginApi = Boolean(url && url.origin === window.location.origin && url.pathname.startsWith("/api/"));

    // Requests outside the PULSO API and callers with their own cancellation policy stay untouched.
    if (!isSameOriginApi || init.signal) return nativeFetch(input, init);

    // Never retry or force-abort mutating requests. A lost response does not prove that
    // the server failed to persist the action, so replaying it could duplicate user data.
    const retryable = method === "GET" || method === "HEAD";
    if (!retryable) return nativeFetch(input, init);

    // The first window covers a normal Render Free cold start. A short second attempt is
    // reserved for a transient gateway/network failure. This caps the UI wait near 30s,
    // instead of leaving the feed looking frozen for more than a minute.
    const timeouts = [20000, 9000];

    for (let attempt = 0; attempt < timeouts.length; attempt += 1) {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), timeouts[attempt]);

      try {
        const response = await nativeFetch(input, { ...init, signal: controller.signal });
        const transient = transientStatuses.has(response.status);
        if (transient && attempt + 1 < timeouts.length) {
          try { await response.body?.cancel(); } catch (_) {}
          await sleep(650);
          continue;
        }
        if (transient) {
          showConnectionBanner("O servidor demorou para responder. Recarregue para tentar novamente.");
        }
        return response;
      } catch (error) {
        const timedOut = error?.name === "AbortError";
        const networkFailure = error instanceof TypeError;
        const canRetry = attempt + 1 < timeouts.length && (timedOut || networkFailure);

        if (canRetry) {
          await sleep(650);
          continue;
        }

        if (navigator.onLine === false) {
          showConnectionBanner("Seu celular está sem conexão com a internet.");
          throw new Error("Você está sem conexão com a internet. Reconecte e tente novamente.");
        }

        if (timedOut || networkFailure) {
          showConnectionBanner("Não conseguimos carregar esta parte do PULSO. Toque em “Tentar de novo”.");
        }

        if (timedOut) {
          const timeoutError = new Error("A conexão demorou mais que o esperado. Tente novamente.");
          timeoutError.name = "PulsoTimeoutError";
          throw timeoutError;
        }

        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }

    showConnectionBanner("Não conseguimos carregar esta parte do PULSO. Tente novamente.");
    throw new Error("Não foi possível conectar ao PULSO agora. Tente novamente.");
  };
})();
