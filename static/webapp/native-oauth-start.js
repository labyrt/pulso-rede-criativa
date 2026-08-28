(() => {
  "use strict";
  const form = document.getElementById("native-oauth-form");
  if (!form) return;
  window.setTimeout(() => form.requestSubmit(), 80);
})();
