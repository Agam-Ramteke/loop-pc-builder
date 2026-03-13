export interface BuildGuide {
  id: string;
  title: string;
  description: string;
  tier: 'budget' | 'midrange' | 'enthusiast';
  totalPrice: number;
  components: { category: string; name: string; price: number }[];
  color: string;
  icon: string;
}

export const buildGuides: BuildGuide[] = [
  {
    id: 'guide-budget',
    title: 'Budget Gaming',
    description: 'Great 1080p gaming without breaking the bank. Perfect for esports titles and casual gaming.',
    tier: 'budget',
    totalPrice: 45000,
    color: '#34A853',
    icon: '💰',
    components: [
      { category: 'CPU', name: 'Intel Core i5-13400F', price: 12500 },
      { category: 'GPU', name: 'AMD Radeon RX 7600', price: 22000 },
      { category: 'RAM', name: '16GB DDR4 3200MHz', price: 2800 },
      { category: 'Storage', name: '500GB NVMe SSD', price: 3000 },
      { category: 'PSU', name: '550W 80+ Bronze', price: 3200 },
      { category: 'Case', name: 'Ant Esports ICE-112', price: 1500 },
    ],
  },
  {
    id: 'guide-midrange',
    title: 'Mid-Range Beast',
    description: 'Smooth 1440p gaming and solid productivity. The sweet spot for most builders.',
    tier: 'midrange',
    totalPrice: 105000,
    color: '#4285F4',
    icon: '⚡',
    components: [
      { category: 'CPU', name: 'AMD Ryzen 7 7800X3D', price: 28000 },
      { category: 'GPU', name: 'NVIDIA RTX 4070 Super', price: 48000 },
      { category: 'RAM', name: '32GB DDR5 6000MHz', price: 8500 },
      { category: 'Storage', name: '1TB NVMe Gen4 SSD', price: 6500 },
      { category: 'Cooler', name: 'DeepCool AK620', price: 3500 },
      { category: 'PSU', name: '750W 80+ Gold', price: 6500 },
      { category: 'Case', name: 'Lian Li Lancool 216', price: 4000 },
    ],
  },
  {
    id: 'guide-enthusiast',
    title: 'Enthusiast Rig',
    description: 'No compromises. 4K gaming, content creation, and everything in between.',
    tier: 'enthusiast',
    totalPrice: 250000,
    color: '#EA4335',
    icon: '🔥',
    components: [
      { category: 'CPU', name: 'AMD Ryzen 9 9950X', price: 45000 },
      { category: 'GPU', name: 'NVIDIA RTX 4090', price: 130000 },
      { category: 'RAM', name: '64GB DDR5 6400MHz', price: 18000 },
      { category: 'Storage', name: '2TB NVMe Gen5 SSD', price: 16000 },
      { category: 'Cooler', name: 'NZXT Kraken Elite 360', price: 15000 },
      { category: 'PSU', name: '1000W 80+ Platinum', price: 14000 },
      { category: 'Case', name: 'NZXT H9 Flow', price: 12000 },
    ],
  },
];
