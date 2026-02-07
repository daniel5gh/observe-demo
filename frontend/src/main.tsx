import React from "react";
import ReactDOM from "react-dom/client";
import { initTelemetry } from "./telemetry";
import App from "./App";

initTelemetry();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
