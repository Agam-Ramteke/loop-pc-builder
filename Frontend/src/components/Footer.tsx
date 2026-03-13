'use client';

import Link from 'next/link';
import { Infinity as InfinityIcon, Github, Twitter, Youtube, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-dark-gray border-t border-border-gray">
      <div className="container mx-auto px-4 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          
          {/* Brand */}
          <div className="lg:col-span-1">
            <Link href="/" className="flex items-center gap-2 mb-4 group">
              <InfinityIcon className="h-7 w-7 text-neon-blue" />
              <span className="font-heading font-bold text-lg tracking-tight">
                Loop<span className="text-neon-blue">PC</span>
              </span>
            </Link>
            <p className="text-gray-500 text-sm leading-relaxed mb-6">
              India&apos;s smartest PC builder. Real-time pricing, compatibility checking, and the best deals — all in one place.
            </p>
            <div className="flex items-center gap-3">
              <a href="#" className="w-9 h-9 rounded-lg bg-mid-gray border border-border-gray flex items-center justify-center text-gray-400 hover:text-neon-blue hover:border-neon-blue/30 transition-all">
                <Twitter className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-mid-gray border border-border-gray flex items-center justify-center text-gray-400 hover:text-foreground hover:border-gray-400 transition-all">
                <Github className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-mid-gray border border-border-gray flex items-center justify-center text-gray-400 hover:text-red-500 hover:border-red-500/30 transition-all">
                <Youtube className="w-4 h-4" />
              </a>
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
          <p className="text-gray-600 text-xs">© 2026 LoopPC. Built for the Indian PC building community.</p>
          <div className="flex items-center gap-6 text-xs text-gray-600">
            <a href="#" className="hover:text-foreground transition-colors">Privacy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms</a>
            <a href="#" className="hover:text-foreground transition-colors">Contact</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
