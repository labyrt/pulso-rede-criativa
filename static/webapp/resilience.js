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

  window.fetch = async function pulsoFetch(input, init = {}) {
    const url = requestUrl(input);
    const method = String(init.method || (typeof input !== "string" && input.method) || "GET").toUpperCase();
    const isSameOriginApi = Boolean(url && url.origin === window.location.origin && url.pathname.startsWith("/api/"));

    // Leave third-party requests and callers with their own cancellation policy untouched.
    if (!isSameOriginApi || init.signal) return nativeFetch(input, init);

    // Mutating requests are intentionally never retried or force-aborted here. A POST,
    // PATCH or DELETE may already have reached the server even if the browser loses
    // the response; repeating it could duplicate a post, comment, Pix intent or action.
    const retryable = method === "GET" || method === "HEAD";
    if (!retryable) return nativeFetch(input, init);

    const maxAttempts = 2;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const controller = new AbortController();
      // Render Free can take longer than a normal request while waking. Two bounded
      // attempts allow the instance to wake without leaving the interface spinning forever.
      const timeout = window.setTimeout(() => controller.abort(), 32000);

      try {
        const response = await nativeFetch(input, { ...init, signal: controller.signal });
        const canRetryStatus = attempt < maxAttempts && transientStatuses.has(response.status);

        if (canRetryStatus) {
          try { await response.body?.cancel(); } catch (_) {}
          await sleep(700);
          continue;
        }

        return response;
      } catch (error) {
        const timedOut = error?.name === "AbortError";
        const networkFailure = error instanceof TypeError;
        const canRetry = attempt < maxAttempts && (timedOut || networkFailure);

        if (canRetry) {
          await sleep(700);
          continue;
        }

        if (timedOut) {
          const timeoutError = new Error("A conexão com o PULSO demorou mais que o esperado. Tente novamente em alguns segundos.");
          timeoutError.name = "PulsoTimeoutError";
          throw timeoutError;
        }

        if (networkFailure && navigator.onLine === false) {
          throw new Error("Você está sem conexão com a internet. Reconecte e tente novamente.");
        }

        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    }

    throw new Error("Não foi possível conectar ao PULSO agora. Tente novamente.");
  };
})();
