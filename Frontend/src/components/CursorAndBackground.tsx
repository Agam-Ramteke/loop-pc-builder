'use client';

export default function CursorAndBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 z-[-1] overflow-hidden">
      <div className="absolute inset-x-0 top-0 h-72 bg-gradient-to-b from-neon-blue/8 via-neon-blue/4 to-transparent dark:from-neon-blue/14 dark:via-neon-blue/5" />
      <div className="absolute inset-x-0 bottom-0 h-72 bg-gradient-to-t from-neon-green/6 via-neon-green/3 to-transparent dark:from-neon-green/8 dark:via-neon-green/4" />
      <div className="absolute left-[-10%] top-[18%] h-72 w-72 rounded-full bg-neon-blue/8 blur-[120px] dark:bg-neon-blue/12" />
      <div className="absolute right-[-8%] top-[12%] h-80 w-80 rounded-full bg-neon-green/6 blur-[140px] dark:bg-neon-green/10" />
    </div>
  );
}
