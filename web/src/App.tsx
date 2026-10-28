import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Alerts, Basis, Desk, Expiry, Intake, Lab, Munimji, Privacy, Terms, Tour, Verdict } from "./routes/Pages";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/desk" replace />} />
          <Route path="/desk" element={<Desk />} />
          <Route path="/intake" element={<Intake />} />
          <Route path="/tour" element={<Tour />} />
          <Route path="/verdict" element={<Verdict />} />
          <Route path="/expiry" element={<Expiry />} />
          <Route path="/basis" element={<Basis />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/lab" element={<Lab />} />
          <Route path="/munimji" element={<Munimji />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
