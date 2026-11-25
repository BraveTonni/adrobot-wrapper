import type { ReactNode } from "react";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

type AppSection = "create" | "edit";

type Props = {
  activeSection: AppSection;
  children: ReactNode;
  onSectionChange: (section: AppSection) => void;
  title: string;
};

export function AppShell({
  activeSection,
  children,
  onSectionChange,
  title,
}: Props) {
  return (
    <div className="app-shell">
      <AppSidebar
        activeSection={activeSection}
        onSectionChange={onSectionChange}
      />
      <main className="main">
        <AppHeader title={title} />
        <div className="content">
          {children}
          <AppFooter />
        </div>
      </main>
    </div>
  );
}
