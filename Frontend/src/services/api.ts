import { mockComponents, Component, ComponentCategory } from "../data/mockData";

/**
 * Live API Service connected to Next.js API Routes querying MongoDB
 */

export interface PaginatedComponents {
  data: Component[];
  totalCount: number;
  page: number;
  totalPages: number;
}

export const getComponents = async (
  category?: ComponentCategory | 'All',
  searchQuery?: string,
  sortBy?: 'priceAsc' | 'priceDesc' | 'name',
  page: number = 1,
  limit: number = 20
): Promise<PaginatedComponents> => {
  try {
    const params = new URLSearchParams();
    if (category && category !== 'All') params.append('category', category);
    if (searchQuery) params.append('search', searchQuery);
    if (sortBy) params.append('sort', sortBy);
    if (page) params.append('page', page.toString());
    if (limit) params.append('limit', limit.toString());
    
    const res = await fetch(`/api/components?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch components');
    
    return await res.json();
  } catch (error) {
    console.error("Error fetching components:", error);
    return { data: [], totalCount: 0, page: 1, totalPages: 1 };
  }
};

export const getComponentById = async (id: string): Promise<Component | undefined> => {
  try {
    const res = await fetch(`/api/components/${id}`);
    if (!res.ok) throw new Error('Product not found');
    return await res.json();
  } catch (error) {
    console.error("Error fetching component by ID:", error);
    return undefined;
  }
};

export interface CompatibilityReport {
  isValid: boolean;
  warnings: string[];
  errors: string[];
}

export const checkCompatibility = async (buildItems: Component[]): Promise<CompatibilityReport> => {
  await new Promise((resolve) => setTimeout(resolve, 400));
  
  const report: CompatibilityReport = {
    isValid: true,
    warnings: [],
    errors: [],
  };

  const cpu = buildItems.find(c => c.category === 'CPU');
  const mobo = buildItems.find(c => c.category === 'Motherboard');
  const psu = buildItems.find(c => c.category === 'Power Supply');

  // Hardcoded mock rules:
  if (cpu && mobo) {
    if (cpu.specs.Socket !== mobo.specs.Socket) {
      report.isValid = false;
      report.errors.push(`CPU socket ${cpu.specs.Socket} is incompatible with Motherboard socket ${mobo.specs.Socket}.`);
    } else if (cpu.specs.Socket === 'AM5') {
      report.warnings.push('Warning: Motherboard may require a BIOS update for this CPU.');
    }
  }

  if (psu) {
    const totalWattage = buildItems.reduce((sum, item) => sum + (item.wattage || 0), 0);
    const psuWattage = parseInt(psu.specs.Wattage?.replace('W', '') || '0', 10);
    if (psuWattage > 0 && totalWattage > psuWattage * 0.8) {
       report.warnings.push(`Warning: System wattage (${totalWattage}W) is approaching PSU capacity.`);
    }
  }

  return report;
};
