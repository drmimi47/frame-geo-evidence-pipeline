// A portable JSON manifest and pre-rendered PDF pages, served by the existing /static mount.
const manifestURL = new URL("./documents/document.json", import.meta.url);

export async function renderDocument(main, research) {
  const article = document.createElement("article");
  article.className = "document-pages";
  article.setAttribute("aria-label", "Reconstruction");
  const status = document.createElement("p");
  status.className = "empty";
  status.setAttribute("role", "status");
  status.textContent = "Loading document…";
  article.append(status);
  main.replaceChildren(article);
  research.replaceChildren();

  try {
    const response = await fetch(manifestURL, { cache: "no-cache" });
    if (!response.ok) throw new Error("Document unavailable.");
    const data = await response.json();
    if (typeof data.title !== "string" || !Array.isArray(data.pages) || !data.pages.length) {
      throw new Error("Document has no pages.");
    }
    // Validate before building the page; only assets from this document directory are accepted.
    const pages = data.pages.map((page) => {
      const url = new URL(page.src, manifestURL);
      if (url.origin !== manifestURL.origin || !url.pathname.startsWith(new URL("./", manifestURL).pathname) ||
          !Number.isInteger(page.width) || page.width <= 0 || !Number.isInteger(page.height) || page.height <= 0) {
        throw new Error("Invalid document page.");
      }
      return { ...page, url };
    });
    // Switching views while the manifest is loading must not overwrite the new view.
    if (!article.isConnected) return;
    renderResearch(research, data.research);
    const header = document.createElement("header");
    const title = document.createElement("h1");
    title.textContent = data.title;
    header.append(title);
    if (data.subtitle) {
      const subtitle = document.createElement("p");
      subtitle.className = "document-subtitle";
      subtitle.textContent = data.subtitle;
      header.append(subtitle);
    }
    article.replaceChildren(header);
    pages.forEach((page, index) => {
      const figure = document.createElement("figure");
      figure.className = "document-page";
      const img = document.createElement("img");
      img.src = page.url.href;
      img.alt = `${data.title} — page ${index + 1}`;
      img.width = page.width;
      img.height = page.height;
      img.loading = index === 0 ? "eager" : "lazy";
      img.decoding = "async";
      img.addEventListener("error", () => {
        const message = document.createElement("p");
        message.className = "empty";
        message.textContent = `Page ${index + 1} could not be loaded. Reload to try again.`;
        figure.replaceChildren(message);
      }, { once: true });
      figure.append(img);
      article.append(figure);
    });
  } catch (error) {
    if (article.isConnected) status.textContent = `${error.message} Reload to try again.`;
  }
}

function renderResearch(panel, data) {
  if (!data || typeof data.description !== "string") return;
  const content = document.createElement("div");
  content.className = "research-content";
  const section = (label, text) => {
    const heading = document.createElement("h2");
    heading.textContent = label;
    content.append(heading);
    if (text) {
      const paragraph = document.createElement("p");
      paragraph.textContent = text;
      content.append(paragraph);
    }
  };
  section("Research", data.description);
  if (data.site) section("Site", data.site);
  if (Array.isArray(data.photograph_years)) section("Source photographs", data.photograph_years.join(" & "));
  if (Array.isArray(data.method) && data.method.length) {
    section("Method");
    const list = document.createElement("ol");
    for (const step of data.method) {
      const item = document.createElement("li");
      item.textContent = step;
      list.append(item);
    }
    content.append(list);
  }
  panel.replaceChildren(content);
}
