import React, { useState, useEffect } from "react";
import { getVendors, getProducts, getNegotiationStrategy } from "../services/api";

export default function NegotiationStrategy() {
  const [vendors, setVendors] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    vendor_id: "",
    product_id: "",
    quantity: 500,
    current_quoted_price: "",
    target_price_reduction_pct: 10,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getVendors().then(setVendors).catch(() => {});
    getProducts().then(setProducts).catch(() => {});
  }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        vendor_id: Number(form.vendor_id),
        product_id: Number(form.product_id),
        quantity: Number(form.quantity),
        current_quoted_price: Number(form.current_quoted_price),
        target_price_reduction_pct: Number(form.target_price_reduction_pct),
      };
      const data = await getNegotiationStrategy(payload);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to generate strategy.");
    } finally {
      setLoading(false);
    }
  };

  const isValid =
    form.vendor_id && form.product_id && form.quantity && form.current_quoted_price;

  const confidenceClass = (c) => {
    if (c === "High") return "badge-success";
    if (c === "Low") return "badge-danger";
    return "badge-warning";
  };

  const statusBadge = (status) => {
    const map = { overpriced: "badge-danger", fairly_priced: "badge-success", underpriced: "badge-info" };
    return <span className={`badge ${map[status] || "badge-info"}`}>{status.replace("_", " ")}</span>;
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Negotiation AI</h1>
        <p className="page-sub">RAG-grounded strategy — retrieves similar cases, then generates LLM advice</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 24, alignItems: "start" }}>
        <div className="card">
          <p className="card-title">Negotiation Context</p>
          <div className="form-group">
            <label className="form-label">Vendor</label>
            <select value={form.vendor_id} onChange={(e) => set("vendor_id", e.target.value)}>
              <option value="">— Select vendor —</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Product</label>
            <select value={form.product_id} onChange={(e) => set("product_id", e.target.value)}>
              <option value="">— Select product —</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Order Quantity</label>
            <input type="number" value={form.quantity} min={1} onChange={(e) => set("quantity", e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Current Quoted Price (per unit)</label>
            <input type="number" value={form.current_quoted_price} min={0} step={0.01} placeholder="0.00"
              onChange={(e) => set("current_quoted_price", e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Target Reduction % (default 10%)</label>
            <input type="number" value={form.target_price_reduction_pct} min={1} max={50}
              onChange={(e) => set("target_price_reduction_pct", e.target.value)} />
          </div>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!isValid || loading} style={{ width: "100%" }}>
            {loading ? "Generating strategy..." : "◎ Generate Strategy"}
          </button>
          {error && <p style={{ color: "var(--danger)", fontSize: 11, marginTop: 12 }}>{error}</p>}
        </div>

        <div className="card" style={{ background: "transparent", border: "1px dashed var(--border)" }}>
          <p className="card-title">RAG Pipeline Flow</p>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            {[
              ["1", "Price Analysis", "Market avg & vendor deviation computed from PostgreSQL"],
              ["2", "Query Embedding", "Context embedded using Sentence-Transformers (local)"],
              ["3", "FAISS Retrieval", "Top-3 similar cases retrieved from vector index"],
              ["4", "LLM Generation", "Strategy generated with retrieved cases in prompt context"],
            ].map(([n, title, desc]) => (
              <div key={n} style={{ display: "flex", gap: 12, marginBottom: 14 }}>
                <div style={{
                  width: 22, height: 22, borderRadius: "50%",
                  background: "var(--accent-dim)", border: "1px solid var(--border-accent)",
                  color: "var(--accent-light)", fontSize: 10, fontWeight: 700,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
                }}>{n}</div>
                <div>
                  <p style={{ color: "var(--text-primary)", marginBottom: 2, fontWeight: 500 }}>{title}</p>
                  <p style={{ fontSize: 11, color: "var(--text-muted)" }}>{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-wrap">
          <div className="spinner" />
          <span>Retrieving similar cases · Generating strategy...</span>
        </div>
      )}

      {result && (
        <div>
          {/* Summary bar */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "center" }}>
              <div>
                <p style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.06em" }}>Vendor</p>
                <p style={{ fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 600 }}>{result.vendor_name}</p>
              </div>
              <div>
                <p style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.06em" }}>Price Status</p>
                {statusBadge(result.price_analysis?.price_status)}
              </div>
              <div>
                <p style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.06em" }}>Recommended Target</p>
                <p style={{ fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 700, color: "var(--success)" }}>
                  ${result.recommended_target_price.toFixed(2)}/unit
                </p>
              </div>
              <div>
                <p style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.06em" }}>AI Confidence</p>
                <span className={`badge ${confidenceClass(result.confidence_level)}`}>{result.confidence_level}</span>
              </div>
            </div>
          </div>

          <div className="grid-2" style={{ marginBottom: 16 }}>
            {/* Retrieved Cases */}
            <div className="card">
              <p className="card-title">Retrieved Cases ({result.retrieved_cases?.length})</p>
              {result.retrieved_cases?.map((c) => (
                <div className="case-card" key={c.case_id}>
                  <div className="case-sim">
                    <span>Similarity</span>
                    <div className="sim-bar">
                      <div className="sim-fill" style={{ width: `${c.similarity_score * 100}%` }} />
                    </div>
                    <span>{(c.similarity_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="case-title">{c.title}</p>
                  <p className="case-outcome">✓ {c.outcome}</p>
                  <div>{c.tactics_used.map((t) => <span className="tactic-tag" key={t}>{t}</span>)}</div>
                </div>
              ))}
            </div>

            {/* Key Talking Points */}
            <div className="card">
              <p className="card-title">Key Talking Points</p>
              {result.key_talking_points?.length > 0 ? (
                result.key_talking_points.map((tp, i) => (
                  <div className="talking-point" key={i}>
                    <span className="tp-bullet">▸</span>
                    <span>{tp}</span>
                  </div>
                ))
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: 12 }}>
                  See strategy text below for detailed talking points.
                </p>
              )}
            </div>
          </div>

          {/* Full Strategy */}
          <div className="card">
            <p className="card-title">Generated Negotiation Strategy</p>
            <div className="strategy-box">{result.strategy}</div>
          </div>
        </div>
      )}
    </div>
  );
}
