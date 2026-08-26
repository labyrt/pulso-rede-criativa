(() => {
  "use strict";

  const nativeFetch = window.fetch.bind(window);
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

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

    const retryable = method === "GET" || method === "HEAD";
    const maxAttempts = retryable ? 2 : 1;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 18000);

      try {
        return await nativeFetch(input, { ...init, signal: controller.signal });
      } catch (error) {
        const timedOut = error?.name === "AbortError";
        const networkFailure = error instanceof TypeError;
        const canRetry = attempt < maxAttempts && (timedOut || networkFailure);

        if (canRetry) {
          await sleep(900);
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
