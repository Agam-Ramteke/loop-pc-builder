'use client';

import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';

export default function CursorAndBackground() {
  const [mousePosition, setMousePosition] = useState({ x: -100, y: -100 });
  const [isHovering, setIsHovering] = useState(false);
  
  useEffect(() => {
    const updateMousePosition = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
      
      const target = e.target as HTMLElement;
      if (target && (target.tagName.toLowerCase() === 'button' || target.tagName.toLowerCase() === 'a' || target.closest('button') || target.closest('a'))) {
        setIsHovering(true);
      } else {
        setIsHovering(false);
      }
    };
    
    window.addEventListener('mousemove', updateMousePosition);
    return () => {
      window.removeEventListener('mousemove', updateMousePosition);
    };
  }, []);

  return (
    <>
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        {/* Ambient Top and Bottom Glow mimicking Antigravity */}
        <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-neon-blue/10 to-transparent dark:from-neon-blue/20"></div>
        <div className="absolute bottom-0 left-0 w-full h-[300px] bg-gradient-to-t from-neon-blue/10 to-transparent dark:from-neon-blue/20"></div>
      </div>
      

      
      {/* Trailing Soft Glow */}
      <motion.div
        className="fixed top-0 left-0 w-64 h-64 rounded-full pointer-events-none z-[99]"
        style={{
          background: 'radial-gradient(circle, rgba(66, 133, 244, 0.15) 0%, rgba(0,0,0,0) 70%)',
        }}
        animate={{
          x: mousePosition.x - 128,
          y: mousePosition.y - 128,
        }}
        transition={{
          type: 'tween',
          ease: 'easeOut',
          duration: 0.15,
        }}
      />
    </>
  );
}
