'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react';
import { useBuild } from '@/context/BuildContext';
import { ComponentCategory } from '@/data/mockData';
import BuildSlot from '@/components/BuildSlot';
import CompatibilityBanner from '@/components/CompatibilityBanner';
import { scaleCatalogPrice } from '@/lib/builderRecommendations';

const BUILD_CATEGORIES: ComponentCategory[] = [
  'CPU',
  'CPU Cooler',
  'Motherboard',
  'Memory',
  'Storage',
  'Video Card',
  'Case',
  'Power Supply',
];

function formatInr(value: number) {
  return `INR ${Math.round(value).toLocaleString('en-IN')}`;
}

export default function CustomBuildWorkspace() {
  const router = useRouter();
  const { build, totalPrice, totalWattage, clearBuild } = useBuild();
  const filledSlots = Object.values(build).filter(Boolean).length;

  const handleChoose = (category: ComponentCategory) => {
    router.push(`/browse?category=${encodeURIComponent(category)}`);
  };

  return (
    <div className="container mx-auto px-4 py-8 md:py-10">
      <section className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/60 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-400">
                  Custom build
                </span>
                <Link
                  href="/builder"
                  className="inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-400 transition-colors hover:text-foreground"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to builder hub
                </Link>
              </div>
              <h1 className="mt-4 text-3xl font-heading font-extrabold tracking-tight text-foreground md:text-4xl">
                Choose your parts manually.
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-400">
                Browse each component category directly, or jump to the recommendation page for a guided starting draft.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/builder/recommendation"
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-neon-blue px-5 py-3 text-sm font-bold text-black transition-all duration-300 hover:bg-neon-blue/90"
              >
                <Sparkles className="h-4 w-4" />
                Get recommendations
              </Link>

              <button
                type="button"
                onClick={clearBuild}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-red-500/30 bg-red-500/10 px-5 py-3 text-sm font-semibold text-red-400 transition-all duration-300 hover:bg-red-500/15"
              >
                Clear build
              </button>
            </div>
          </div>

          <CompatibilityBanner />

          <div className="overflow-hidden rounded-[28px] border border-border-gray bg-mid-gray/40">
            <div className="hidden border-b border-border-gray px-5 py-4 text-sm font-semibold text-gray-500 sm:flex">
              <div className="w-48">Component</div>
              <div className="flex-grow">Selection</div>
            </div>

            <div className="space-y-3 p-4 md:p-5">
              {BUILD_CATEGORIES.map((category) => (
                <BuildSlot
                  key={category}
                  category={category}
                  component={build[category]}
                  onChoose={handleChoose}
                />
              ))}
            </div>
          </div>
        </div>

        <aside className="w-full">
          <div className="sticky top-24 rounded-[28px] border border-border-gray bg-background/90 p-6 backdrop-blur-xl">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Build summary</p>
              <h2 className="mt-2 text-2xl font-heading font-bold text-foreground">Current workspace</h2>
            </div>

            <div className="mt-6 grid gap-3">
              <div className="rounded-[22px] border border-border-gray bg-mid-gray/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Filled slots</p>
                <div className="mt-2 text-2xl font-bold text-foreground">
                  {filledSlots} / {BUILD_CATEGORIES.length}
                </div>
              </div>

              <div className="rounded-[22px] border border-border-gray bg-mid-gray/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Catalog total</p>
                <div className="mt-2 text-2xl font-bold text-neon-green">{formatInr(scaleCatalogPrice(totalPrice))}</div>
              </div>

              <div className="rounded-[22px] border border-border-gray bg-mid-gray/70 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Estimated wattage</p>
                <div className="mt-2 text-2xl font-bold text-neon-blue">{totalWattage} W</div>
              </div>
            </div>

            <div className="mt-6 rounded-[22px] border border-border-gray bg-mid-gray/50 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Need a faster start?</p>
              <p className="mt-3 text-sm leading-6 text-gray-400">
                The recommendation page can draft a full build here without adding a new navbar item.
              </p>
            </div>

            <div className="mt-6 flex flex-col gap-3">
              <Link
                href="/builder/recommendation"
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-foreground px-5 py-3.5 text-sm font-bold text-background transition-all duration-300 hover:bg-white/90"
              >
                Open recommendation page
                <ArrowRight className="h-4 w-4" />
              </Link>

              <Link
                href="/browse"
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-border-gray bg-transparent px-5 py-3.5 text-sm font-semibold text-foreground transition-all duration-300 hover:border-foreground/20 hover:bg-mid-gray"
              >
                Explore all components
              </Link>
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
