import React, { useState, useEffect } from "react";
import { getProducts, recommendVendors } from "../services/api";

const ScoreBar = ({ label, value, color }) => (
  <div className="score-bar-wrap">
    <div className="score-bar-header">
      <span className="score-bar-label">{label}</span>
      <span className="score-bar-val">{value.toFixed(1)}</span>
    </div>
    <div className="score-bar-track">
      <div className="score-bar-fill" style={{ width: `${value}%`, background: color }} />
    </div>
  </div>
);

export default function VendorRecommender() {
  const [products, setProducts] = useState([]);
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState(500);
  const [topN, setTopN] = useState(3);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getProducts().then(setProducts).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!productId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await recommendVendors(Number(productId), Number(quantity), Number(topN));
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to fetch recommendations.");
    } finally {
      setLoading(false);
    }
  };

  const rankBadgeClass = (rank) =>
    rank === 1 ? "rank-1-badge" : rank === 2 ? "rank-2-badge" : "rank-3-badge";

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Vendor Recommender</h1>
        <p className="page-sub">Scores vendors using explainable rules — Price 40% · Delivery 30% · Reliability 30%</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 24, alignItems: "start" }}>
        <div className="card">
          <p className="card-title">Configure Query</p>
          <div className="form-group">
            <label className="form-label">Product</label>
            <select value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">— Select product —</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Order Quantity</label>
            <input type="number" value={quantity} min={1} onChange={(e) => setQuantity(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Top N Vendors</label>
            <select value={topN} onChange={(e) => setTopN(e.target.value)}>
              <option value={3}>Top 3</option>
              <option value={5}>Top 5</option>
            </select>
          </div>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!productId || loading} style={{ width: "100%" }}>
            {loading ? "Analysing..." : "⊞ Get Recommendations"}
          </button>

          {error && (
            <p style={{ color: "var(--danger)", fontSize: 11, marginTop: 12 }}>{error}</p>
          )}
        </div>

        <div className="card" style={{ background: "transparent", border: "1px dashed var(--border)" }}>
          <p className="card-title">How Scoring Works</p>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.9 }}>
            <p style={{ marginBottom: 8 }}>Each vendor is scored 0–100 across three dimensions:</p>
            {[
              ["Price (40%)", "Lower price relative to peers = higher score"],
              ["Delivery (30%)", "Fewer average days = higher score"],
              ["Reliability (30%)", "On-time rate × quality rating"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                <span style={{ color: "var(--accent-light)", flexShrink: 0 }}>▸</span>
                <span><span style={{ color: "var(--text-primary)" }}>{k}:</span> {v}</span>
              </div>
            ))}
            <p style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)" }}>
              All scores are computed from your historical purchase order data.
              No AI black-box — every score is fully explainable.
            </p>
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-wrap">
          <div className="spinner" />
          <span>Scoring vendors against historical data...</span>
        </div>
      )}

      {result && (
        <div>
          <p style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 16 }}>
            {result.analysis_note}
          </p>

          {result.recommendations.map((rec) => (
            <div className="vendor-rank-card" key={rec.vendor.id} style={{ marginBottom: 16 }}>
              <span className={`rank-badge ${rankBadgeClass(rec.rank)}`}>
                #{rec.rank} {rec.rank === 1 ? "— Top Pick" : ""}
              </span>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16, paddingTop: 8 }}>
                <div>
                  <p style={{ fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
                    {rec.vendor.name}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    {rec.vendor.category} · {rec.vendor.country}
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <p style={{ fontFamily: "var(--font-display)", fontSize: 28, fontWeight: 800, color: "var(--accent-light)" }}>
                    {rec.score_breakdown.total_score.toFixed(0)}
                  </p>
                  <p style={{ fontSize: 10, color: "var(--text-muted)" }}>composite score</p>
                </div>
              </div>

              <div className="grid-2" style={{ gap: 24 }}>
                <div>
                  <ScoreBar label="Price Score" value={rec.score_breakdown.price_score} color="var(--accent)" />
                  <ScoreBar label="Delivery Score" value={rec.score_breakdown.delivery_score} color="#10b981" />
                  <ScoreBar label="Reliability Score" value={rec.score_breakdown.reliability_score} color="#f59e0b" />
                </div>
                <div style={{ fontSize: 12 }}>
                  {[
                    ["Avg Unit Price Percentile", `${rec.score_breakdown.price_percentile.toFixed(0)}th pct`],
                    ["Avg Delivery", `${rec.score_breakdown.avg_delivery_days.toFixed(0)} days`],
                    ["On-Time Rate", `${rec.score_breakdown.on_time_rate.toFixed(1)}%`],
                    ["Quality Rating", `${rec.score_breakdown.avg_quality.toFixed(1)} / 5`],
                    ["Total Orders", `${rec.score_breakdown.total_orders}`],
                  ].map(([k, v]) => (
                    <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--text-muted)" }}>{k}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              <p style={{ marginTop: 12, padding: "8px 12px", background: "var(--bg)", borderRadius: 6, fontSize: 11, color: "var(--text-secondary)", borderLeft: "2px solid var(--border-accent)" }}>
                {rec.recommendation}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
