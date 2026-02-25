import React from "react";
import { useTheme } from "../context/ThemeContext";
import "./ThemeToggle.scss";

const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      className={`theme-toggle theme-toggle-${theme}`}
      onClick={toggleTheme}
    >
      {theme === "dark" ? "Dark" : "Light"}
    </button>
  );
};

export default ThemeToggle;

