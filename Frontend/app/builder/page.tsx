import { Sidebar } from "@/components/layout/Sidebar";
import { Card } from "@/components/ui/Card";

export default function BuilderPage() {
    return (
        <div className="flex h-[calc(100vh-80px)] overflow-hidden">
            <Sidebar className="hidden md:flex" />
            <div className="flex-1 p-8 overflow-auto">
                <div className="max-w-5xl mx-auto space-y-8">
                    <div className="flex items-center justify-between">
                        <h1 className="text-3xl font-bold">Custom Loop Configuration</h1>
                        <span className="text-sm text-[var(--muted-foreground)]">Step 1 of 4</span>
                    </div>

                    {/* Placeholder Content Area */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-6">
                            {/* Placeholder Component Lists */}
                            <Card className="p-6 h-64 flex items-center justify-center border-dashed border-2 border-[var(--border)] bg-transparent">
                                <span className="text-[var(--muted-foreground)]">Component Selection Interface (Placeholder)</span>
                            </Card>
                            <Card className="p-6 h-64 flex items-center justify-center border-dashed border-2 border-[var(--border)] bg-transparent">
                                <span className="text-[var(--muted-foreground)]">Component Details & Compatibility</span>
                            </Card>
                        </div>

                        <div className="lg:col-span-1">
                            {/* Live Preview / Spec Sheet Placeholder */}
                            <Card className="h-full min-h-[400px] border-[var(--primary)]/20 bg-[var(--card)]/50">
                                <div className="p-6 space-y-4">
                                    <h3 className="font-semibold text-[var(--primary)]">Current Specs</h3>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-[var(--muted-foreground)]">CPU</span>
                                            <span>Not Selected</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--muted-foreground)]">GPU</span>
                                            <span>Not Selected</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--muted-foreground)]">RAM</span>
                                            <span>Not Selected</span>
                                        </div>
                                    </div>
                                    <div className="pt-4 border-t border-[var(--border)]">
                                        <div className="flex justify-between font-bold text-lg">
                                            <span>Total</span>
                                            <span>$0.00</span>
                                        </div>
                                    </div>
                                </div>
                            </Card>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
