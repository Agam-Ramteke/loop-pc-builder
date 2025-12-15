"use client";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { MOCK_RECOMMENDATIONS } from "@/lib/mockData";
import { Cpu, Zap, Activity } from "lucide-react"; // Icons
import Link from "next/link";
import { motion } from "framer-motion";

export default function DashboardPage() {
    return (
        <div className="container mx-auto px-4 py-8 space-y-12">
            <div className="space-y-2">
                <h1 className="text-4xl font-bold tracking-tight">Welcome back, User.</h1>
                <p className="text-[var(--muted-foreground)] text-lg">
                    Your personalized configuration loops are ready.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {MOCK_RECOMMENDATIONS.map((pc, index) => (
                    <motion.div
                        key={pc.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.1 }}
                    >
                        <Card className="h-full hover:border-[var(--primary)] transition-colors group">
                            <CardHeader>
                                <div className="flex justify-between items-start">
                                    <CardTitle className="text-xl group-hover:text-[var(--primary)] transition-colors">{pc.name}</CardTitle>
                                    {pc.type === 'Budget Build' && <Zap size={20} className="text-[var(--secondary)]" />}
                                    {pc.type === 'Performance Build' && <Activity size={20} className="text-[var(--primary)]" />}
                                    {pc.type === 'Creator Build' && <Cpu size={20} className="text-purple-500" />}
                                </div>
                                <CardDescription>{pc.type}</CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="h-32 bg-[var(--accent)]/30 rounded-md flex items-center justify-center overflow-hidden relative">
                                    {/* Placeholder for 3D Thumbnail */}
                                    <div className="absolute inset-0 bg-gradient-to-t from-[var(--background)] to-transparent opacity-50" />
                                    <span className="z-10 text-sm text-[var(--muted-foreground)] font-mono">3D PREVIEW</span>
                                </div>
                                <ul className="space-y-2 text-sm">
                                    <li className="flex justify-between border-b border-[var(--border)] pb-1">
                                        <span className="text-[var(--muted-foreground)]">CPU</span>
                                        <span>{pc.specs.cpu}</span>
                                    </li>
                                    <li className="flex justify-between border-b border-[var(--border)] pb-1">
                                        <span className="text-[var(--muted-foreground)]">GPU</span>
                                        <span>{pc.specs.gpu}</span>
                                    </li>
                                    <li className="flex justify-between border-b border-[var(--border)] pb-1">
                                        <span className="text-[var(--muted-foreground)]">RAM</span>
                                        <span>{pc.specs.ram}</span>
                                    </li>
                                </ul>
                            </CardContent>
                            <CardFooter className="flex justify-between items-center">
                                <span className="text-lg font-bold">${pc.price}</span>
                                <Button disabled variant="outline" size="sm">
                                    View Specs
                                </Button>
                            </CardFooter>
                        </Card>
                    </motion.div>
                ))}
            </div>

            <div className="flex justify-center pt-8">
                <Link href="/builder">
                    <Button size="lg" variant="neon" className="px-12">
                        Start New Loop
                    </Button>
                </Link>
            </div>
        </div>
    );
}
