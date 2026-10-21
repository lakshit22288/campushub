(function () {
  "use strict";

  if (!["localhost", "127.0.0.1"].includes(window.location.hostname)) return;

  const themes = [
    { id: "balanced", name: "Balanced — DM Sans + Space Grotesk" },
    { id: "friendly", name: "Friendly — Plus Jakarta Sans + Outfit" },
    { id: "editorial", name: "Editorial — Manrope + Playfair Display" },
    { id: "precise", name: "Precise — Inter + Sora" },
    { id: "open", name: "Open — Work Sans + Urbanist" },
  ];
  const storageKey = "campushub-font-preview";
  const savedTheme = window.localStorage.getItem(storageKey);
  const initialTheme = themes.some((theme) => theme.id === savedTheme)
    ? savedTheme
    : "editorial";

  function applyTheme(themeId) {
    document.documentElement.dataset.fontTheme = themeId;
    window.localStorage.setItem(storageKey, themeId);
  }

  applyTheme(initialTheme);

  const dock = document.createElement("details");
  dock.className = "font-preview-dock";
  dock.open = true;

  const title = document.createElement("summary");
  title.textContent = "Try 5 font pairings";

  const content = document.createElement("div");
  content.className = "font-preview-content";

  const label = document.createElement("label");
  label.textContent = "Choose a style";

  const select = document.createElement("select");
  select.setAttribute("aria-label", "Choose a font pairing");
  themes.forEach((theme) => {
    const option = document.createElement("option");
    option.value = theme.id;
    option.textContent = theme.name;
    select.appendChild(option);
  });
  select.value = initialTheme;
  select.addEventListener("change", () => applyTheme(select.value));
  label.appendChild(select);

  const sample = document.createElement("div");
  sample.className = "font-preview-sample";
  const sampleHeading = document.createElement("strong");
  sampleHeading.textContent = "Find your people.";
  const sampleBody = document.createElement("span");
  sampleBody.textContent = "Learn, share and build together on campus.";
  sample.append(sampleHeading, sampleBody);

  content.append(label, sample);
  dock.append(title, content);
  document.body.appendChild(dock);
})();
