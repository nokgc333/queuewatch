/** ルーティング定義（仕様書§6.1 画面一覧、ADR-0006: react-router使用）。 */
import { lazy, Suspense, type ReactElement } from "react";
import { Link, Route, Switch, useRoute } from "wouter";

import { Dashboard } from "@/pages/Dashboard";

/** 初期バンドルを小さくするため、ダッシュボード以外の画面(統計は Chart.js を含む)は、開くときに読み込む。 */
const JobDetail = lazy(() =>
  import("@/pages/JobDetail").then((m) => ({ default: m.JobDetail })),
);
const Stats = lazy(() =>
  import("@/pages/Stats").then((m) => ({ default: m.Stats })),
);
const DeadLetterQueue = lazy(() =>
  import("@/pages/DeadLetterQueue").then((m) => ({
    default: m.DeadLetterQueue,
  })),
);

function NavItem({
  to,
  exact = false,
  children,
}: {
  to: string;
  exact?: boolean;
  children: string;
}): ReactElement {
  const [isMatch] = useRoute(exact ? to : `${to}/*?`);
  return (
    <Link
      href={to}
      aria-current={isMatch ? "page" : undefined}
      className={`rounded px-3 py-1.5 text-sm font-medium ${
        isMatch ? "bg-blue-700 text-white" : "text-slate-700 hover:bg-slate-100"
      }`}
    >
      {children}
    </Link>
  );
}

export function App(): ReactElement {
  return (
    <div className="min-h-screen bg-slate-100">
      <nav
        aria-label="メインメニュー"
        className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2"
      >
        <span className="mr-4 text-base font-bold text-slate-900">
          QueueWatch
        </span>
        <NavItem to="/" exact>
          ダッシュボード
        </NavItem>
        <NavItem to="/stats">統計</NavItem>
        <NavItem to="/dead">デッドレター</NavItem>
      </nav>
      <main>
        <Suspense
          fallback={
            <p role="status" className="p-4 text-slate-600">
              読み込み中…
            </p>
          }
        >
          <Switch>
            <Route path="/" component={Dashboard} />
            <Route path="/jobs/:id" component={JobDetail} />
            <Route path="/stats" component={Stats} />
            <Route path="/dead" component={DeadLetterQueue} />
          </Switch>
        </Suspense>
      </main>
    </div>
  );
}
