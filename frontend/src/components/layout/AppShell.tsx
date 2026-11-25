import type { ReactNode } from "react";

type AppSection = "create" | "edit";

type Props = {
  activeSection: AppSection;
  children: ReactNode;
  onSectionChange: (section: AppSection) => void;
};

export function AppShell({ activeSection, children, onSectionChange }: Props) {
  const title = activeSection === "create" ? "Новая кампания" : "Управление офферами";

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Основная навигация">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span className="brand-name">adrobot</span>
        </div>
        <p className="nav-label">Рабочее пространство</p>
        <button
          className={`nav-item ${activeSection === "create" ? "active" : ""}`}
          type="button"
          aria-current={activeSection === "create" ? "page" : undefined}
          onClick={() => onSectionChange("create")}
        >
          <span className="icon" aria-hidden="true">add_circle</span>
          <span className="nav-text">Создать кампанию</span>
        </button>
        <button
          className={`nav-item ${activeSection === "edit" ? "active" : ""}`}
          type="button"
          aria-current={activeSection === "edit" ? "page" : undefined}
          onClick={() => onSectionChange("edit")}
        >
          <span className="icon" aria-hidden="true">tune</span>
          <span className="nav-text">Редактор офферов</span>
        </button>
        <p className="sidebar-status">Keitaro · API v1</p>
      </aside>

      <main className="main">
        <header className="topbar">
          <strong>{title}</strong>
          <span>Рабочее пространство</span>
        </header>
        <div className="content">{children}</div>
      </main>
    </div>
  );
}
