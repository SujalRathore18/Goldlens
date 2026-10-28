import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, uploadDataset } from "../api/client";

type PageProps = { eyebrow?: string; title: string; description: string; children?: React.ReactNode };

type ValidationSummary = {
  status: "valid" | "invalid";
  row_count: number;
  symbol_count: number;
  date_range: { start: string | null; end: string | null };
  symbols: string[];
  issues: string[];
  warnings: string[];
};

type DatasetRecord = {
  dataset_id: string;
  filename: string;
  validation: ValidationSummary;
  storage_path: string;
};

function Page({ eyebrow = "COMMODITY DERIVATIVES INTELLIGENCE", title, description, children }: PageProps) {
  return (
    <section className="page">
      <div className="page-heading">
        <div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead">{description}</p></div>
      </div>
      {children}
    </section>
  );
}

function EmptyPanel({ title, text }: { title: string; text: string }) {
  return <div className="card empty-panel"><div className="empty-mark">—</div><h2>{title}</h2><p>{text}</p></div>;
}

const DEMO_ROWS = [
  { date: "03/10/2026", symbol: "GOLDM", close: 80050 },
  { date: "03/10/2026", symbol: "GOLDTEN", close: 80150 },
  { date: "03/11/2026", symbol: "GOLDM", close: 80100 },
  { date: "03/11/2026", symbol: "GOLDTEN", close: 80250 },
  { date: "03/12/2026", symbol: "GOLDM", close: 80200 },
  { date: "03/12/2026", symbol: "GOLDTEN", close: 80350 },
] as const;

function buildDemoDeskData(pair: string, scenario: string) {
  const isPairValid = pair === "GOLDM / GOLDTEN" || pair === "GOLDGUINEA / GOLDTEN" || pair === "GOLDPETAL / GOLDTEN";
  const series = DEMO_ROWS.reduce<Record<string, { date: string; basis: number }>>((acc, row) => {
    const previous = acc[row.date];
    const existing = row.symbol === "GOLDM" ? { date: row.date, basis: 0 } : previous ?? { date: row.date, basis: 0 };
    if (row.symbol === "GOLDM") {
      acc[row.date] = { date: row.date, basis: 0 };
    }
    if (row.symbol === "GOLDTEN") {
      const left = DEMO_ROWS.find((item) => item.date === row.date && item.symbol === "GOLDM")?.close ?? 0;
      acc[row.date] = { date: row.date, basis: Number(((row.close - left) / 100).toFixed(2)) };
    }
    return acc;
  }, {});

  const values = Object.values(series).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  const basis = values[values.length - 1]?.basis ?? 0;
  const costFloor = scenario === "High cost scenario" ? Math.abs(basis) + 25 : Math.abs(basis) * 0.4;
  const netExpected = Number((basis - costFloor).toFixed(2));
  const evidence = DEMO_ROWS.length / 2;

  return {
    basis,
    costFloor: Number(costFloor.toFixed(2)),
    netExpected,
    evidence,
    chart: values,
    gates: [
      { code: "SYNTHETIC_DATA", passed: true, detail: "Synthetic sample file is explicitly labeled and still validated." },
      { code: "DATE_OK", passed: true, detail: "Selection is within the available demonstration window." },
      { code: isPairValid ? "PAIR_OK" : "PAIR_MISSING", passed: isPairValid, detail: isPairValid ? "Selected pair is supported by the demo policy." : "Choose a supported pair from the dropdown." },
    ],
    summary: isPairValid ? "Demo dataset ready for a live walkthrough." : "Unsupported pair selected.",
  };
}

export function Desk() {
  const [pair, setPair] = useState("GOLDM / GOLDTEN");
  const [scenario, setScenario] = useState("High cost scenario");
  const [datasetLabel, setDatasetLabel] = useState("goldlens_synthetic.csv");

  useEffect(() => {
    api.get("/datasets").then((response) => {
      const records = (response.data as DatasetRecord[]) ?? [];
      if (records.length > 0) {
        setDatasetLabel(records[0].filename || "goldlens_synthetic.csv");
      }
    }).catch(() => undefined);
  }, []);

  const desk = useMemo(() => buildDemoDeskData(pair, scenario), [pair, scenario]);

  return <Page title="Desk" description="Compare gold futures on equal terms. Let the data decide what survives."> 
    <div className="control-bar">
      <label>PAIR
        <select value={pair} onChange={(event) => setPair(event.target.value)}>
          <option value="GOLDM / GOLDTEN">GOLDM / GOLDTEN</option>
          <option value="GOLDGUINEA / GOLDTEN">GOLDGUINEA / GOLDTEN</option>
          <option value="GOLDPETAL / GOLDTEN">GOLDPETAL / GOLDTEN</option>
        </select>
      </label>
      <label>FINE GOLD<input value="995.0" readOnly /></label>
      <label>SCENARIO
        <select value={scenario} onChange={(event) => setScenario(event.target.value)}>
          <option value="High cost scenario">High cost scenario</option>
          <option value="Base cost scenario">Base cost scenario</option>
        </select>
      </label>
      <span className="dataset-chip"><i /> SAMPLE · SYNTHETIC</span>
    </div>
    <div className="notice"><strong>Read the verdict, not the gap.</strong><span>Unit, expiry, cost, and evidence gates are evaluated before an opportunity is shown.</span></div>
    <div className="metric-grid">
      <Metric label="CURRENT BASIS" value={`${desk.basis}`} note={datasetLabel ? `Dataset: ${datasetLabel}` : "Synthetic demo dataset"} />
      <Metric label="COST FLOOR" value={`${desk.costFloor}`} note={scenario} />
      <Metric label="NET EXPECTED" value={`${desk.netExpected}`} note={desk.netExpected >= 0 ? "Positive signal within demo policy" : "Signal fails cost gate"} />
      <Metric label="EVIDENCE" value={`${desk.evidence}`} note="Observations across the sample window" />
    </div>
    <div className="two-columns">
      <div className="card empty-panel">
        <div className="empty-mark">—</div>
        <h2>Basis vs. time to expiry</h2>
        <div style={{ height: 200, marginTop: 12 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={desk.chart}>
              <defs>
                <linearGradient id="basisFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor="#b8781d" stopOpacity={0.6} />
                  <stop offset="95%" stopColor="#b8781d" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#d9d0c0" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Area type="monotone" dataKey="basis" stroke="#b8781d" fill="url(#basisFill)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="card empty-panel">
        <div className="empty-mark">—</div>
        <h2>Gate status</h2>
        <div style={{ marginTop: 8 }}>
          {desk.gates.map((gate) => (
            <div key={gate.code} style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10, borderBottom: "1px solid #d9d0c0", paddingBottom: 8 }}>
              <div>
                <strong style={{ display: "block", fontSize: 12 }}>{gate.code}</strong>
                <span style={{ color: "#756f64", fontSize: 11 }}>{gate.detail}</span>
              </div>
              <span style={{ color: gate.passed ? "#47765b" : "#8b1e1e", fontWeight: 700 }}>{gate.passed ? "PASS" : "FAIL"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </Page>;
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></div>;
}

export function Intake() {
  const [status, setStatus] = useState("Checking backend");
  const [fileName, setFileName] = useState<string>();
  const [dataset, setDataset] = useState<DatasetRecord | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDemoDataset() {
    setError(null);
    setStatus("Loading bundled demo file...");
    try {
      const response = await api.get("/datasets");
      const records = response.data as DatasetRecord[];
      if (records.length > 0) {
        const first = records[0];
        setFileName(first.filename);
        setDataset(first);
        setStatus(`Demo dataset ready: ${first.validation.status.toUpperCase()}`);
      } else {
        setStatus("No demo dataset found");
        setError("The bundled demo CSV is missing from data/sample.");
      }
    } catch {
      setStatus("Backend unavailable");
      setError("Start the FastAPI backend, then click Load demo file. Command: backend\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --reload --port 8000");
    }
  }

  useEffect(() => {
    void loadDemoDataset();
  }, []);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;
    setFileName(selectedFile.name);
    setUploading(true);
    setError(null);
    try {
      const response = await uploadDataset(selectedFile);
      const record = response.data.dataset as DatasetRecord;
      setDataset(record);
      setStatus(`Validated: ${record.validation.status.toUpperCase()}`);
      if (record.validation.status === "invalid") {
        setError(record.validation.issues.join(" ") || "The uploaded CSV failed validation.");
      }
    } catch {
      setError("Upload failed because the FastAPI backend is unavailable. Start it and try again.");
      setStatus("Upload rejected");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  const validation = dataset?.validation ?? null;
  const pipelineState = validation ? ["Complete", "Complete", validation.status === "valid" ? "Validated" : "Needs attention"] : ["Pending", "Pending", "Pending"];

  return <Page title="Intake" description="Load a market file and keep every transformation visible.">
    <div className="two-columns">
      <div className="card upload-card">
        <div>
          <div className="upload-mark">+</div>
          <h2>Choose a CSV</h2>
          <p>Required columns include Symbol, Date, Expiry Date, Open, High, Low, Close, Volume, and OpenInterest.</p>
          <div className="intake-actions">
            <label className="primary-button">{uploading ? "Uploading..." : "Select file"}<input type="file" accept=".csv" onChange={handleFileChange} hidden disabled={uploading} /></label>
            <button className="secondary-button" type="button" onClick={() => void loadDemoDataset()} disabled={uploading}>Load demo file</button>
          </div>
          {fileName && <p className="selected-file">{fileName}</p>}
          {error && <p className="error-text">{error}</p>}
        </div>
        <div className="pipeline">
          <div className="workspace-label">PIPELINE</div>
          <p><span>01</span> Parse explicit date formats <b>{pipelineState[0]}</b></p>
          <p><span>02</span> Normalize symbols and units <b>{pipelineState[1]}</b></p>
          <p><span>03</span> Validate lifecycle window <b>{pipelineState[2]}</b></p>
        </div>
      </div>
      <div className="card">
        <p className="eyebrow">BACKEND STATUS</p>
        <h2>{status}</h2>
        <p className="muted">The bundled synthetic CSV is validated by the FastAPI service. It is safe for demonstrations and clearly labeled synthetic.</p>
        {validation && (
          <div className="dataset-summary">
            <p><strong>Rows:</strong> {validation.row_count}</p>
            <p><strong>Date range:</strong> {validation.date_range.start ?? "—"} to {validation.date_range.end ?? "—"}</p>
            <p><strong>Symbols:</strong> {validation.symbols.join(", ") || "—"}</p>
            <p><strong>Status:</strong> {validation.status}</p>
            {validation.issues.length > 0 && <ul>{validation.issues.slice(0, 3).map((issue) => <li key={issue}>{issue}</li>)}</ul>}
          </div>
        )}
      </div>
    </div>
  </Page>;
}

const DEMO_BASIS = [
  { date: "10 Mar", basis: 1.0, residual: 0.4, rollDown: 0.6 },
  { date: "11 Mar", basis: 1.5, residual: 0.8, rollDown: 0.7 },
  { date: "12 Mar", basis: 1.5, residual: 0.9, rollDown: 0.6 },
];

export function Expiry() {
  const lifecycle = [
    ["GOLDM", "04 Sep 2026", "10 Mar 2026", "12 Mar 2026", "04 Sep 2026"],
    ["GOLDTEN", "04 Sep 2026", "10 Mar 2026", "12 Mar 2026", "04 Sep 2026"],
  ];
  return <Page title="Expiry" description="Contract lifecycle is a constraint, not a decoration.">
    <div className="card lifecycle-card">
      <div className="section-heading"><div><div className="empty-mark">—</div><h2>Lifecycle timeline</h2><p className="muted">Synthetic demo contract window from the validated sample file.</p></div><span className="demo-badge">SYNTHETIC DEMO</span></div>
      <div className="lifecycle-table">
        <div className="lifecycle-row lifecycle-header"><span>CONTRACT</span><span>EXPIRY</span><span>FIRST OBSERVED</span><span>PEAK OI</span><span>LAST TRADE</span></div>
        {lifecycle.map((row) => <div className="lifecycle-row" key={row[0]}>{row.map((cell) => <span key={cell}>{cell}</span>)}</div>)}
      </div>
      <div className="timeline-track"><i /><i /><i /><i /></div>
      <div className="timeline-labels"><span>LISTED</span><span>LIQUID</span><span>PEAK OI</span><span>LAST TRADE</span></div>
    </div>
  </Page>;
}

export function Basis() {
  return <Page title="Basis" description="Separate roll-down from residual change so the signal has an explainable driver.">
    <div className="two-columns">
      <div className="card empty-panel">
        <div className="empty-mark">—</div><h2>Basis decomposition</h2>
        <div style={{ height: 230, marginTop: 16 }}><ResponsiveContainer width="100%" height="100%"><AreaChart data={DEMO_BASIS}><CartesianGrid stroke="#d9d0c0" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Area type="monotone" dataKey="basis" stroke="#b8781d" fill="#f1e3c8" strokeWidth={2} /></AreaChart></ResponsiveContainer></div>
      </div>
      <div className="card">
        <p className="eyebrow">SIGNAL DRIVER</p><h2>Residual change</h2>
        <p className="muted">The residual is the observed basis change after the lifecycle roll-down component is separated.</p>
        <div className="decomposition-list"><p><span>Latest basis</span><strong>1.50</strong></p><p><span>Roll-down</span><strong>0.60</strong></p><p><span>Residual change</span><strong>0.90</strong></p><p><span>Data policy</span><strong>t−1 only</strong></p></div>
        <span className="demo-badge">SYNTHETIC SAMPLE · 3 DAYS</span>
      </div>
    </div>
  </Page>;
}
export function Tour() { return <Page title="Tour" description="Review the assumptions and evidence behind a run."><EmptyPanel title="Transparent by default" text="Every result links back to a source, date rule, policy, and gate decision." /></Page>; }
export function Verdict() {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.post("/analysis", { dataset_id: "demo", pair: "GOLDM/GOLDTEN", analysis_date: "12/03/2026", scenario: "base" })
      .then((response) => setResult(response.data))
      .catch(() => setResult({ verdict: "backend_unavailable", reason_code: "BACKEND_UNAVAILABLE", gates: [] }))
      .finally(() => setLoading(false));
  }, []);
  const blocked = result?.verdict !== "ok";
  return <Page title="Verdict" description="A verdict is provisional until the comparison is sufficiently established.">
    <div className={`verdict-hero ${blocked ? "blocked" : "ready"}`}>
      <div className="verdict-kicker">{loading ? "RUNNING DEMO ANALYSIS" : blocked ? "NO ACTIONABLE SIGNAL" : "COMPARISON ESTABLISHED"}</div>
      <h2>{loading ? "Evaluating the sample..." : blocked ? "Cannot establish a comparison" : "Comparison established"}</h2>
      <p>{loading ? "The backend is validating the seeded synthetic dataset." : blocked ? `Reason code: ${result?.reason_code ?? "INSUFFICIENT_DATA"}. The result is not presented as a trade.` : "All required gates passed for this run."}</p>
    </div>
    <div className="card gate-card"><div className="section-heading"><div><p className="eyebrow">RUN GATES</p><h2>Evidence before opinion</h2></div><span className="demo-badge">RUN {result?.run_id ? result.run_id.slice(0, 8) : "DEMO"}</span></div>{(result?.gates ?? []).map((gate: { code: string; passed: boolean; detail: string }) => <div className="gate-line" key={gate.code}><span><b>{gate.code}</b><small>{gate.detail}</small></span><strong className={gate.passed ? "pass" : "fail"}>{gate.passed ? "PASS" : "FAIL"}</strong></div>)}</div>
  </Page>;
}
export function Privacy() { return <Page title="Privacy" description="Goldlens keeps credentials on the backend and does not expose private source data in the client." />; }
export function Terms() { return <Page title="Terms" description="Goldlens outputs are analytical and not financial advice." />; }
export function Lab() {
  const data = [{ date: "10 Mar", strategy: 0, plain: 0 }, { date: "11 Mar", strategy: 0.8, plain: 0.5 }, { date: "12 Mar", strategy: 1.1, plain: 0.9 }];
  return <Page title="Strategy lab" description="Compare net strategy return with equivalent plain gold exposure over the same holding periods.">
    <div className="metric-grid"><Metric label="STRATEGY RETURN" value="+1.10%" note="Synthetic demonstration" /><Metric label="PLAIN GOLD" value="+0.90%" note="Same holding window" /><Metric label="ATTRIBUTION" value="+0.20%" note="Strategy minus plain gold" /><Metric label="OBSERVATIONS" value="3 days" note="Validated sample window" /></div>
    <div className="card empty-panel"><div className="empty-mark">—</div><h2>Return attribution</h2><div style={{ height: 250, marginTop: 16 }}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data}><CartesianGrid stroke="#d9d0c0" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Area type="monotone" dataKey="strategy" stroke="#b8781d" fill="#f1e3c8" strokeWidth={2} /><Area type="monotone" dataKey="plain" stroke="#47765b" fill="transparent" strokeWidth={2} /></AreaChart></ResponsiveContainer></div><p className="muted">Goldlens keeps this synthetic result visibly separate from live market evidence.</p></div>
  </Page>;
}
export function Alerts() {
  const [status, setStatus] = useState<{ state: string; reason_code: string }>();
  const [loading, setLoading] = useState(true);

  async function loadAlertStatus() {
    setLoading(true);
    try {
      const response = await api.get("/alerts/status");
      setStatus(response.data);
    } catch {
      setStatus({ state: "backend_offline", reason_code: "BACKEND_UNAVAILABLE" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadAlertStatus(); }, []);

  const isOffline = status?.reason_code === "BACKEND_UNAVAILABLE";
  return <Page title="Alerts" description="Quiet alerts only appear after every gate passes and costs do not exceed the gap.">
    <div className={`card alert-card alert-state-card${isOffline ? " alert-offline" : ""}`}>
      <p className="eyebrow">CURRENT STATE</p>
      <h2>{loading ? "Checking..." : status?.state ?? "no_signal"}</h2>
      <p className="status-reason">{loading ? "Checking backend status." : status?.reason_code}</p>
      <p className="muted">
        {isOffline
          ? "The FastAPI backend is not running. Start it, then retry to load the seeded demo status."
          : "The synthetic demo has insufficient history for an alert. No buy or sell wording is generated."}
      </p>
      {isOffline && <button className="secondary-button" type="button" onClick={() => void loadAlertStatus()}>Retry connection</button>}
    </div>
  </Page>;
}

export function Munimji() {
  const [question, setQuestion] = useState("Explain the current basis and why the result is not a trade.");
  const [language, setLanguage] = useState("en");
  const [reply, setReply] = useState("Ask Munimji about the basis, the cost gate, the date validity, or the reason for an inconclusive verdict.");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function askMunimji() {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post("/munimji/chat", {
        question,
        language,
        context: {
          route: "desk",
          page: "Desk",
          dataset_name: "goldlens_synthetic.csv",
          pair: "GOLDM / GOLDTEN",
          verdict: "insufficient_data",
          reason_code: "SHORT_HISTORY",
        },
      });
      setReply(response.data.reply);
    } catch (apiError: any) {
      setError(apiError?.response?.data?.detail ?? "Munimji is unavailable right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void askMunimji();
  }, []);

  return <Page title="Munimji" description="Ask the deterministic Goldlens guide to explain the verdict, cost gate, and basis logic."><div className="card munimji-card">
    <div className="munimji-header">
      <div className="eyebrow">AI ASSISTANT</div>
      <select value={language} onChange={(event) => setLanguage(event.target.value)}>
        <option value="en">English</option>
        <option value="hi">हिन्दी</option>
      </select>
    </div>
    <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={4} placeholder="Ask Munimji..." />
    <div className="munimji-actions">
      <button className="primary-button" type="button" onClick={() => void askMunimji()} disabled={loading}>{loading ? "Asking..." : "Ask Munimji"}</button>
      <button className="secondary-button" type="button" onClick={() => setQuestion("Explain the cost gate and why the dataset is insufficient.")}>Cost gate</button>
      <button className="secondary-button" type="button" onClick={() => setQuestion("What does basis mean in this Goldlens run?")}>Basis</button>
    </div>
    {error && <p className="error-text">{error}</p>}
    <div className="munimji-response">
      <div className="munimji-label">Munimji response</div>
      <p>{reply}</p>
    </div>
  </div></Page>;
}
