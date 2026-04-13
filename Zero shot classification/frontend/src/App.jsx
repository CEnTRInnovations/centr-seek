// import React, { useState } from "react";
// import { scoreDocuments } from "./api";
// import "./styles.css"
// function ProgressBar({ value = 0 }) {
//   return (
//     <div className="progress-wrap" role="progressbar" aria-valuenow={Math.round(value)}>
//       <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
//     </div>
//   );
// }

// export default function App() {
//   const [urlsText, setUrlsText] = useState("");
//   const [file, setFile] = useState(null);
//   const [running, setRunning] = useState(false);
//   const [progressMsg, setProgressMsg] = useState("");
//   const [progressPct, setProgressPct] = useState(0);
//   const [result, setResult] = useState(null);
//   const [error, setError] = useState(null);

//   const handleFile = (e) => {
//     setFile(e.target.files[0] || null);
//   };

//   const handleRun = async () => {
//     setError(null);
//     setResult(null);
//     setProgressPct(0);
//     setProgressMsg("");

//     const urls = urlsText
//       .split(/\r?\n/)
//       .map((u) => u.trim())
//       .filter(Boolean);

//     if (!file && urls.length === 0) {
//       setError("Provide at least one URL or upload a single PDF/TXT.");
//       return;
//     }

//     try {
//       setRunning(true);
//       setProgressMsg("Uploading & starting scoring...");
//       setProgressPct(8);

//       // fire request
//       const json = await scoreDocuments({ urls, file });

//       setProgressMsg("Processing results...");
//       setProgressPct(60);

//       // small delay for UX
//       await new Promise((r) => setTimeout(r, 300));

//       setResult(json);
//       setProgressMsg("Done");
//       setProgressPct(100);
//     } catch (e) {
//       setError(e.message || String(e));
//       setProgressMsg("");
//       setProgressPct(0);
//     } finally {
//       setRunning(false);
//       // reset progress after a moment
//       setTimeout(() => setProgressPct(0), 1200);
//     }
//   };

//   const handleReset = () => {
//     setUrlsText("");
//     setFile(null);
//     setResult(null);
//     setError(null);
//     setProgressMsg("");
//     setProgressPct(0);
//   };

//   return (
//     <div className="page-bg">
//       <div className="container">
//         <header className="header">
//           <h1 className="title">Community-Engaged Document Scorer</h1>
//           <p className="subtitle">Paste article URLs or upload a PDF — get dimension-level engagement scores.</p>
//         </header>

//         <main className="card">
//           <div className="card-grid">
//             <section className="left">
//               <label className="label">Enter one URL per line</label>
//               <textarea
//                 className="textarea"
//                 rows={8}
//                 placeholder="https://example.com/article1\nhttps://example.com/article2"
//                 value={urlsText}
//                 onChange={(e) => setUrlsText(e.target.value)}
//                 disabled={running}
//               />
//             </section>

//             <aside className="right">
//               <label className="label">Or upload a single PDF / TXT</label>
//               <div className="filebox">
//                 <input id="fileInput" type="file" accept=".pdf,.txt" onChange={handleFile} />
//                 <div className="file-meta">
//                   <div className="file-name">{file ? file.name : "No file chosen"}</div>
//                   <div className="file-help">PDF or plain text. Max file size depends on server limits.</div>
//                 </div>
//               </div>

//               <div className="actions-vertical">
//                 <button className="btn primary" onClick={handleRun} disabled={running}>
//                   {running ? "Running…" : "Run Scoring"}
//                 </button>
//                 <button className="btn ghost" onClick={handleReset} disabled={running}>
//                   Reset
//                 </button>
//                 <a className="docs-link" href="#" onClick={(e) => e.preventDefault()}>
//                   How it works
//                 </a>
//               </div>
//             </aside>
//           </div>

//           <div className="status-row">
//             <div className="status-left">
//               {progressMsg && <div className="progress-caption">{progressMsg}</div>}
//               {progressMsg && <ProgressBar value={progressPct} />}
//             </div>
//             <div className="status-right">
//               {error && <div className="error-box">{error}</div>}
//             </div>
//           </div>

//           {result && (
//             <section className="results">
//               <h3>Results</h3>
//               <pre className="result-json">{JSON.stringify(result, null, 2)}</pre>
//               <a
//                 className="download"
//                 href={URL.createObjectURL(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }))}
//                 download="scoring_result.json"
//               >
//                 Download JSON
//               </a>
//             </section>
//           )}
//         </main>

//         <footer className="footer">
//           <small>Built for quick review — take care with large documents. Backend must be running at <code>/api/score</code>.</small>
//         </footer>
//       </div>
//     </div>
//   );
// }


import React, { useState } from "react";
import { scoreDocuments } from "./api";
import "./styles.css";

function ProgressBar({ value = 0 }) {
  return (
    <div className="progress-wrap" role="progressbar" aria-valuenow={Math.round(value)}>
      <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export default function App() {
  const [urlsText, setUrlsText] = useState("");
  const [file, setFile] = useState(null);
  const [running, setRunning] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");
  const [progressPct, setProgressPct] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFile = (e) => {
    setFile(e.target.files[0] || null);
  };

  const handleRun = async () => {
    setError(null);
    setResult(null);
    setProgressPct(0);
    setProgressMsg("");

    const urls = urlsText
      .split(/\r?\n/)
      .map((u) => u.trim())
      .filter(Boolean);

    if (!file && urls.length === 0) {
      setError("Provide at least one URL or upload a single PDF/TXT.");
      return;
    }

    try {
      setRunning(true);
      setProgressMsg("Uploading & starting scoring...");
      setProgressPct(8);

      // fire request
      const json = await scoreDocuments({ urls, file });

      setProgressMsg("Processing results...");
      setProgressPct(60);

      // small delay for UX
      await new Promise((r) => setTimeout(r, 300));

      setResult(json);
      setProgressMsg("Done");
      setProgressPct(100);
    } catch (e) {
      setError(e.message || String(e));
      setProgressMsg("");
      setProgressPct(0);
    } finally {
      setRunning(false);
      // reset progress after a moment
      setTimeout(() => setProgressPct(0), 1200);
    }
  };

  const handleReset = () => {
    setUrlsText("");
    setFile(null);
    setResult(null);
    setError(null);
    setProgressMsg("");
    setProgressPct(0);
  };

  return (
    <div className="page-bg">
      <div className="container">
        <header className="header">
          <h1 className="title">Community-Engaged Document Scorer</h1>
          <p className="subtitle">
            Paste article URLs or upload a PDF — get dimension-level engagement scores.
          </p>
        </header>

        <main className="card">
          <div className="card-grid">
            <section className="left">
              <label className="label">Enter one URL per line</label>
              <textarea
                className="textarea"
                rows={8}
                placeholder="https://example.com/article1\nhttps://example.com/article2"
                value={urlsText}
                onChange={(e) => setUrlsText(e.target.value)}
                disabled={running}
              />
            </section>

            <aside className="right">
              <label className="label">Or upload a single PDF / TXT</label>
              <div className="filebox">
                <input
                  id="fileInput"
                  type="file"
                  accept=".pdf,.txt"
                  onChange={handleFile}
                  className="hidden"
                  style={{ display: "none" }}
                />
                <label
                  htmlFor="fileInput"
                  className = "choose-file-btn"
                  // className="file-select-box cursor-pointer w-full border-2 border-blue-400 border-dashed rounded-lg p-4 text-center hover:bg-blue-50 transition"
                > 
                  {file ? (
                    <span className="text-blue-600 font-medium">{file.name}</span>
                  ) : (
                    <span className="text-gray-500">Click to upload a file</span>
                  )}
                </label>
                <div className=" text-sm text-gray-400 mt-1 py-4.5" style={{ padding: "10px" }}>
                  PDF or plain text. Max file size depends on server limits.
                </div>
              </div>

              <div className="actions-vertical mt-4">
                <button className="btn primary" onClick={handleRun} disabled={running}>
                  {running ? "Running…" : "Run Scoring"}
                </button>
                <button className="btn ghost" onClick={handleReset} disabled={running}>
                  Reset
                </button>
                <a className="docs-link" href="#" onClick={(e) => e.preventDefault()}>
                  How it works
                </a>
              </div>
            </aside>
          </div>

          <div className="status-row">
            <div className="status-left">
              {progressMsg && <div className="progress-caption">{progressMsg}</div>}
              {progressMsg && <ProgressBar value={progressPct} />}
            </div>
            <div className="status-right">{error && <div className="error-box">{error}</div>}</div>
          </div>

          {result && (
            <section className="results">
              <h3>Results</h3>
              <pre className="result-json">{JSON.stringify(result, null, 2)}</pre>
              <a
                className="download"
                href={URL.createObjectURL(
                  new Blob([JSON.stringify(result, null, 2)], { type: "application/json" })
                )}
                download="scoring_result.json"
              >
                Download JSON
              </a>
            </section>
          )}
        </main>

        <footer className="footer">
          <small>
            Slow run for large docs. Backend endpoint running at{" "}
            <code>/api/score</code>.
          </small>
        </footer>
      </div>
    </div>
  );
}
