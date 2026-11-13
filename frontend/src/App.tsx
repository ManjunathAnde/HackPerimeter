import { BrowserRouter, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";

export default function App() {
  return (
    <div className="min-h-screen bg-cream font-sans text-ink">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatPage />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}
