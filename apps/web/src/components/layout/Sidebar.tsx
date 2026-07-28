"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  MessageSquare, 
  Search, 
  ClipboardList, 
  Settings, 
  LogOut,
  Menu,
  X,
  Martini
} from 'lucide-react';

export function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { name: 'Chat Assistant', href: '/chat', match: '/chat', icon: MessageSquare },
    { name: 'Khám phá', href: '/search', match: '/search', icon: Search },
    { name: 'Menu Builder', href: '/menu-builder', match: '/menu-builder', icon: ClipboardList },
  ];

  return (
    <>
      {/* Mobile Menu Toggle */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 bg-bg-surface border border-border-default rounded-md text-text-secondary"
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Sidebar */}
      <div className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-64 bg-bg-elevated border-r border-border-default
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        flex flex-col
      `}>
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-border-default gap-3">
          <div className="w-8 h-8 rounded bg-primary-500/20 flex items-center justify-center text-primary-400">
            <Martini size={20} />
          </div>
          <span className="font-semibold text-lg tracking-tight">Mixologist</span>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.match);
            return (
              <Link 
                key={item.name} 
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${isActive 
                    ? 'bg-primary-500/10 text-primary-400 border border-primary-500/20' 
                    : 'text-text-secondary hover:text-text-primary hover:bg-bg-surface border border-transparent'}
                `}
              >
                <item.icon size={18} className={isActive ? 'text-primary-400' : 'text-text-tertiary'} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-border-default space-y-2">
          <button className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-surface transition-colors">
            <Settings size={18} className="text-text-tertiary" />
            Cài đặt
          </button>
          <Link href="/" className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-bg-surface transition-colors">
            <LogOut size={18} className="text-text-tertiary" />
            Về trang chủ
          </Link>
        </div>
      </div>

      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
