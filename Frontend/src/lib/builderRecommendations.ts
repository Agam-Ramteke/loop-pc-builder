import { Component, ComponentCategory, mockComponents } from '@/data/mockData';

export type BuilderPurpose = 'gaming' | 'work' | 'creative' | 'streaming';
export type BuilderPriority =
  | 'performance'
  | 'value'
  | 'quiet'
  | 'future-ready'
  | 'rgb'
  | 'creator-ready';

export interface BuilderProfile {
  budget: number;
  purpose: BuilderPurpose;
  priorities: BuilderPriority[];
  preferences: string;
}

export interface RecommendationPick {
  category: ComponentCategory;
  component: Component;
  fitLabel: string;
  reason: string;
}

export interface RecommendationResult {
  title: string;
  summary: string;
  tierLabel: string;
  highlights: string[];
  picks: RecommendationPick[];
  estimatedPrice: number;
  estimatedWattage: number;
}

export const BUILDER_BUDGET_MIN = 60000;
export const BUILDER_BUDGET_MAX = 350000;
export const BUILDER_BUDGET_STEP = 5000;
export const DISPLAY_PRICE_MULTIPLIER = 100;

export const DEFAULT_BUILDER_PROFILE: BuilderProfile = {
  budget: 150000,
  purpose: 'gaming',
  priorities: ['performance', 'future-ready'],
  preferences: '',
};

const CATEGORY_ORDER: ComponentCategory[] = [
  'CPU',
  'CPU Cooler',
  'Motherboard',
  'Memory',
  'Storage',
  'Video Card',
  'Case',
  'Power Supply',
];

const COMPONENT_TAGS: Record<string, string[]> = {
  'cpu-1': ['gaming', 'streaming', 'performance', 'future-ready'],
  'cpu-2': ['work', 'creative', 'performance', 'creator-ready'],
  'cpu-3': ['gaming', 'value', 'quiet'],
  'cpu-4': ['work', 'creative', 'value'],
  'gpu-1': ['gaming', 'creative', 'performance', 'future-ready'],
  'gpu-2': ['gaming', 'creative', 'value', 'creator-ready'],
  'gpu-3': ['gaming', 'streaming', 'value', 'performance'],
  'mobo-1': ['gaming', 'future-ready', 'rgb'],
  'mobo-2': ['work', 'creative', 'performance', 'creator-ready'],
  'mobo-3': ['value'],
  'ram-1': ['value', 'quiet'],
  'ram-2': ['performance', 'rgb', 'future-ready'],
  'stor-1': ['creative', 'performance', 'future-ready', 'creator-ready'],
  'stor-2': ['gaming', 'value', 'quiet'],
  'case-1': ['gaming', 'rgb', 'performance'],
  'case-2': ['creative', 'rgb', 'future-ready'],
  'psu-1': ['value', 'quiet'],
  'psu-2': ['performance', 'future-ready'],
  'cool-1': ['performance', 'rgb'],
  'cool-2': ['value', 'quiet'],
};

const COMPONENT_BASE_REASON: Record<string, string> = {
  'cpu-1': 'High-cache AM5 chip that keeps gaming latency low and leaves room for later upgrades.',
  'cpu-2': 'Heavy multi-core option for creator workloads, parallel tools, and mixed work sessions.',
  'cpu-3': 'Efficient value CPU that keeps the total budget under control without losing responsiveness.',
  'cpu-4': 'Balanced Intel option for productivity-focused builds when stock returns.',
  'gpu-1': 'Flagship GPU pick for 4K, ray tracing, and long-term headroom.',
  'gpu-2': 'Strong creator-and-gaming card with plenty of VRAM for demanding projects.',
  'gpu-3': 'Excellent upper-midrange gaming card for high-refresh 1440p builds.',
  'mobo-1': 'Feature-rich AM5 board with a clean upgrade path and a polished enthusiast feature set.',
  'mobo-2': 'Well-equipped Intel board for heavier workstations and creator-focused configs.',
  'mobo-3': 'Lower-cost AM5 board that keeps the platform accessible when it is available.',
  'ram-1': 'Reliable 32 GB DDR5 kit that fits value and low-noise builds well.',
  'ram-2': 'Faster DDR5 kit that suits performance tuning and showcase builds.',
  'stor-1': 'Fast 2 TB NVMe drive with enough space for large games, media, or project files.',
  'stor-2': 'Value-focused Gen4 SSD that keeps the build snappy without overspending.',
  'case-1': 'Airflow-first chassis that works well for performance-focused full-size parts.',
  'case-2': 'Showcase case with strong presentation value for premium desktop setups.',
  'psu-1': 'Quiet 850 W unit with enough room for most balanced builds.',
  'psu-2': 'Higher-headroom supply for flagship GPUs, future upgrades, and sustained load.',
  'cool-1': '360 mm AIO that suits hotter CPUs and RGB-first aesthetics.',
  'cool-2': 'High-value air cooler that keeps noise and cost in check.',
};

const PURPOSE_PRIORITY_BONUS: Record<BuilderPurpose, string[]> = {
  gaming: ['gaming', 'performance'],
  work: ['work', 'creator-ready'],
  creative: ['creative', 'creator-ready'],
  streaming: ['gaming', 'streaming', 'performance'],
};

const PRIORITY_MATCHES: Record<BuilderPriority, string[]> = {
  performance: ['performance'],
  value: ['value'],
  quiet: ['quiet'],
  'future-ready': ['future-ready'],
  rgb: ['rgb'],
  'creator-ready': ['creative', 'creator-ready'],
};

function getBudgetTier(budget: number) {
  if (budget < 100000) {
    return { id: 'value', label: 'Value-first', targetRank: 0.2 };
  }

  if (budget < 220000) {
    return { id: 'balanced', label: 'Balanced', targetRank: 0.55 };
  }

  return { id: 'enthusiast', label: 'Enthusiast', targetRank: 1 };
}

function getCategoryPool(category: ComponentCategory) {
  return mockComponents
    .filter((component) => component.category === category)
    .sort((left, right) => left.price - right.price);
}

function getPriceRank(component: Component) {
  const pool = getCategoryPool(component.category);
  if (pool.length <= 1) {
    return 1;
  }

  const index = pool.findIndex((item) => item.id === component.id);
  return index / (pool.length - 1);
}

function parseNumericValue(value: string | undefined) {
  if (!value) {
    return 0;
  }

  const match = value.match(/\d+/);
  return match ? Number.parseInt(match[0], 10) : 0;
}

function getPreferenceFlags(preferences: string) {
  const normalized = preferences.toLowerCase();

  return {
    wantsQuiet: normalized.includes('quiet') || normalized.includes('silent') || normalized.includes('low noise'),
    wantsRgb: normalized.includes('rgb') || normalized.includes('lighting') || normalized.includes('showcase'),
    wantsCreatorBias:
      normalized.includes('editing') ||
      normalized.includes('render') ||
      normalized.includes('creator') ||
      normalized.includes('3d'),
  };
}

function getCandidateScore(
  component: Component,
  profile: BuilderProfile,
  category: ComponentCategory,
  selectedCpu: Component | null,
  requiredPsuWattage: number,
) {
  const tags = COMPONENT_TAGS[component.id] ?? [];
  const tier = getBudgetTier(profile.budget);
  const priceRank = getPriceRank(component);
  const preferenceFlags = getPreferenceFlags(profile.preferences);

  let score = 60;
  score += Math.max(0, 14 - Math.abs(priceRank - tier.targetRank) * 20);
  score += component.inStock ? 8 : -20;

  for (const tag of PURPOSE_PRIORITY_BONUS[profile.purpose]) {
    if (tags.includes(tag)) {
      score += 10;
    }
  }

  for (const priority of profile.priorities) {
    if (PRIORITY_MATCHES[priority].some((tag) => tags.includes(tag))) {
      score += 9;
    }
  }

  if (preferenceFlags.wantsQuiet && tags.includes('quiet')) {
    score += 8;
  }

  if (preferenceFlags.wantsRgb && tags.includes('rgb')) {
    score += 8;
  }

  if (preferenceFlags.wantsCreatorBias && (tags.includes('creative') || tags.includes('creator-ready'))) {
    score += 8;
  }

  if (category === 'Motherboard' && selectedCpu) {
    if (component.specs.Socket === selectedCpu.specs.Socket) {
      score += 26;
    } else {
      score -= 50;
    }
  }

  if (category === 'CPU Cooler' && selectedCpu) {
    const isLiquid = component.specs.Type === 'Liquid';
    if (selectedCpu.wattage >= 180 && isLiquid) {
      score += 16;
    }
    if (selectedCpu.wattage <= 120 && !isLiquid) {
      score += 10;
    }
  }

  if (category === 'Power Supply') {
    const wattage = parseNumericValue(component.specs.Wattage);
    if (wattage >= requiredPsuWattage) {
      score += 18;
    } else {
      score -= 40;
    }
  }

  return score;
}

function pickBestComponent(
  category: ComponentCategory,
  profile: BuilderProfile,
  selectedCpu: Component | null = null,
  requiredPsuWattage = 0,
) {
  const pool = mockComponents.filter((component) => component.category === category);

  return [...pool].sort((left, right) => {
    const leftScore = getCandidateScore(left, profile, category, selectedCpu, requiredPsuWattage);
    const rightScore = getCandidateScore(right, profile, category, selectedCpu, requiredPsuWattage);
    return rightScore - leftScore;
  })[0];
}

function buildReason(
  component: Component,
  profile: BuilderProfile,
  category: ComponentCategory,
  selectedCpu: Component | null,
  requiredPsuWattage: number,
) {
  const tags = COMPONENT_TAGS[component.id] ?? [];
  const extras: string[] = [];

  if (category === 'Motherboard' && selectedCpu) {
    extras.push(`It matches the ${selectedCpu.specs.Socket} platform.`);
  }

  if (category === 'Power Supply') {
    extras.push(`It covers the projected ${requiredPsuWattage} W requirement with upgrade room.`);
  }

  if (profile.priorities.includes('quiet') && tags.includes('quiet')) {
    extras.push('It also lines up with a quieter tuning target.');
  }

  if (profile.priorities.includes('future-ready') && tags.includes('future-ready')) {
    extras.push('It keeps more headroom for future upgrades.');
  }

  if (profile.priorities.includes('rgb') && tags.includes('rgb')) {
    extras.push('It fits a stronger visual and lighting-focused build style.');
  }

  return [COMPONENT_BASE_REASON[component.id], ...extras].join(' ');
}

function getFitLabel(component: Component, profile: BuilderProfile) {
  const tags = COMPONENT_TAGS[component.id] ?? [];
  const directMatches = profile.priorities.filter((priority) =>
    PRIORITY_MATCHES[priority].some((tag) => tags.includes(tag)),
  ).length;

  if (tags.includes(profile.purpose) && directMatches >= 1) {
    return 'Strong fit';
  }

  if (tags.includes(profile.purpose) || directMatches >= 1) {
    return 'Good fit';
  }

  return 'Flexible fit';
}

function buildHeadline(profile: BuilderProfile, tierLabel: string) {
  const purposeLabelMap: Record<BuilderPurpose, string> = {
    gaming: 'Gaming',
    work: 'Workstation',
    creative: 'Creator',
    streaming: 'Streaming',
  };

  return `${tierLabel} ${purposeLabelMap[profile.purpose]} build`;
}

function buildSummary(profile: BuilderProfile) {
  const summaryMap: Record<BuilderPurpose, string> = {
    gaming: 'GPU-first tuning with enough CPU headroom for smooth frame pacing.',
    work: 'CPU-forward tuning for productivity and workstation loads.',
    creative: 'Balanced creator stack with fast storage and strong multi-core throughput.',
    streaming: 'A balanced stream-ready stack for gaming plus background encode.',
  };

  return summaryMap[profile.purpose];
}

export function scaleCatalogPrice(price: number) {
  return Math.round(price * DISPLAY_PRICE_MULTIPLIER);
}

export function buildRecommendation(profile: BuilderProfile): RecommendationResult {
  const cpu = pickBestComponent('CPU', profile);
  const gpu = pickBestComponent('Video Card', profile);
  const motherboard = pickBestComponent('Motherboard', profile, cpu);
  const cooler = pickBestComponent('CPU Cooler', profile, cpu);
  const memory = pickBestComponent('Memory', profile);
  const storage = pickBestComponent('Storage', profile);
  const pcCase = pickBestComponent('Case', profile);
  const projectedWattage = cpu.wattage + gpu.wattage + motherboard.wattage + memory.wattage + storage.wattage + cooler.wattage + pcCase.wattage;
  const requiredPsuWattage = projectedWattage >= 700 || profile.priorities.includes('future-ready') ? 1000 : 850;
  const powerSupply = pickBestComponent('Power Supply', profile, cpu, requiredPsuWattage);

  const selectedComponents = new Map<ComponentCategory, Component>([
    ['CPU', cpu],
    ['CPU Cooler', cooler],
    ['Motherboard', motherboard],
    ['Memory', memory],
    ['Storage', storage],
    ['Video Card', gpu],
    ['Case', pcCase],
    ['Power Supply', powerSupply],
  ]);

  const picks = CATEGORY_ORDER.map((category) => {
    const component = selectedComponents.get(category)!;
    return {
      category,
      component,
      fitLabel: getFitLabel(component, profile),
      reason: buildReason(component, profile, category, cpu, requiredPsuWattage),
    };
  });

  const estimatedPrice = picks.reduce((sum, pick) => sum + scaleCatalogPrice(pick.component.price), 0);
  const estimatedWattage = picks.reduce((sum, pick) => sum + pick.component.wattage, 0);
  const tier = getBudgetTier(profile.budget);
  const highlightPriority = profile.priorities[0];

  return {
    title: buildHeadline(profile, tier.label),
    summary: buildSummary(profile),
    tierLabel: tier.label,
    highlights: [
      `${tier.label} tier for ${profile.purpose}.`,
      `${estimatedWattage} W projected draw.`,
      highlightPriority
        ? `${highlightPriority.replace('-', ' ')} stays front and center.`
        : 'Ready for manual refinement.',
    ],
    picks,
    estimatedPrice,
    estimatedWattage,
  };
}
