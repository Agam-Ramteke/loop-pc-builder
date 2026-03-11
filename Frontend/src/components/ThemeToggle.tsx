'use client';

import { useTheme } from 'next-themes';
import { Moon, Sun, Laptop } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex items-center bg-dark-gray/60 backdrop-blur-md rounded-full shadow-[0_0_15px_rgba(66,133,244,0.3)] border border-border-gray/50 overflow-hidden p-1">
      <button
        onClick={() => setTheme('light')}
        className={`p-2 rounded-full transition-all ${theme === 'light' ? 'bg-white/20 text-neon-blue shadow-inner' : 'text-gray-400 hover:text-foreground hover:bg-white/10'}`}
        title="Light Mode"
      >
        <Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme('system')}
        className={`p-2 rounded-full transition-all ${theme === 'system' ? 'bg-white/20 text-neon-blue shadow-inner' : 'text-gray-400 hover:text-foreground hover:bg-white/10'}`}
        title="System Preference"
      >
        <Laptop className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={`p-2 rounded-full transition-all ${theme === 'dark' ? 'bg-white/20 text-neon-blue shadow-inner' : 'text-gray-400 hover:text-foreground hover:bg-white/10'}`}
        title="Dark Mode"
      >
        <Moon className="w-4 h-4" />
      </button>
    </div>
  );
}
