'use client';

import Link from 'next/link';
import { ArrowRight, BrainCircuit, Boxes, WandSparkles } from 'lucide-react';

const PATHS = [
  {
    href: '/builder/recommendation',
    label: 'Guided Recommendation',
    title: 'Recommend my build',
    description: 'Set your budget, purpose, and priorities, then get a starting draft.',
    icon: BrainCircuit,
    tone: 'border-neon-blue/30 bg-neon-blue/10 text-neon-blue',
  },
  {
    href: '/builder/custom',
    label: 'Custom Build',
    title: 'Choose parts manually',
    description: 'Open the slot-by-slot builder directly and hand-pick every component.',
    icon: Boxes,
    tone: 'border-border-gray bg-mid-gray/60 text-gray-300',
  },
];

export default function BuilderPage() {
  return (
    <div className="container mx-auto px-4 py-8 md:py-10">
      <section className="relative overflow-hidden rounded-[32px] border border-border-gray bg-background shadow-[0_25px_80px_rgba(0,0,0,0.35)]">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -left-20 top-0 h-64 w-64 rounded-full bg-neon-blue/10 blur-[90px]" />
          <div className="absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-neon-green/10 blur-[120px]" />
        </div>

        <div className="relative grid gap-6 p-6 md:p-8 xl:grid-cols-[0.82fr_1.18fr] xl:items-center xl:p-10">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-neon-blue/30 bg-neon-blue/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-neon-blue">
              <WandSparkles className="h-3.5 w-3.5" />
              Start Building
            </div>
            <h1 className="mt-5 text-4xl font-heading font-extrabold tracking-tight text-foreground md:text-5xl">
              Pick your builder flow.
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-7 text-gray-400 md:text-base">
              Guided recommendations and custom part selection now live on separate pages. Use this builder entry point to switch between them.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {PATHS.map((path) => (
              <Link
                key={path.href}
                href={path.href}
                className="group rounded-[28px] border border-border-gray bg-mid-gray/60 p-5 transition-all duration-300 hover:border-foreground/20 hover:bg-mid-gray"
              >
                <div className={`inline-flex h-12 w-12 items-center justify-center rounded-2xl border ${path.tone}`}>
                  <path.icon className="h-5 w-5" />
                </div>
                <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">{path.label}</p>
                <h2 className="mt-2 text-2xl font-bold text-foreground">{path.title}</h2>
                <p className="mt-3 text-sm leading-6 text-gray-400">{path.description}</p>
                <div className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-foreground">
                  Open flow
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
