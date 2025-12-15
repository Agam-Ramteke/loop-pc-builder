import Link from "next/link";
import { Button } from "@/components/ui/Button";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] text-center px-4">
      <div className="max-w-4xl space-y-8 animate-in fade-in zoom-in duration-1000 slide-in-from-bottom-10">
        <h1 className="text-6xl md:text-8xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-[var(--foreground)] to-[var(--primary)] drop-shadow-lg">
          Build PCs that <br />
          <span className="text-[var(--primary)] text-glow">think in loops.</span>
        </h1>

        <p className="text-xl md:text-2xl text-[var(--foreground)]/80 max-w-2xl mx-auto font-light">
          The interface to a thinking machine. Experience the future of PC configuration.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-6 pt-8">
          <Link href="/builder">
            <Button size="lg" variant="neon" className="text-lg px-12 py-6 rounded-full">
              Build My PC
            </Button>
          </Link>
          <Link href="/dashboard">
            <Button size="lg" variant="ghost" className="text-lg px-8 py-6 rounded-full">
              View Dashboard
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
