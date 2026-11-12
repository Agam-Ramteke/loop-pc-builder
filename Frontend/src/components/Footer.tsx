'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Infinity as InfinityIcon, Github, Twitter, Youtube, Mail, Bell } from 'lucide-react';

export default function Footer() {
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({ message: '', visible: false });

  const triggerToast = (msg: string) => {
    setToast({ message: msg, visible: true });
    setTimeout(() => setToast(prev => ({ ...prev, visible: false })), 3000);
  };

  return (
    <footer className="bg-background border-t border-border-gray relative">
      <div className="container mx-auto px-4 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          
          {/* Brand */}
          <div className="lg:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4 group">
              <InfinityIcon className="h-7 w-7 text-neon-blue" />
              <span className="font-heading font-bold text-lg tracking-tight text-foreground">
                Loop<span className="text-neon-blue">PC</span>
              </span>
            </Link>
            <p className="text-gray-500 text-sm leading-relaxed mb-6">
              India&apos;s smartest PC builder. Real-time pricing, compatibility checking, and the best deals — all in one place.
            </p>
            <div className="flex items-center gap-3">
              <button 
                onClick={() => triggerToast('LoopPC X (Twitter) profile coming soon!')}
                className="w-10 h-10 rounded-lg bg-mid-gray/50 border border-border-gray flex items-center justify-center text-gray-500 hover:text-white hover:bg-[#000000] hover:border-black transition-all cursor-pointer group/social"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="transition-colors">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                </svg>
              </button>
              <a 
                href="https://github.com/Agam-Ramteke/loop-pc-builder" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-10 h-10 rounded-lg bg-mid-gray/50 border border-border-gray flex items-center justify-center text-gray-500 hover:text-white hover:bg-[#24292e] hover:border-[#24292e] transition-all"
              >
                <Github className="w-5 h-5" />
              </a>
              <button 
                onClick={() => triggerToast('LoopPC YouTube channel available soon!')}
                className="w-10 h-10 rounded-lg bg-mid-gray/50 border border-border-gray flex items-center justify-center text-gray-500 hover:text-white hover:bg-[#FF0000] hover:border-[#FF0000] transition-all cursor-pointer group/social"
              >
                <Youtube className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-heading font-bold text-sm uppercase tracking-wider text-foreground mb-4">Quick Links</h4>
            <ul className="space-y-3">
              {[
                { href: '/builder', label: 'PC Builder' },
                { href: '/browse', label: 'Browse Components' },
                { href: '/browse?category=Video+Card', label: 'Graphics Cards' },
                { href: '/browse?category=CPU', label: 'Processors' },
                { href: '/browse?category=Motherboard', label: 'Motherboards' },
              ].map(link => (
                <li key={link.href}>
                  <Link href={link.href} className="text-gray-500 hover:text-neon-blue text-sm transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="font-heading font-bold text-sm uppercase tracking-wider text-foreground mb-4">Resources</h4>
            <ul className="space-y-3">
              {[
                { href: '#build-guides', label: 'Build Guides' },
                { href: '#blog', label: 'Blog' },
                { href: '#community', label: 'Community' },
                { href: '#deals', label: 'Price Drops' },
                { href: '#', label: 'Compatibility Checker' },
              ].map(link => (
                <li key={link.label}>
                  <Link href={link.href} className="text-gray-500 hover:text-neon-blue text-sm transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter */}
          <div>
            <h4 className="font-heading font-bold text-sm uppercase tracking-wider text-foreground mb-4">Stay Updated</h4>
            <p className="text-gray-500 text-sm mb-4">Get weekly price drops and build recommendations.</p>
            <div className="flex gap-2">
              <input
                type="email"
                placeholder="your@email.com"
                className="flex-1 h-10 rounded-lg border border-border-gray bg-mid-gray px-3 text-sm text-foreground placeholder:text-gray-500 focus:border-neon-blue focus:outline-none focus:ring-1 focus:ring-neon-blue transition-all"
              />
              <button className="h-10 px-4 rounded-lg bg-neon-blue text-white font-medium text-sm hover:bg-neon-blue/90 transition-colors flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-border-gray flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-gray-600 text-xs text-center sm:text-left">© 2026 LoopPC. Built for the Indian PC building community.</p>
          <div className="flex items-center gap-6 text-xs text-gray-600">
            <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors">Contact</a>
          </div>
        </div>
      </div>

      {/* Aesthetic Toast Notification */}
      <AnimatePresence>
        {toast.visible && (
          <motion.div
            initial={{ opacity: 0, y: 20, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 20, x: '-50%' }}
            className="fixed bottom-10 left-1/2 z-50 px-6 py-3 rounded-xl border border-neon-blue/30 bg-black/80 backdrop-blur-md shadow-2xl flex items-center gap-3"
          >
            <div className="w-8 h-8 rounded-full bg-neon-blue/10 flex items-center justify-center">
              <Bell className="w-4 h-4 text-neon-blue" />
            </div>
            <span className="text-sm font-medium text-white whitespace-nowrap">
              {toast.message}
            </span>
            <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-neon-blue/5 to-transparent pointer-events-none" />
          </motion.div>
        )}
      </AnimatePresence>
    </footer>
  );
}
