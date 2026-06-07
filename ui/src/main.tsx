import React from "react";
import ReactDOM from "react-dom/client";
import { CopilotKit } from "@copilotkit/react-core";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CopilotKit runtimeUrl="/api/copilotkit">
      <App />
    </CopilotKit>
  </React.StrictMode>
);
