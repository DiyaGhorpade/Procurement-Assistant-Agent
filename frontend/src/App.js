import React, { useState } from "react";
import Dashboard from "./pages/Dashboard";
import VendorRecommender from "./pages/VendorRecommender";
import PriceAnalysis from "./pages/PriceAnalysis";
import NegotiationStrategy from "./pages/NegotiationStrategy";
import "./index.css";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "◈" },
  { id: "vendors", label: "Vendor Recommender", icon: "⊞" },
  { id: "price", label: "Price Analysis", icon: "↗" },
  { id: "negotiate", label: "Negotiation AI", icon: "◎" },
];

export default function App() {
  const [page, setPage] = useState("dashboard");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">⬡</span>
          <div>
            <p className="brand-title">ProcureAI</p>
            <p className="brand-sub">Negotiation Assistant</p>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${page === item.id ? "active" : ""}`}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="status-dot" />
          <span>RAG Pipeline Active</span>
        </div>
      </aside>

      <main className="main-content">
        {page === "dashboard" && <Dashboard onNavigate={setPage} />}
        {page === "vendors" && <VendorRecommender />}
        {page === "price" && <PriceAnalysis />}
        {page === "negotiate" && <NegotiationStrategy />}
      </main>
    </div>
  );
}
