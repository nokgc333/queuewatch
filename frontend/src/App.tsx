/** ルーティング定義（仕様書§6.1 画面一覧、ADR-0006: react-router使用）。 */
import type { ReactElement } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { Dashboard } from "@/pages/Dashboard";
import { DeadLetterQueue } from "@/pages/DeadLetterQueue";
import { JobDetail } from "@/pages/JobDetail";
import { Stats } from "@/pages/Stats";

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }): string =>
  `rounded px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
  }`;

export function App(): ReactElement {
  return (
    <div className="min-h-screen bg-slate-100">
      <nav className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2">
        <span className="mr-4 text-base font-bold text-slate-900">QueueWatch</span>
        <NavLink to="/" end className={NAV_LINK_CLASS}>
          ダッシュボード
        </NavLink>
        <NavLink to="/stats" className={NAV_LINK_CLASS}>
          統計
        </NavLink>
        <NavLink to="/dead" className={NAV_LINK_CLASS}>
          デッドレター
        </NavLink>
      </nav>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/stats" element={<Stats />} />
          <Route path="/dead" element={<DeadLetterQueue />} />
        </Routes>
      </main>
    </div>
  );
}
