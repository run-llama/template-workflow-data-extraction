import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "@llamaindex/ui/styles.css";
import "./index.css";

// https://github.com/run-llama/llama_deploy/blob/main/llama_deploy/apiserver/deployment.py#L183
const base = import.meta.env.VITE_LLAMA_DEPLOY_BASE_PATH ?? "/";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={base}>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
