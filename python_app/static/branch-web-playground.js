(function () {
  "use strict";

  const html = document.getElementById("web-html");
  const css = document.getElementById("web-css");
  const js = document.getElementById("web-js");
  const preview = document.getElementById("web-preview");
  const run = document.getElementById("web-run");
  const reset = document.getElementById("web-reset");
  if (!html || !css || !js || !preview || !run || !reset) return;

  const initial = [html.value, css.value, js.value];
  const closeTag = (source, name) => source.replace(new RegExp(`<\\/${name}`, "gi"), `<\\\\/${name}`);
  const render = () => {
    preview.srcdoc = [
      "<!doctype html><html><head>",
      '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'">',
      `<style>${closeTag(css.value, "style")}</style></head><body>`,
      html.value,
      `<script>${closeTag(js.value, "script")}<\/script></body></html>`
    ].join("");
  };

  run.addEventListener("click", render);
  reset.addEventListener("click", () => {
    [html.value, css.value, js.value] = initial;
    render();
  });
  render();
})();
