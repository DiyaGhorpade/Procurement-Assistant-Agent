import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";

const MOCK_SPEND = [
  { month: "Oct", spend: 84200 },
  { month: "Nov", spend: 91500 },
  { month: "Dec", spend: 68300 },
  { month: "Jan", spend: 112400 },
  { month: "Feb", spend: 97800 },
  { month: "Mar", spend: 134200 },
];

const TOP_VENDORS = [
  { name: "GlobalTech Supplies", score: 87, orders: 42, status: "overpriced" },
  { name: "EuroComponents GmbH", score: 81, orders: 38, status: "fairly_priced" },
  { name: "PrimeParts Inc.", score: 75, orders: 29, status: "underpriced" },
  { name: "AsiaPacific Trading", score: 68, orders: 21, status: "overpriced" },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) {
    return (
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px" }}>
        <p style={{ color: "var(--text-secondary)", fontSize: 11, marginBottom: 4 }}>{label}</p>
        <p style={{ color: "var(--accent-light)", fontFamily: "var(--font-display)", fontSize: 16, fontWeight: 700 }}>
          ${payload[0].value.toLocaleString()}
        </p>
      </div>
    );
  }
  return null;
};

export default function Dashboard({ onNavigate }) {
  const statusBadge = (status) => {
    const map = {
      overpriced: ["badge-danger", "Overpriced"],
      fairly_priced: ["badge-success", "Fair"],
      underpriced: ["badge-info", "Underpriced"],
    };
    const [cls, label] = map[status] || ["badge-info", status];
    return <span className={`badge ${cls}`}>{label}</span>;
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Procurement Intelligence</h1>
        <p className="page-sub">AI-powered overview — last updated: {new Date().toLocaleDateString()}</p>
      </div>

      <div className="stat-grid">
        {[
          { label: "Total Vendors", value: "7", change: "+2 this quarter", dir: "up" },
          { label: "Active Products", value: "7", change: "Stable", dir: "up" },
          { label: "Avg Negotiation Saving", value: "12.4%", change: "vs last quarter", dir: "up" },
          { label: "Overpriced Vendors", value: "3", change: "Requires attention", dir: "down" },
        ].map((s) => (
          <div className="stat-card" key={s.label}>
            <p className="stat-label">{s.label}</p>
            <p className="stat-value">{s.value}</p>
            <p className={`stat-change ${s.dir}`}>{s.change}</p>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <p className="card-title">Monthly Procurement Spend</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={MOCK_SPEND} barSize={24}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} />
              <YAxis axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="spend" radius={[4, 4, 0, 0]}>
                {MOCK_SPEND.map((_, i) => (
                  <Cell key={i} fill={i === MOCK_SPEND.length - 1 ? "var(--accent)" : "var(--bg-elevated)"} stroke="var(--border)" strokeWidth={1} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <p className="card-title">Top Vendors by Score</p>
          {TOP_VENDORS.map((v, i) => (
            <div key={v.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "9px 0", borderBottom: i < TOP_VENDORS.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontFamily: "var(--font-display)", fontSize: 13, fontWeight: 700, color: "var(--text-muted)", width: 18 }}>{i + 1}</span>
                <div>
                  <p style={{ fontSize: 12, color: "var(--text-primary)" }}>{v.name}</p>
                  <p style={{ fontSize: 10, color: "var(--text-muted)" }}>{v.orders} orders</p>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {statusBadge(v.status)}
                <span style={{ fontFamily: "var(--font-display)", fontSize: 15, fontWeight: 700, color: "var(--accent-light)" }}>{v.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <p className="card-title">Quick Actions</p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={() => onNavigate("vendors")}>⊞ Recommend Vendors</button>
          <button className="btn btn-ghost" onClick={() => onNavigate("price")}>↗ Analyse Prices</button>
          <button className="btn btn-ghost" onClick={() => onNavigate("negotiate")}>◎ Generate Strategy</button>
        </div>
      </div>
    </div>
  );
}
