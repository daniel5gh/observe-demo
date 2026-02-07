import { useState, useEffect, FormEvent } from "react";

const API = "http://localhost:5050";

interface Order {
  id: string;
  customerName: string;
  product: string;
  quantity: number;
  price: number | null;
  status: string;
  createdAt: string;
}

export default function App() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [product, setProduct] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API}/orders`);
      if (res.ok) setOrders(await res.json());
    } catch (e) {
      console.error("Failed to fetch orders", e);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const res = await fetch(`${API}/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customerName, product, quantity }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.error || `Request failed: ${res.status}`);
      } else {
        setCustomerName("");
        setProduct("");
        setQuantity(1);
        await fetchOrders();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "2rem auto", fontFamily: "system-ui, sans-serif" }}>
      <h1>Observe Demo - Orders</h1>

      <form onSubmit={handleSubmit} style={{ marginBottom: "2rem", display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "end" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Customer
          <input value={customerName} onChange={(e) => setCustomerName(e.target.value)} required style={{ padding: "0.4rem" }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Product
          <input value={product} onChange={(e) => setProduct(e.target.value)} required placeholder='Try "error" for error trace' style={{ padding: "0.4rem" }} />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          Qty
          <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} required style={{ padding: "0.4rem", width: 60 }} />
        </label>
        <button type="submit" disabled={submitting} style={{ padding: "0.4rem 1rem", alignSelf: "end" }}>
          {submitting ? "Submitting..." : "Create Order"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <h2>Orders</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
            <th style={{ padding: "0.5rem" }}>ID</th>
            <th style={{ padding: "0.5rem" }}>Customer</th>
            <th style={{ padding: "0.5rem" }}>Product</th>
            <th style={{ padding: "0.5rem" }}>Qty</th>
            <th style={{ padding: "0.5rem" }}>Price</th>
            <th style={{ padding: "0.5rem" }}>Status</th>
            <th style={{ padding: "0.5rem" }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} style={{ borderBottom: "1px solid #eee" }}>
              <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.8rem" }}>{o.id.slice(0, 8)}</td>
              <td style={{ padding: "0.5rem" }}>{o.customerName}</td>
              <td style={{ padding: "0.5rem" }}>{o.product}</td>
              <td style={{ padding: "0.5rem" }}>{o.quantity}</td>
              <td style={{ padding: "0.5rem" }}>{o.price != null ? `$${o.price.toFixed(2)}` : "-"}</td>
              <td style={{ padding: "0.5rem" }}>{o.status}</td>
              <td style={{ padding: "0.5rem", fontSize: "0.8rem" }}>{new Date(o.createdAt).toLocaleString()}</td>
            </tr>
          ))}
          {orders.length === 0 && (
            <tr>
              <td colSpan={7} style={{ padding: "1rem", textAlign: "center", color: "#888" }}>
                No orders yet. Create one above!
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <p style={{ marginTop: "2rem", fontSize: "0.85rem", color: "#666" }}>
        Open <a href="http://localhost:8080" target="_blank" rel="noreferrer">HyperDX</a> to view distributed traces.
        {" | "}
        <a href="http://localhost:15672" target="_blank" rel="noreferrer">RabbitMQ Management</a> (demo/demo)
      </p>
    </div>
  );
}
