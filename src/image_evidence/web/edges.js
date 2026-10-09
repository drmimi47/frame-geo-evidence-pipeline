// Filmstrip edge shadings (app.js dress), made off the main thread so switching to the Filmstrip never stalls:
// each thumbnail's outermost columns (SLIT_ROWS colours a side), and for each strip the two shadings from its
// own edge into its neighbour's. Asked for one strip at a time: { key, prev, own, next } (thumbnail URLs,
// "" for no neighbour); answers { key, bl, br } (CSS urls of small PNGs) or { key, error }. Blob URLs made here
// (they stay valid while this worker runs, which is as long as the page): a blob sent to the page costs it far
// more to receive than the image cost to make, and a data URL costs it far more to style.
const SLIT_ROWS = 48, SHADE_COLS = 16;
const edges = new Map(); // thumbnail URL -> the promise of its { l, r } edge columns (RGBA)

function edgesOf(url) {
  if (!url) return Promise.resolve(null);
  if (!edges.has(url)) edges.set(url, (async () => {
    const img = await createImageBitmap(await (await fetch(url)).blob());
    const w = img.width, h = img.height, k = Math.max(1, Math.round(w / 50)), in1 = Math.round(w / 100);
    const g = new OffscreenCanvas(2, SLIT_ROWS).getContext("2d", { willReadFrequently: true });
    g.drawImage(img, in1, 0, k, h, 0, 0, 1, SLIT_ROWS);
    g.drawImage(img, w - in1 - k, 0, k, h, 1, 0, 1, SLIT_ROWS);
    img.close();
    const d = g.getImageData(0, 0, 2, SLIT_ROWS).data, col = (x) => d.filter((_, j) => (j >> 2) % 2 === x);
    return { l: col(0), r: col(1) };
  })().catch((e) => { edges.delete(url); throw e; }));
  return edges.get(url);
}
const mix = (a, b) => (b ? a.map((v, j) => (v + b[j]) >> 1) : a);
async function shade(a, b) { // column a shading into column b, as a CSS url
  const px = new Uint8ClampedArray(4 * SHADE_COLS * SLIT_ROWS);
  for (let y = 0; y < SLIT_ROWS; y++)
    for (let x = 0; x < SHADE_COLS; x++)
      for (let ch = 0, f = x / (SHADE_COLS - 1); ch < 4; ch++)
        px[4 * (y * SHADE_COLS + x) + ch] = a[4 * y + ch] + (b[4 * y + ch] - a[4 * y + ch]) * f;
  const c = new OffscreenCanvas(SHADE_COLS, SLIT_ROWS);
  c.getContext("2d").putImageData(new ImageData(px, SHADE_COLS, SLIT_ROWS), 0, 0);
  return `url("${URL.createObjectURL(await c.convertToBlob())}")`;
}

onmessage = async ({ data: { key, prev, own, next } }) => {
  try {
    const [p, o, n] = await Promise.all([edgesOf(prev), edgesOf(own), edgesOf(next)]);
    const [bl, br] = await Promise.all([shade(mix(o.l, p?.r), o.l), shade(o.r, mix(o.r, n?.l))]);
    postMessage({ key, bl, br });
  } catch {
    postMessage({ key, error: true });
  }
};
