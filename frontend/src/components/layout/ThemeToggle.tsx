"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";
const STORAGE_KEY = "adrobot-theme";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    try {
      const storedTheme = window.localStorage.getItem(STORAGE_KEY);
      if (storedTheme === "light" || storedTheme === "dark") {
        setTheme(storedTheme);
        applyTheme(storedTheme);
      }
    } catch {
      applyTheme("dark");
    }
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    applyTheme(nextTheme);

    try {
      window.localStorage.setItem(STORAGE_KEY, nextTheme);
    } catch {
      // The selected theme still applies for the current page session.
    }
  }

  const label = theme === "dark" ? "Включить светлую тему" : "Включить тёмную тему";

  return (
    <button
      aria-label={label}
      className="button theme-toggle"
      title={label}
      type="button"
      onClick={toggleTheme}
    >
      <span aria-hidden="true" className="icon">
        {theme === "dark" ? "light_mode" : "dark_mode"}
      </span>
    </button>
  );
}
