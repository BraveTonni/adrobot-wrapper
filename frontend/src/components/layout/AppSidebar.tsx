import { Icon } from "@/components/Icon";

type AppSection = "create" | "edit";

type Props = {
  activeSection: AppSection;
  onSectionChange: (section: AppSection) => void;
};

export function AppSidebar({ activeSection, onSectionChange }: Props) {
  return (
    <aside className="sidebar" aria-label="Основная навигация">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          A
        </span>
        <span className="brand-name">adrobot</span>
      </div>

      <nav aria-label="Рабочее пространство">
        <p className="nav-label">Кампании</p>
        <button
          aria-current={activeSection === "create" ? "page" : undefined}
          className={`nav-item ${activeSection === "create" ? "active" : ""}`}
          type="button"
          onClick={() => onSectionChange("create")}
        >
          <Icon name="add-circle" />
          <span className="nav-text">Создать кампанию</span>
        </button>
        <button
          aria-current={activeSection === "edit" ? "page" : undefined}
          className={`nav-item ${activeSection === "edit" ? "active" : ""}`}
          type="button"
          onClick={() => onSectionChange("edit")}
        >
          <Icon name="tune" />
          <span className="nav-text">Редактор офферов</span>
        </button>
      </nav>

      <p className="sidebar-footer">Keitaro · API v1</p>
    </aside>
  );
}
