"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { motion } from "framer-motion";

export function ThemeToggle() {
    const [theme, setTheme] = useState<"light" | "dark">("dark");

    useEffect(() => {
        // Check initial preference
        const savedTheme = localStorage.getItem("theme") as "light" | "dark" | null;
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        const initial = savedTheme || (prefersDark ? "dark" : "dark"); // Default to dark as requested
        setTheme(initial);
        document.documentElement.setAttribute("data-theme", initial);
    }, []);

    const toggleTheme = () => {
        const newTheme = theme === "light" ? "dark" : "light";
        setTheme(newTheme);
        document.documentElement.setAttribute("data-theme", newTheme);
        localStorage.setItem("theme", newTheme);
    };

    return (
        <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={toggleTheme}
            className="p-3 rounded-full bg-[var(--card)] border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors backdrop-blur-md"
            aria-label="Toggle Theme"
        >
            <motion.div
                initial={false}
                animate={{ rotate: theme === "dark" ? 0 : 180 }}
                transition={{ duration: 0.3 }}
            >
                {theme === "dark" ? <Moon size={20} /> : <Sun size={20} />}
            </motion.div>
        </motion.button>
    );
}
