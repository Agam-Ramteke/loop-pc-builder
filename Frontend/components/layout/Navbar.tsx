"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { motion } from "framer-motion";

export function Navbar() {
    const pathname = usePathname();

    const navItems = [
        { name: "Builder", href: "/builder" },
        { name: "Dashboard", href: "/dashboard" },
        { name: "Login", href: "/login" },
    ];

    return (
        <motion.nav
            initial={{ y: -100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-4 backdrop-blur-sm bg-transparent"
        >
            <Link href="/" className="text-2xl font-bold tracking-tighter hover:opacity-80 transition-opacity">
                <span className="text-[var(--primary)]">Loop</span>PCBuilder
            </Link>

            <div className="flex items-center gap-6">
                {navItems.map((item) => (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={clsx(
                            "text-sm font-medium transition-colors hover:text-[var(--primary)]",
                            pathname === item.href ? "text-[var(--primary)]" : "text-[var(--foreground)]"
                        )}
                    >
                        {item.name}
                    </Link>
                ))}
                <ThemeToggle />
            </div>
        </motion.nav>
    );
}
