'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  BriefcaseBusiness,
  CheckCircle2,
  Clapperboard,
  Gamepad2,
  Gauge,
  Layers3,
  LucideIcon,
  MonitorPlay,
  Palette,
  RefreshCw,
  Sparkles,
  Target,
  Volume2,
  WandSparkles,
} from 'lucide-react';
import { useBuild } from '@/context/BuildContext';
import { ComponentCategory } from '@/data/mockData';
import {
  buildRecommendation,
  BUILDER_BUDGET_MAX,
  BUILDER_BUDGET_MIN,
  BUILDER_BUDGET_STEP,
  BuilderPriority,
  BuilderPurpose,
  DEFAULT_BUILDER_PROFILE,
  scaleCatalogPrice,
} from '@/lib/builderRecommendations';

const BUDGET_MARKS = [BUILDER_BUDGET_MIN, 120000, 200000, BUILDER_BUDGET_MAX];

const PURPOSE_OPTIONS: Array<{
  id: BuilderPurpose;
  label: string;
  description: string;
  icon: LucideIcon;
}> = [
  { id: 'gaming', label: 'Gaming', description: 'Frame rate and upgrade room.', icon: Gamepad2 },
  { id: 'work', label: 'Workstation', description: 'Productivity-first starting point.', icon: BriefcaseBusiness },
  { id: 'creative', label: 'Creator', description: 'Edit, render, and media work.', icon: Clapperboard },
  { id: 'streaming', label: 'Streaming', description: 'Gaming plus multitasking headroom.', icon: MonitorPlay },
];

const PRIORITY_OPTIONS: Array<{
  id: BuilderPriority;
  label: string;
  icon: LucideIcon;
}> = [
  { id: 'performance', label: 'Raw performance', icon: Target },
  { id: 'value', label: 'Value conscious', icon: Gauge },
  { id: 'quiet', label: 'Low noise', icon: Volume2 },
  { id: 'future-ready', label: 'Future ready', icon: Sparkles },
  { id: 'rgb', label: 'RGB and showcase', icon: Palette },
  { id: 'creator-ready', label: 'Creator friendly', icon: Layers3 },
];

function formatInr(value: number) {
  return `INR ${Math.round(value).toLocaleString('en-IN')}`;
}

function formatBudgetShort(value: number) {
  if (value >= 100000) {
    const lakhs = value / 100000;
    return `INR ${Number.isInteger(lakhs) ? lakhs.toFixed(0) : lakhs.toFixed(1)}L`;
  }

  return `INR ${(value / 1000).toFixed(0)}K`;
}

export default function RecommendationWorkspace() {
  const router = useRouter();
  const [profile, setProfile] = useState(DEFAULT_BUILDER_PROFILE);
  const [hasPreview, setHasPreview] = useState(false);
  const { build, replaceBuild, addComponent } = useBuild();

  const recommendation = useMemo(() => buildRecommendation(profile), [profile]);
  const draftApplied = recommendation.picks.every(
    (pick) => build[pick.category]?.id === pick.component.id,
  );

  const handleChoose = (category: ComponentCategory) => {
    router.push(`/browse?category=${encodeURIComponent(category)}`);
  };

  const handlePriorityToggle = (priority: BuilderPriority) => {
    setProfile((current) => ({
      ...current,
      priorities: current.priorities.includes(priority)
        ? current.priorities.filter((entry) => entry !== priority)
        : [...current.priorities, priority],
    }));
  };

  const handleApplyRecommendation = () => {
    replaceBuild(recommendation.picks.map((pick) => pick.component));
    setHasPreview(true);
    router.push('/builder/custom');
  };

  return (
    <div className="container mx-auto flex min-h-[calc(100vh-6rem)] items-center px-4 py-6 md:py-8">
      <section className="relative overflow-hidden rounded-[32px] border border-border-gray bg-background shadow-[0_25px_80px_rgba(0,0,0,0.35)] xl:h-[calc(100vh-8rem)]">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -left-20 top-0 h-64 w-64 rounded-full bg-orange-500/10 blur-[90px]" />
          <div className="absolute -right-20 bottom-0 h-72 w-72 rounded-full bg-orange-400/8 blur-[120px]" />
        </div>

        <div className="relative grid gap-5 p-5 md:p-6 xl:h-full xl:grid-cols-[0.96fr_1.04fr] xl:gap-5 xl:p-6">
          <div className="flex flex-col gap-4 xl:min-h-0">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-500">
                <WandSparkles className="h-3.5 w-3.5" />
                Recommendation
              </span>
              <Link
                href="/builder"
                className="inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-400 transition-colors hover:text-foreground"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to builder hub
              </Link>
            </div>

            <div className="max-w-3xl">
              <h1 className="text-3xl font-heading font-extrabold tracking-tight text-foreground md:text-4xl">
                Get a guided starting build.
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-400 md:text-base">
                Set your brief here, then move to the custom build page when you are ready to tweak parts.
              </p>
            </div>

            <div className="rounded-[26px] border border-border-gray bg-background p-4 backdrop-blur-xl md:p-5 xl:flex-1 xl:min-h-0 xl:overflow-hidden">
              <div className="flex flex-col gap-4 xl:h-full xl:min-h-0">
                <div className="flex flex-col gap-4 xl:min-h-0 xl:flex-1 xl:overflow-y-auto xl:pr-1">
                  <div>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Budget target</p>
                      <h3 className="mt-1 text-2xl font-heading font-bold text-foreground">{formatInr(profile.budget)}</h3>
                    </div>
                    <span className="rounded-full border border-border-gray bg-background/80 px-3 py-1 text-xs font-semibold text-gray-300">
                      {recommendation.tierLabel} tier
                    </span>
                  </div>

                  <div className="mt-5">
                    <input
                      type="range"
                      min={BUILDER_BUDGET_MIN}
                      max={BUILDER_BUDGET_MAX}
                      step={BUILDER_BUDGET_STEP}
                      value={profile.budget}
                      onChange={(event) =>
                        setProfile((current) => ({
                          ...current,
                          budget: Number.parseInt(event.target.value, 10),
                        }))
                      }
                      className="recommendation-slider h-2 w-full appearance-none rounded-full"
                    />
                    <div className="mt-3 flex items-center justify-between text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">
                      {BUDGET_MARKS.map((mark) => (
                        <span key={mark}>{formatBudgetShort(mark)}</span>
                      ))}
                    </div>
                  </div>
                  </div>

                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Primary purpose</p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {PURPOSE_OPTIONS.map((option) => {
                        const isActive = profile.purpose === option.id;

                        return (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() =>
                              setProfile((current) => ({
                                ...current,
                                purpose: option.id,
                              }))
                            }
                            className={`rounded-[18px] border p-3 text-left transition-all duration-300 ${
                              isActive
                                ? 'border-orange-500/40 bg-orange-500/10 shadow-[0_0_40px_rgba(249,115,22,0.08)]'
                                : 'border-border-gray bg-background/60 hover:border-foreground/20 hover:bg-background/80'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              <div
                                className={`flex h-9 w-9 items-center justify-center rounded-xl ${
                                  isActive ? 'bg-orange-500/20 text-orange-500' : 'bg-white/5 text-gray-400'
                                }`}
                              >
                                <option.icon className="h-4 w-4" />
                              </div>
                              <div>
                                <h4 className="font-semibold text-foreground">{option.label}</h4>
                                <p className="mt-0.5 text-xs leading-5 text-gray-500">{option.description}</p>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Priorities</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {PRIORITY_OPTIONS.map((option) => {
                        const isActive = profile.priorities.includes(option.id);

                        return (
                          <button
                            key={option.id}
                            type="button"
                            onClick={() => handlePriorityToggle(option.id)}
                            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-semibold transition-all duration-300 ${
                              isActive
                              ? 'border-orange-500/40 bg-orange-500/10 text-orange-500'
                              : 'border-border-gray bg-background/70 text-gray-400 hover:border-foreground/20 hover:text-foreground'
                            }`}
                          >
                            <option.icon className="h-4 w-4" />
                            {option.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label
                      htmlFor="builder-preferences"
                      className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500"
                    >
                      Preferences and notes
                    </label>
                    <textarea
                      id="builder-preferences"
                      value={profile.preferences}
                      onChange={(event) =>
                        setProfile((current) => ({
                          ...current,
                          preferences: event.target.value,
                        }))
                      }
                      placeholder="Quiet, white theme, 4K editing, ray tracing..."
                      className="mt-3 min-h-20 w-full rounded-[20px] border border-border-gray bg-background/70 px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-gray-500 focus:border-neon-blue/50"
                    />
                  </div>
                </div>

                <div className="sticky bottom-0 z-10 -mx-1 mt-auto border-t border-border-gray/70 bg-mid-gray/95 px-1 pt-3 backdrop-blur-md">
                  <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  <button
                    type="button"
                    onClick={() => setHasPreview(true)}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl bg-orange-500 px-5 py-3 text-sm font-bold text-black transition-all duration-300 hover:bg-orange-400"
                  >
                    <WandSparkles className="h-4 w-4" />
                    Generate
                  </button>

                  <Link
                    href="/builder/custom"
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-border-gray bg-background/80 px-5 py-3 text-sm font-bold text-foreground transition-all duration-300 hover:border-foreground/20 hover:bg-mid-gray"
                  >
                    Open custom build
                  </Link>

                  <button
                    type="button"
                    onClick={() => {
                      setProfile(DEFAULT_BUILDER_PROFILE);
                      setHasPreview(false);
                    }}
                    className="inline-flex items-center justify-center gap-2 rounded-2xl border border-border-gray bg-transparent px-5 py-3 text-sm font-semibold text-gray-400 transition-all duration-300 hover:border-foreground/20 hover:text-foreground"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reset
                  </button>
                </div>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border border-border-gray bg-background/90 p-4 backdrop-blur-xl md:p-5 xl:flex xl:min-h-0 xl:flex-col">
            {!hasPreview ? (
              <div className="flex min-h-[420px] flex-1 flex-col items-center justify-center rounded-[24px] border border-dashed border-border-gray bg-mid-gray/40 px-6 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 text-gray-400">
                  <BrainCircuit className="h-7 w-7" />
                </div>
                <h2 className="mt-5 text-2xl font-heading font-bold text-foreground">Ready to recommend</h2>
                <p className="mt-3 max-w-md text-sm leading-6 text-gray-400">
                  Generate a brief-driven draft, then send it straight to the custom build page.
                </p>
              </div>
            ) : (
              <div className="flex flex-1 flex-col gap-4 xl:min-h-0">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="inline-flex items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-500">
                      <Sparkles className="h-3.5 w-3.5" />
                      Guided recommendation
                    </span>
                    {draftApplied && (
                      <span className="inline-flex items-center gap-2 rounded-full border border-border-gray bg-mid-gray/70 px-3 py-1 text-xs font-semibold text-gray-300">
                        <CheckCircle2 className="h-3.5 w-3.5 text-orange-500" />
                        Draft already applied
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="max-w-xl">
                      <h2 className="text-2xl font-heading font-bold text-foreground md:text-3xl">{recommendation.title}</h2>
                      <p className="mt-2 text-sm leading-6 text-gray-400">{recommendation.summary}</p>
                    </div>

                    <div className="flex gap-2 self-start">
                      <button
                        type="button"
                        onClick={handleApplyRecommendation}
                        disabled={draftApplied}
                        className="inline-flex items-center justify-center gap-2 rounded-2xl bg-foreground px-4 py-2.5 text-sm font-bold text-background transition-all duration-300 hover:bg-white/90 disabled:cursor-default disabled:opacity-50"
                      >
                        <ArrowRight className="h-4 w-4" />
                        {draftApplied ? 'Applied' : 'Apply to custom'}
                      </button>

                      <Link
                        href="/builder/custom"
                        className="inline-flex items-center justify-center gap-2 rounded-2xl border border-border-gray bg-mid-gray/70 px-4 py-2.5 text-sm font-bold text-foreground transition-all duration-300 hover:border-foreground/20 hover:bg-mid-gray"
                      >
                        Custom page
                      </Link>
                    </div>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-[20px] border border-border-gray bg-mid-gray/70 p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Budget fit</p>
                    <div className="mt-1.5 text-lg font-bold text-foreground">{recommendation.tierLabel}</div>
                  </div>
                  <div className="rounded-[20px] border border-border-gray bg-mid-gray/70 p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Estimated total</p>
                    <div className="mt-1.5 text-lg font-bold text-foreground">{formatInr(recommendation.estimatedPrice)}</div>
                  </div>
                  <div className="rounded-[20px] border border-border-gray bg-mid-gray/70 p-3.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">Projected draw</p>
                    <div className="mt-1.5 text-lg font-bold text-foreground">{recommendation.estimatedWattage} W</div>
                  </div>
                </div>

                <div className="rounded-[20px] border border-border-gray bg-mid-gray/50 p-4">
                  <div className="flex flex-wrap gap-2">
                    {recommendation.highlights.map((highlight) => (
                      <span
                        key={highlight}
                        className="rounded-full border border-border-gray bg-background/60 px-3 py-1.5 text-xs leading-5 text-gray-300"
                      >
                        {highlight}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="space-y-2.5 xl:min-h-0 xl:flex-1 xl:overflow-y-auto xl:pr-1">
                  {recommendation.picks.map((pick) => {
                    const isSelected = build[pick.category]?.id === pick.component.id;

                    return (
                      <div
                        key={pick.category}
                        className="rounded-[20px] border border-border-gray bg-mid-gray/50 p-4 transition-colors duration-300 hover:border-foreground/20"
                      >
                        <div className="flex flex-col gap-3">
                          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                            <div>
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">{pick.category}</span>
                                <span className="rounded-full border border-orange-500/20 bg-orange-500/10 px-2.5 py-1 text-[11px] font-semibold text-orange-500">
                                  {pick.fitLabel}
                                </span>
                              </div>
                              <h3 className="mt-2 text-base font-bold text-foreground">{pick.component.name}</h3>
                            </div>

                            <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400">
                              <span>{pick.component.provider}</span>
                              <span className="h-1 w-1 rounded-full bg-gray-600" />
                              <span>{formatInr(scaleCatalogPrice(pick.component.price))}</span>
                            </div>
                          </div>

                          <p className="line-clamp-2 text-sm leading-6 text-gray-400">{pick.reason}</p>

                          <div className="flex flex-col gap-2 sm:flex-row">
                            <button
                              type="button"
                              onClick={() => addComponent(pick.component)}
                              className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-bold transition-all duration-300 ${
                                isSelected
                                  ? 'border border-orange-500/30 bg-orange-500/10 text-orange-500'
                                  : 'bg-foreground text-background hover:bg-white/90'
                              }`}
                            >
                              {isSelected ? <CheckCircle2 className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}
                              {isSelected ? 'Selected' : 'Use part'}
                            </button>

                            <button
                              type="button"
                              onClick={() => handleChoose(pick.category)}
                              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-border-gray bg-background/70 px-4 py-2.5 text-sm font-semibold text-foreground transition-all duration-300 hover:border-foreground/20 hover:bg-mid-gray"
                            >
                              Browse alternatives
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
