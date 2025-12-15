import * as React from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "default" | "outline" | "ghost" | "neon";
    size?: "default" | "sm" | "lg";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "default", size = "default", ...props }, ref) => {
        return (
            <button
                className={cn(
                    "inline-flex items-center justify-center rounded-md text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50",
                    {
                        "bg-[var(--primary)] text-[var(--primary-foreground)] shadow hover:bg-[var(--primary)]/90":
                            variant === "default",
                        "border border-[var(--input)] bg-transparent shadow-sm hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]":
                            variant === "outline",
                        "hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]":
                            variant === "ghost",
                        "bg-transparent border border-[var(--primary)] text-[var(--primary)] shadow-[0_0_10px_var(--primary)] hover:shadow-[0_0_20px_var(--primary)] hover:bg-[var(--primary)]/10":
                            variant === "neon",
                        "h-9 px-4 py-2": size === "default",
                        "h-8 rounded-md px-3 text-xs": size === "sm",
                        "h-10 rounded-md px-8": size === "lg",
                    },
                    className
                )}
                ref={ref}
                {...props}
            />
        );
    }
);
Button.displayName = "Button";

export { Button, cn };
