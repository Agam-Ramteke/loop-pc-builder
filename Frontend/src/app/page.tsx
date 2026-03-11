'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { ArrowRight, Zap, Target, Cpu } from 'lucide-react';
import { Component } from '@/data/mockData';
import ProductCard from '@/components/ProductCard';
import { useAnimationFrame } from 'framer-motion';

import { useTheme } from 'next-themes';

function CanvasStarfield() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    const resize = () => {
       const rect = canvas.parentElement?.getBoundingClientRect();
       if (rect) {
           canvas.width = rect.width;
           canvas.height = rect.height;
       } else {
           canvas.width = window.innerWidth;
           canvas.height = window.innerHeight;
       }
    };
    resize();
    window.addEventListener('resize', resize);

    let mouseX = canvas.width / 2;
    let mouseY = canvas.height / 2;
    
    const handleMouseMove = (e: MouseEvent) => {
       const rect = canvas.getBoundingClientRect();
       mouseX = e.clientX - rect.left;
       mouseY = e.clientY - rect.top;
    };
    window.addEventListener('mousemove', handleMouseMove);

    const colors = [
      [66, 133, 244],   // Google Blue
      [161, 66, 244],   // Purple/Violet
      [234, 67, 53],    // Salmon/Red
      [251, 188, 5],    // Golden Yellow
      [52, 168, 83],    // Green (sparse)
    ];

    let currentX = mouseX;
    let currentY = mouseY;

    const numParticles = 800;
    const particles: any[] = [];
    for (let i = 0; i < numParticles; i++) {
        // Skew roughly half the particles toward standard Google Blue for branding unity
        const color = Math.random() > 0.5 ? colors[0] : colors[Math.floor(Math.random() * colors.length)];
        particles.push({
            offsetX: Math.random() * 2000,
            offsetY: Math.random() * 2000,
            baseSize: Math.random() * 1.5 + 1.2,
            floatOffset: Math.random() * Math.PI * 2,
            c: color
        });
    }

    let time = 0;
    const render = () => {
        time += 1;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Smoothly follow the mouse with a slight lag
        currentX += (mouseX - currentX) * 0.1;
        currentY += (mouseY - currentY) * 0.1;

        const isDark = document.documentElement.classList.contains('dark');
        
        // Grid size slightly larger than typical 1080p max viewing radius to prevent pop-in
        const gridW = 1800;
        const gridH = 1800;

        particles.forEach((p) => {
            // Infinite continuous wrap-around relative to the cursor position
            let relX = (p.offsetX - currentX) % gridW;
            if (relX < 0) relX += gridW;
            if (relX > gridW / 2) relX -= gridW;
            const anchorX = currentX + relX;

            let relY = (p.offsetY - currentY) % gridH;
            if (relY < 0) relY += gridH;
            if (relY > gridH / 2) relY -= gridH;
            const anchorY = currentY + relY;

            // Brownian floating motion (stationary but breathing)
            const floatX = Math.sin(time * 0.02 + p.floatOffset) * 12;
            const floatY = Math.cos(time * 0.015 + p.floatOffset) * 12;
            
            const targetX = anchorX + floatX;
            const targetY = anchorY + floatY;

            const dx = targetX - currentX;
            const dy = targetY - currentY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            // Culling optimization outside safe visual radius
            if (dist > 850) return;

            const angle = Math.atan2(dy, dx);

            // Antigravity repel for creating the large hollow eye around the cursor
            let pushStrength = 0;
            if (dist < 200) {
                pushStrength = (200 - dist) * 0.5;
            }

            const finalX = targetX + Math.cos(angle) * pushStrength;
            const finalY = targetY + Math.sin(angle) * pushStrength;

            // Distance based on heavily repelled final coordinates
            const rDx = finalX - currentX;
            const rDy = finalY - currentY;
            const rDist = Math.sqrt(rDx * rDx + rDy * rDy);

            // Distance-based Opacity Fadeout
            let alpha = 1 - (rDist / 800);
            if (rDist < 200) {
                alpha *= Math.max(0, (rDist - 120) / 80); // Fades completely in the hollow deadzone
            }
            alpha = Math.max(0, Math.min(1, alpha));
            if (alpha <= 0.01) return;

            alpha *= (isDark ? 0.9 : 0.6);

            // Gentle pulsing logic over time
            const pulse = (Math.sin(time * 0.03 + p.floatOffset) + 1) / 2;
            alpha *= 0.6 + 0.4 * pulse;

            // Radial dashed stretching (extends outwards along the vector from the focal point)
            const dashLength = Math.min(18, Math.max(0, (rDist - 180) * 0.05));

            ctx.beginPath();
            ctx.fillStyle = `rgba(${p.c[0]}, ${p.c[1]}, ${p.c[2]}, ${alpha})`;
            ctx.strokeStyle = `rgba(${p.c[0]}, ${p.c[1]}, ${p.c[2]}, ${alpha})`;

            if (isDark && rDist < 350) {
                ctx.shadowBlur = 10;
                ctx.shadowColor = `rgba(${p.c[0]}, ${p.c[1]}, ${p.c[2]}, 1)`;
            } else {
                ctx.shadowBlur = 0;
            }

            if (dashLength < 1) {
                ctx.beginPath();
                ctx.arc(finalX, finalY, p.baseSize, 0, Math.PI * 2);
                ctx.fill();
            } else {
                // Radial alignment aligns precisely to the angle from cursor to the particle
                const drawAngle = Math.atan2(rDy, rDx);
                const halfLength = dashLength / 2;
                
                // Draw a standard tabular/tubular dash. Constant thickness.
                ctx.beginPath();
                ctx.moveTo(finalX - Math.cos(drawAngle) * halfLength, finalY - Math.sin(drawAngle) * halfLength);
                ctx.lineTo(finalX + Math.cos(drawAngle) * halfLength, finalY + Math.sin(drawAngle) * halfLength);
                ctx.lineWidth = p.baseSize * 1.5; // Slightly thicker tubular line
                ctx.lineCap = "round";
                ctx.stroke();
            }
        });

        ctx.globalAlpha = 1;
        animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
        cancelAnimationFrame(animationFrameId);
        window.removeEventListener('resize', resize);
        window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [mounted, resolvedTheme]);

  return (
    <canvas 
      ref={canvasRef} 
      className={`absolute inset-0 z-[5] pointer-events-none opacity-90 transition-opacity duration-1000 ${mounted && resolvedTheme === 'dark' ? 'mix-blend-screen' : 'mix-blend-normal'}`} 
    />
  );
}

function HeroSection() {
  return (
    <section 
      className="relative w-full h-screen flex flex-col items-center justify-center border-b border-border-gray overflow-hidden group bg-dark-gray"
    >
      {/* Abstract background styling */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[50%] -right-[10%] w-[80%] h-[150%] bg-neon-blue/5 rounded-full blur-[120px]" />
        <div className="absolute -bottom-[50%] -left-[10%] w-[60%] h-[120%] bg-neon-green/5 rounded-full blur-[100px]" />
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiIC8+CjxwYXRoIGQ9Ik0wIDM5aDQwTTAgMHY0MEgwem0zOSAwVjAiIHN0cm9rZT0icmdiYSgxMDAsMTAwLDEwMCwwLjA1KSIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiAvPgo8L3N2Zz4=')] [mask-image:linear-gradient(to_bottom,white,transparent)]" />
      </div>

      <CanvasStarfield />

      <div className="container mx-auto px-4 relative z-10 flex flex-col items-center text-center -mt-10">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border-gray bg-background/50 text-neon-blue text-sm mb-8 backdrop-blur-md shadow-[0_0_15px_rgba(66,133,244,0.15)]">
          <Zap className="w-4 h-4" />
          <span className="font-medium tracking-wide">Next-Gen Builder Engine</span>
        </div>
        <h1 className="text-6xl md:text-8xl lg:text-9xl font-heading font-extrabold tracking-tighter mb-8 leading-[1.1]">
          Build Your <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-blue via-blue-400 to-neon-blue/80 inline-block pb-3">Dream PC</span>
        </h1>
        <p className="max-w-[700px] text-gray-500 text-xl md:text-2xl mb-12 font-sans font-light">
          Intelligent component aggregation, real-time compatibility checking, and exact market pricing.
        </p>
        <div className="flex flex-col sm:flex-row gap-6 w-full sm:w-auto">
          <Link 
            href="/builder" 
            className="group flex items-center justify-center gap-3 h-16 px-10 rounded-2xl bg-foreground text-background font-heading font-bold text-lg hover:scale-105 transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_40px_rgba(66,133,244,0.4)]"
          >
            Start Building Now
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link 
            href="/browse" 
            className="flex items-center justify-center h-16 px-10 rounded-2xl bg-transparent text-foreground font-heading font-bold text-lg border border-border-gray hover:bg-foreground/5 dark:hover:bg-white/5 transition-all hover:border-gray-400 hover:scale-105 backdrop-blur-md"
          >
            Browse Components
          </Link>
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      icon: <Target className="w-8 h-8 text-neon-blue" />,
      title: "Smart Compatibility",
      desc: "Our engine automatically checks socket types, wattage, and physical dimensions to ensure your parts fit perfectly.",
      gradient: "from-neon-blue/40"
    },
    {
      icon: <Cpu className="w-8 h-8 text-neon-green" />,
      title: "Massive Selection",
      desc: "Aggregating data from top retailers to give you access to thousands of parts, updated in real-time.",
      gradient: "from-neon-green/40"
    },
    {
      icon: <Zap className="w-8 h-8 text-neon-blue" />,
      title: "Live Pricing",
      desc: "Find the lowest prices and never overpay for your hardware with our daily price tracking algorithms.",
      gradient: "from-neon-blue/40"
    }
  ];

  return (
    <section className="py-32 bg-background relative overflow-hidden">
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiIGZpbGw9Im5vbmUiIC8+CjxwYXRoIGQ9Ik0wIDM5aDQwTTAgMHY0MEgwem0zOSAwVjAiIHN0cm9rZT0icmdiYSgxMDAsMTAwLDEwMCwwLjAyKSIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiAvPgo8L3N2Zz4=')] [mask-image:linear-gradient(to_bottom,transparent,white,transparent)] pointer-events-none" />
      
      <div className="container mx-auto px-4 relative z-10">
        <div className="text-center mb-20 md:mb-32">
          <h2 className="text-4xl md:text-6xl lg:text-7xl font-heading font-extrabold tracking-tight mb-6">Engineered for <span className="text-foreground/30">Excellence</span></h2>
          <p className="text-xl md:text-2xl text-gray-500 max-w-2xl mx-auto font-light">Every feature designed to provide a frictionless build experience from conception to ordering.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
          {features.map((feature, i) => (
            <div key={i} className="group relative rounded-[2rem] bg-gradient-to-b from-border-gray/50 to-transparent p-[1px] overflow-hidden hover:from-border-gray transition-colors duration-700">
              <div className={`absolute inset-0 bg-gradient-to-b ${feature.gradient} to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-[60px] pointer-events-none`} />
              <div className="relative h-full bg-background rounded-[2rem] p-10 lg:p-12 flex flex-col items-start group-hover:bg-mid-gray/40 transition-colors duration-500">
                <div className="p-5 bg-mid-gray/50 rounded-2xl border border-border-gray mb-8 group-hover:scale-110 group-hover:bg-dark-gray transition-all duration-500">
                   {feature.icon}
                </div>
                <h3 className="text-3xl font-heading font-bold mb-4 text-foreground group-hover:text-neon-blue transition-colors duration-300">{feature.title}</h3>
                <p className="text-gray-500 font-sans text-lg leading-relaxed">{feature.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home() {
  const [trendingParts, setTrendingParts] = useState<Component[]>([]);

  useEffect(() => {
    let mounted = true;
    fetch('/api/components/trending')
      .then(res => res.json())
      .then(parts => {
        if (mounted) setTrendingParts(parts);
      })
      .catch(console.error);
    return () => { mounted = false; };
  }, []);

  return (
    <div className="flex flex-col min-h-screen">
      <HeroSection />
      <FeaturesSection />

      {/* Trending Components */}
      <section className="py-32 bg-dark-gray border-t border-border-gray">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-end mb-12">
            <div>
              <h2 className="text-4xl md:text-5xl font-heading font-bold mb-4">Trending Components</h2>
              <p className="text-gray-400 text-lg md:text-xl font-light">Most popular choices this week</p>
            </div>
            <Link href="/browse" className="text-neon-blue hover:text-neon-blue/80 text-lg font-medium flex items-center gap-2 group">
              View all <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 xl:gap-8">
            {trendingParts.map(part => (
               <ProductCard key={part.id} component={part} />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
