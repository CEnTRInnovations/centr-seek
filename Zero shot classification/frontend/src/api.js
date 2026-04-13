const BASE = import.meta.env.PROD ? "" : "http://127.0.0.1:8000";

export async function scoreDocuments({ urls = [], file = null }) {
  try {
    console.log("scoreDocuments called", { urls, fileName: file?.name });

    const form = new FormData();
    form.append("urls", JSON.stringify(urls || []));
    if (file) form.append("file", file);

    console.log("FormData prepared, starting fetch to", `${BASE}/api/score`);

    const resp = await fetch(`${BASE}/api/score`, {
      method: "POST",
      body: form,
      // DO NOT set Content-Type header manually for FormData
    });

    console.log("fetch completed, status:", resp.status, resp.statusText);

    if (!resp.ok) {
      const txt = await resp.text();
      console.error("server returned error body:", txt);
      throw new Error(txt || resp.statusText);
    }

    const json = await resp.json();
    console.log("server JSON:", json);
    return json;
  } catch (err) {
    console.error("scoreDocuments error:", err);
    throw err;
  }
}
