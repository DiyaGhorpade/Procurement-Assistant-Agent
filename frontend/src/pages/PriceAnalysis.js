import React, { useState, useEffect } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { getVendors, getProducts, getPriceAnalysis } from "../services/api";

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: 11, marginBottom: 4 }}>{label}</p>
        <p style={{ color: "var(--accent-light)", fontWeight: 600, fontSize: 13 }}>
          ${payload[0].value.toFixed(3)}
        </p>
      </div>
    );
  }
  return null;
};

export default function PriceAnalysis() {
  const [vendors, setVendors] = useState([]);
  const [products, setProducts] = useState([]);
  const [vendorId, setVendorId] = useState("");
  const [productId, setProductId] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getVendors().then(setVendors).catch(() => {});
    getProducts().then(setProducts).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    if (!vendorId || !productId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getPriceAnalysis(Number(vendorId), Number(productId));
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || "No price data found for this combination.");
    } finally {
      setLoading(false);
    }
  };

  const deviationClass = (dev) => {
    if (dev > 10) return "deviation-pos";
    if (dev < -10) return "deviation-neg";
    return "deviation-neutral";
  };

  const statusBadge = (status) => {
    const map = {
      overpriced: "badge-danger",
      fairly_priced: "badge-success",
      underpriced: "badge-info",
    };
    return <span className={`badge ${map[status] || "badge-info"}`}>{status.replace("_", " ")}</span>;
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Price Analysis</h1>
        <p className="page-sub">Detect overpriced vendors and quantify negotiation leverage from historical data</p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <p className="card-title">Select Vendor × Product</p>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1, minWidth: 180, marginBottom: 0 }}>
            <label className="form-label">Vendor</label>
            <select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
              <option value="">— Select vendor —</option>
              {vendors.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: 180, marginBottom: 0 }}>
            <label className="form-label">Product</label>
            <select value={productId} onChange={(e) => setProductId(e.target.value)}>
              <option value="">— Select product —</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!vendorId || !productId || loading}
            style={{ flexShrink: 0 }}
          >
            {loading ? "Analysing..." : "↗ Analyse Prices"}
          </button>
        </div>
        {error && <p style={{ color: "var(--danger)", fontSize: 11, marginTop: 12 }}>{error}</p>}
      </div>

      {loading && (
        <div className="loading-wrap">
          <div className="spinner" />
          <span>Computing historical price trends...</span>
        </div>
      )}

      {result && (
        <div>
          <div className="grid-2" style={{ marginBottom: 20 }}>
            <div className="card">
              <p className="card-title">Price Position</p>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                <div>
                  <div className="deviation-display">
                    <span className={`deviation-number ${deviationClass(result.price_deviation_pct)}`}>
                      {result.price_deviation_pct > 0 ? "+" : ""}{result.price_deviation_pct.toFixed(1)}%
                    </span>
                    {statusBadge(result.price_status)}
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-secondary)" }}>vs market average</p>
                </div>
              </div>
              <hr className="divider" />
              {[
                ["Market Average", `$${result.current_market_avg.toFixed(4)}`],
                ["Vendor Average", `$${result.vendor_avg_price.toFixed(4)}`],
                ["Price Deviation", `${result.price_deviation_pct > 0 ? "+" : ""}${result.price_deviation_pct.toFixed(1)}%`],
              ].map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                  <span style={{ color: "var(--text-muted)" }}>{k}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{v}</span>
                </div>
              ))}
            </div>

            <div className="card">
              <p className="card-title">Negotiation Intelligence</p>
              <div style={{ padding: "12px 14px", background: "var(--bg-elevated)", borderRadius: 8, borderLeft: "3px solid var(--accent)", marginBottom: 14 }}>
                <p style={{ fontSize: 12, color: "var(--text-primary)", lineHeight: 1.7 }}>
                  {result.negotiation_leverage}
                </p>
              </div>
              <p className="card-title" style={{ marginBottom: 8 }}>Recommendation</p>
              <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.7 }}>
                {result.recommendation}
              </p>
            </div>
          </div>

          {result.trend?.length > 0 && (
            <div className="card">
              <p className="card-title">
                Price Trend — {result.vendor_name} × {result.product_name}
              </p>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={result.trend} margin={{ top: 4, right: 12, left: -10, bottom: 0 }}>
                  <XAxis dataKey="period" axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis axisLine={false} tickLine={false} tickFormatter={(v) => `$${v.toFixed(2)}`} />
                  <Tooltip content={<CustomTooltip />} />
                  <ReferenceLine
                    y={result.current_market_avg}
                    stroke="rgba(99,102,241,0.4)"
                    strokeDasharray="4 3"
                    label={{ value: "Market avg", position: "right", fill: "var(--accent-light)", fontSize: 10 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="avg_price"
                    stroke="var(--accent-light)"
                    strokeWidth={2}
                    dot={{ fill: "var(--accent)", r: 3 }}
                    activeDot={{ r: 5, fill: "var(--accent-light)" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
