export type ComponentCategory = 'CPU' | 'CPU Cooler' | 'Motherboard' | 'Memory' | 'Storage' | 'Video Card' | 'Case' | 'Power Supply';

export interface Component {
  id: string;
  category: ComponentCategory;
  name: string;
  brand: string;
  price: number;
  provider: 'PrimeABGB' | 'MD Computers' | 'EliteHubs' | string;
  originalPrice?: number;  // original/MRP before discount
  discountPercent?: number; // discount percentage (e.g. 30 means 30% off)
  image: string;
  inStock: boolean;
  wattage: number; // estimated power draw in Watts
  specs: Record<string, string>;
}

export const mockComponents: Component[] = [
  // CPUs
  { id: "cpu-1", category: "CPU", name: "AMD Ryzen 7 7800X3D", brand: "AMD", price: 349.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 120, specs: { Cores: "8", Threads: "16", BaseClock: "4.2GHz", Socket: "AM5" } },
  { id: "cpu-2", category: "CPU", name: "Intel Core i9-13900K", brand: "Intel", price: 549.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 253, specs: { Cores: "24", Threads: "32", BaseClock: "3.0GHz", Socket: "LGA1700" } },
  { id: "cpu-3", category: "CPU", name: "AMD Ryzen 5 7600", brand: "AMD", price: 199.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1591405351990-4726e331f141?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 65, specs: { Cores: "6", Threads: "12", BaseClock: "3.8GHz", Socket: "AM5" } },
  { id: "cpu-4", category: "CPU", name: "Intel Core i5-13600K", brand: "Intel", price: 289.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?q=80&w=400&auto=format&fit=crop", inStock: false, wattage: 181, specs: { Cores: "14", Threads: "20", BaseClock: "3.5GHz", Socket: "LGA1700" } },

  // GPUs
  { id: "gpu-1", category: "Video Card", name: "NVIDIA GeForce RTX 4090", brand: "NVIDIA", price: 1599.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1591488320449-011701bb6704?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 450, specs: { VRAM: "24GB GDDR6X", CoreClock: "2.23GHz" } },
  { id: "gpu-2", category: "Video Card", name: "AMD Radeon RX 7900 XTX", brand: "AMD", price: 999.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1591488320449-011701bb6704?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 355, specs: { VRAM: "24GB GDDR6", CoreClock: "2.3GHz" } },
  { id: "gpu-3", category: "Video Card", name: "ASUS TUF Gaming RTX 4070 Ti", brand: "ASUS", price: 799.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1591488320449-011701bb6704?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 285, specs: { VRAM: "12GB GDDR6X", CoreClock: "2.61GHz" } },

  // Motherboards
  { id: "mobo-1", category: "Motherboard", name: "ASUS ROG Strix B650E-F", brand: "ASUS", price: 259.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 30, specs: { Socket: "AM5", FormFactor: "ATX" } },
  { id: "mobo-2", category: "Motherboard", name: "MSI MAG Z790 TOMAHAWK WIFI", brand: "MSI", price: 289.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 35, specs: { Socket: "LGA1700", FormFactor: "ATX" } },
  { id: "mobo-3", category: "Motherboard", name: "Gigabyte B650 AORUS ELITE AX", brand: "Gigabyte", price: 199.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=400&auto=format&fit=crop", inStock: false, wattage: 30, specs: { Socket: "AM5", FormFactor: "ATX" } },

  // Memory
  { id: "ram-1", category: "Memory", name: "Corsair Vengeance 32GB (2x16GB) DDR5", brand: "Corsair", price: 114.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1563770660941-20978e870e26?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 10, specs: { Speed: "6000MHz", Modules: "2x16GB", Type: "DDR5" } },
  { id: "ram-2", category: "Memory", name: "G.Skill Trident Z5 RGB 32GB", brand: "G.Skill", price: 129.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1563770660941-20978e870e26?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 10, specs: { Speed: "6400MHz", Modules: "2x16GB", Type: "DDR5" } },

  // Storage
  { id: "stor-1", category: "Storage", name: "Samsung 990 PRO 2TB NVMe SSD", brand: "Samsung", price: 189.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1597848212624-a1fb16eadef0?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 8, specs: { Capacity: "2TB", Interface: "PCIe 4.0 x4" } },
  { id: "stor-2", category: "Storage", name: "WD Black SN850X 1TB", brand: "Western Digital", price: 89.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1597848212624-a1fb16eadef0?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 7, specs: { Capacity: "1TB", Interface: "PCIe 4.0 x4" } },

  // Case
  { id: "case-1", category: "Case", name: "NZXT H9 Flow", brand: "NZXT", price: 159.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 15, specs: { FormFactor: "ATX Mid Tower", SidePanel: "Tempered Glass" } },
  { id: "case-2", category: "Case", name: "Lian Li O11 Dynamic EVO", brand: "Lian Li", price: 149.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: false, wattage: 15, specs: { FormFactor: "ATX Mid Tower", SidePanel: "Tempered Glass" } },

  // Power Supply
  { id: "psu-1", category: "Power Supply", name: "Corsair RM850x (2021) 850W", brand: "Corsair", price: 139.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 0, specs: { Wattage: "850W", Efficiency: "80+ Gold", Modular: "Full" } },
  { id: "psu-2", category: "Power Supply", name: "EVGA SuperNOVA 1000 G6", brand: "EVGA", price: 179.99, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 0, specs: { Wattage: "1000W", Efficiency: "80+ Gold", Modular: "Full" } },

  // CPU Cooler
  { id: "cool-1", category: "CPU Cooler", name: "NZXT Kraken Elite 360", brand: "NZXT", price: 279.99, provider: "MD Computers", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 15, specs: { Type: "Liquid", RadiatorSize: "360mm" } },
  { id: "cool-2", category: "CPU Cooler", name: "Thermalright Peerless Assassin 120", brand: "Thermalright", price: 34.90, provider: "PrimeABGB", image: "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?q=80&w=400&auto=format&fit=crop", inStock: true, wattage: 5, specs: { Type: "Air", Height: "157mm" } }
];
