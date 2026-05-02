import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({ baseURL: BASE_URL });

export const getVendors = () => api.get("/vendors").then((r) => r.data);
export const getProducts = () => api.get("/products").then((r) => r.data);
export const getOrders = (vendorId, productId) =>
  api.get("/orders", { params: { vendor_id: vendorId, product_id: productId } }).then((r) => r.data);

export const recommendVendors = (productId, quantity, topN = 3) =>
  api.post("/ai/recommend-vendors", { product_id: productId, quantity, top_n: topN }).then((r) => r.data);

export const getPriceAnalysis = (vendorId, productId) =>
  api.get(`/ai/price-analysis/${vendorId}/${productId}`).then((r) => r.data);

export const getNegotiationStrategy = (payload) =>
  api.post("/ai/negotiation-strategy", payload).then((r) => r.data);
