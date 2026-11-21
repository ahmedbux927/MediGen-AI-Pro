(() => {
  const $ = (id) => document.getElementById(id);

  const password = $("password");
  const toggle = $("toggle");
  if (password && toggle) {
    toggle.addEventListener("click", () => {
      const show = password.type === "password";
      password.type = show ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(show));
      toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
      toggle.querySelector("use").setAttribute("href", show ? "#i-eye-off" : "#i-eye");
      password.focus();
    });

    const caps = $("caps");
    const checkCaps = (e) => {
      if (caps && e.getModifierState) caps.hidden = !e.getModifierState("CapsLock");
    };
    password.addEventListener("keyup", checkCaps);
    password.addEventListener("keydown", checkCaps);
    password.addEventListener("blur", () => caps && (caps.hidden = true));
  }

  const toast = $("toast");
  let toastTimer;
  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
  };

  $("forgot")?.addEventListener("click", (e) => {
    e.preventDefault();
    showToast("Please contact your system administrator to reset your password.");
  });

  const form = $("loginForm");
  const submit = $("submitBtn");
  form?.addEventListener("submit", (e) => {
    const missing = [...form.querySelectorAll("input[required]")].find((input) => !input.value.trim());
    if (missing) {
      e.preventDefault();
      missing.closest(".field")?.classList.add("invalid");
      missing.focus();
      showToast("Please enter your username and password.");
      return;
    }
    submit?.classList.add("loading");
    submit?.setAttribute("aria-busy", "true");
  });
  form?.addEventListener("input", (e) => e.target.closest(".field")?.classList.remove("invalid"));

  const setTheme = (soft, save) => {
    document.body.classList.toggle("soft", soft);
    $("light")?.classList.toggle("selected", !soft);
    $("soft")?.classList.toggle("selected", soft);
    $("light")?.setAttribute("aria-pressed", String(!soft));
    $("soft")?.setAttribute("aria-pressed", String(soft));
    if (save) {
      try { localStorage.setItem("mgThemeMode", soft ? "dark" : "light"); localStorage.removeItem("mgTheme"); } catch (e) { }
    }
  };
  /* First paint follows the app choice when there is one, otherwise the
     computer's own light/dark setting (system), otherwise dark. */
  (() => {
    let saved = null;
    try { saved = localStorage.getItem("mgThemeMode") || localStorage.getItem("mgTheme"); } catch (e) { }
    const soft = saved === "dark" ? true
      : saved === "light" ? false
      : (window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)").matches : true);
    setTheme(soft, false);
  })();
  $("light")?.addEventListener("click", () => setTheme(false, true));
  $("soft")?.addEventListener("click", () => setTheme(true, true));

  const particles = document.querySelector(".particles");
  if (particles && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    for (let i = 0; i < 18; i++) {
      const dot = document.createElement("span");
      const size = 2 + Math.random() * 4;
      dot.style.cssText =
        `left:${Math.random() * 100}%;width:${size}px;height:${size}px;` +
        `animation-duration:${9 + Math.random() * 10}s;animation-delay:${-Math.random() * 15}s;` +
        `opacity:${0.25 + Math.random() * 0.45}`;
      particles.appendChild(dot);
    }
  }
})();
