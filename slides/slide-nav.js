(function () {
  const cfg = window.SLIDE_CONFIG || { pageOrder: [] };
  const path = window.location.pathname.replace(/\\/g, "/");
  const currentFile = path.split("/").pop();
  const pages = cfg.pageOrder || [];
  const index = pages.findIndex(p => p.file === currentFile);
  const prev = index > 0 ? pages[index - 1] : null;
  const next = index >= 0 && index < pages.length - 1 ? pages[index + 1] : null;

  function go(page) {
    if (!page) return;
    window.location.href = page.file;
  }

  function createButton(label, className, page) {
    const btn = document.createElement("button");
    btn.className = `nav-btn ${className || ""}`.trim();
    btn.textContent = label;
    btn.type = "button";
    if (!page) {
      btn.disabled = true;
    } else {
      btn.addEventListener("click", () => go(page));
    }
    return btn;
  }

  const topbarRight = document.getElementById("topbar-right");
  if (topbarRight) {
    topbarRight.prepend(createButton("→", "next-btn", next));
    topbarRight.prepend(createButton("←", "prev-btn", prev));
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft" && prev) {
      go(prev);
    } else if (e.key === "ArrowRight" && next) {
      go(next);
    }
  });
})();

