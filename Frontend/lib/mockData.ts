export const MOCK_RECOMMENDATIONS = [
    {
        id: 'budget-1',
        name: 'Starter Loop',
        type: 'Budget Build',
        price: 850,
        specs: {
            cpu: 'Intel Core i5-13400F',
            gpu: 'NVIDIA RTX 4060',
            ram: '16GB DDR5',
            storage: '1TB NVMe SSD',
        },
        image: '/images/budget-pc.png' // Placeholder
    },
    {
        id: 'performance-1',
        name: 'Velocity Loop',
        type: 'Performance Build',
        price: 1800,
        specs: {
            cpu: 'AMD Ryzen 7 7800X3D',
            gpu: 'NVIDIA RTX 4070 Ti Super',
            ram: '32GB DDR5',
            storage: '2TB NVMe SSD',
        },
        image: '/images/perf-pc.png'
    },
    {
        id: 'creator-1',
        name: 'Infinity Loop',
        type: 'Creator Build',
        price: 3200,
        specs: {
            cpu: 'Intel Core i9-14900K',
            gpu: 'NVIDIA RTX 4090',
            ram: '64GB DDR5',
            storage: '4TB NVMe SSD',
        },
        image: '/images/creator-pc.png'
    }
];

export const MOCK_PARTS = {
    cpu: [
        { id: 'cpu-1', name: 'Intel Core i5-13400F', price: 200, cores: 10 },
        { id: 'cpu-2', name: 'AMD Ryzen 7 7800X3D', price: 400, cores: 8 },
        { id: 'cpu-3', name: 'Intel Core i9-14900K', price: 600, cores: 24 },
    ],
    gpu: [
        { id: 'gpu-1', name: 'NVIDIA RTX 4060', price: 300, vram: '8GB' },
        { id: 'gpu-2', name: 'NVIDIA RTX 4070 Ti Super', price: 800, vram: '16GB' },
        { id: 'gpu-3', name: 'NVIDIA RTX 4090', price: 1600, vram: '24GB' },
    ]
};
