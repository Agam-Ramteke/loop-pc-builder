"use client";

import { cn } from "@/components/ui/Button";
import { Cpu, HardDrive, Calculator, Save, MemoryStick, MonitorPlay } from "lucide-react";
import { useState } from "react";

const steps = [
    { id: 'cpu', name: 'Processor', icon: Cpu },
    { id: 'gpu', name: 'Graphics', icon: MonitorPlay },
    { id: 'ram', name: 'Memory', icon: MemoryStick },
    { id: 'storage', name: 'Storage', icon: HardDrive },
    { id: 'summary', name: 'Summary', icon: Calculator },
];

export function Sidebar({ className }: { className?: string }) {
    const [activeStep, setActiveStep] = useState('cpu');

    return (
        <aside className={cn("w-64 border-r border-[var(--glass-border)] bg-[var(--glass-bg)] backdrop-blur-md flex flex-col h-full", className)}>
            <div className="p-6">
                <h2 className="text-lg font-semibold tracking-tight text-[var(--primary)]">Builder Config</h2>
                <p className="text-xs text-[var(--muted-foreground)]">Select your components</p>
            </div>
            <nav className="flex-1 px-4 space-y-2">
                {steps.map((step) => {
                    const Icon = step.icon;
                    const isActive = activeStep === step.id;
                    return (
                        <button
                            key={step.id}
                            onClick={() => setActiveStep(step.id)}
                            className={cn(
                                "flex items-center w-full gap-3 px-4 py-3 text-sm font-medium rounded-md transition-colors",
                                isActive
                                    ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                                    : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                            )}
                        >
                            <Icon size={18} />
                            {step.name}
                        </button>
                    );
                })}
            </nav>
            <div className="p-4 border-t border-[var(--border)]">
                <button className="flex items-center justify-center w-full gap-2 px-4 py-2 text-sm font-medium text-[var(--foreground)] bg-[var(--accent)] rounded-md hover:bg-[var(--accent)]/80 transition-colors">
                    <Save size={16} />
                    Save Loop
                </button>
            </div>
        </aside>
    );
}
