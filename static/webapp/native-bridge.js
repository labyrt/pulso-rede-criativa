(() => {
  "use strict";

  const android = window.PulsoAndroid;

  if (android) {
    const widgetButtons = [...document.querySelectorAll("[data-native-widget]")];

    if (typeof android.requestPinWidget === "function") {
      widgetButtons.forEach(button => {
        button.hidden = false;
        button.addEventListener("click", event => {
          event.preventDefault();
          event.stopPropagation();
          try {
            android.requestPinWidget();
          } catch (_) {
            // Native bridge is progressive enhancement only.
          }
        });
      });
    }

    const syncWidgetSummary = async () => {
      if (typeof android.updateWidgetSummary !== "function") return;
      try {
        const response = await fetch("/api/v1/widget/summary/", {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        if (response.ok) {
          const payload = await response.json();
          android.updateWidgetSummary(JSON.stringify(payload));
        } else if (response.status === 401 || response.status === 403) {
          android.clearWidgetSummary?.();
        }
      } catch (_) {
        // Keep the last privacy-safe summary when the network is temporarily unavailable.
      }
    };

    document.querySelectorAll("form[data-native-social-provider]").forEach(form => {
      form.addEventListener("submit", event => {
        if (typeof android.startSocialLogin !== "function") return;
        const provider = form.dataset.nativeSocialProvider;
        if (!provider) return;
        event.preventDefault();
        try {
          android.startSocialLogin(provider);
        } catch (_) {
          form.submit();
        }
      });
    });

    syncWidgetSummary();
    window.addEventListener("focus", syncWidgetSummary);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") syncWidgetSummary();
    });
    window.setInterval(() => {
      if (document.visibilityState === "visible") syncWidgetSummary();
    }, 60_000);
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get("composer") === "1") {
    window.setTimeout(() => {
      document.querySelector('[data-action="open-composer"]')?.click();
      params.delete("composer");
      const query = params.toString();
      history.replaceState({}, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
    }, 120);
  }
})();
