import { ThemeToggle } from "./ThemeToggle";

type Props = { title: string };

export function AppHeader({ title }: Props) {
  return (
    <header className="topbar">
      <strong>{title}</strong>
      <div className="topbar-actions">
        <span className="topbar-context">Рабочее пространство</span>
        <ThemeToggle />
      </div>
    </header>
  );
}
