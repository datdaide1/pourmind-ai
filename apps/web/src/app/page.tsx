"use client";

import React, { useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Martini, Loader2, LogIn, UserCircle2 } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartSession = async (mode: 'guest' | 'user') => {
    setIsInitializing(true);
    setError(null);

    try {
      // Create a random session ID or user ID
      const sessionId = crypto.randomUUID();
      const payload = mode === 'guest' 
        ? { mode: 'guest', guest_session_id: sessionId }
        : { mode: 'user', user_id: sessionId, guest_session_id: sessionId };

      const response = await fetch('/api/v1/session/init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Failed to initialize session');
      }

      const data = await response.json();
      
      // Navigate to chat room with the returned session_id
      if (data.session_id) {
        router.push(`/chat/${data.session_id}`);
      } else {
        throw new Error('No session ID returned');
      }
    } catch (err) {
      console.error(err);
      setError('Unable to connect to the server. Please ensure the backend is running.');
      setIsInitializing(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-deepest text-text-primary flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background glow effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary-900/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-secondary-900/20 rounded-full blur-[120px] pointer-events-none" />

      <main className="z-10 flex flex-col items-center max-w-xl w-full gap-8 text-center">
        {/* Logo or Icon */}
        <div className="w-24 h-24 bg-bg-elevated border border-[var(--mode-accent,rgba(255,255,255,0.1))] rounded-3xl flex items-center justify-center shadow-2xl mb-4">
          <Martini size={48} className="text-primary-400" />
        </div>

        {/* Hero Text */}
        <div className="space-y-4">
          <h1 className="text-display font-bold tracking-tight bg-gradient-to-br from-primary-300 to-secondary-500 bg-clip-text text-transparent pb-2">
            The Mixologist
          </h1>
          <p className="text-body-lg text-text-secondary max-w-md mx-auto leading-relaxed">
            Hệ thống gợi ý cocktail thông minh kết hợp không gian giải trí. Khám phá thức uống thiết kế riêng cho tâm trạng của bạn.
          </p>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-sm w-full">
            {error}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 w-full mt-4">
          <button
            onClick={() => handleStartSession('guest')}
            disabled={isInitializing}
            className="flex-1 flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-bg-deepest py-4 px-6 rounded-xl font-semibold transition-all shadow-lg shadow-primary-900/20 disabled:opacity-50"
          >
            {isInitializing ? <Loader2 className="animate-spin" size={20} /> : <UserCircle2 size={20} />}
            Bắt đầu ẩn danh (Guest)
          </button>
          
          <button
            onClick={() => handleStartSession('user')}
            disabled={isInitializing}
            className="flex-1 flex items-center justify-center gap-2 bg-bg-elevated hover:bg-bg-surface border border-border-default hover:border-primary-500/50 text-text-primary py-4 px-6 rounded-xl font-semibold transition-all disabled:opacity-50"
          >
            <LogIn size={20} />
            Giả lập Đăng nhập (User)
          </button>
        </div>
        
        {/* Powered By */}
        <div className="mt-12 flex items-center gap-2 opacity-50">
          <span className="text-micro tracking-widest uppercase">Powered by</span>
          <Image src="/next.svg" alt="Next.js" width={60} height={12} className="opacity-80 invert" />
        </div>
      </main>
    </div>
  );
}
