"use client";

import React from 'react';
import { useRouter } from 'next/navigation';
import { MessageSquarePlus, Clock, Trash2, LayoutGrid } from 'lucide-react';

export default function ChatHistoryPage() {
  const router = useRouter();
  // We simulate checking auth status (isGuest). 
  // For now, if no auth token/user context, we consider them guest.
  const isGuest = true;
  const sessions: Array<{ id: string }> = [];

  const startNewChat = () => {
    // Generate a fresh session ID for Guest
    const newSessionId = crypto.randomUUID();
    router.push(`/chat/${newSessionId}`);
  };

  return (
    <div className="flex flex-col h-full bg-bg-deepest text-text-primary overflow-y-auto">
      <div className="max-w-5xl mx-auto w-full p-6 lg:p-10 space-y-10">
        
        {/* Header */}
        <div className="flex justify-between items-center border-b border-border-default pb-6">
          <div>
            <h1 className="text-h2 font-semibold mb-2 flex items-center gap-3">
              <LayoutGrid className="text-primary-500" />
              Chat Workspace
            </h1>
            <p className="text-text-secondary">Trò chuyện với Mixologist AI hoặc xem lại các lịch sử hội thoại.</p>
          </div>
          <button 
            onClick={startNewChat}
            className="flex items-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-5 py-3 rounded-xl font-medium shadow-md shadow-primary-500/20 transition-all hover:scale-105"
          >
            <MessageSquarePlus size={20} />
            Bắt Đầu Chat Mới
          </button>
        </div>

        {/* Content */}
        {isGuest ? (
          <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
            <div className="w-20 h-20 bg-bg-elevated rounded-full flex items-center justify-center mb-4">
              <Clock size={32} className="text-text-tertiary" />
            </div>
            <h3 className="text-h4 font-medium">Bạn đang dùng chế độ Khách (Guest)</h3>
            <p className="text-text-secondary max-w-md">
              Các cuộc hội thoại của khách vãng lai mang tính chất tạm thời (Ephemeral) để đảm bảo quyền riêng tư. Không có lịch sử nào được lưu lại trên máy chủ.
            </p>
            <button 
              onClick={startNewChat}
              className="mt-6 text-primary-400 hover:text-primary-300 font-medium underline underline-offset-4"
            >
              Tạo phiên trò chuyện ẩn danh ngay
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Real sessions would map here */}
            {sessions.map((session, idx) => (
              <div key={idx} className="bg-bg-elevated border border-border-subtle p-5 rounded-2xl hover:border-border-default hover:-translate-y-1 transition-all cursor-pointer group">
                <div className="flex justify-between items-start mb-3">
                  <h4 className="font-medium text-text-primary truncate pr-4">Margarita & Cocktail Chua</h4>
                  <button className="text-text-tertiary hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Trash2 size={16} />
                  </button>
                </div>
                <p className="text-sm text-text-tertiary mb-4">Hôm qua, 14:30</p>
                <div className="flex gap-2">
                  <span className="px-2 py-1 bg-bg-surface text-text-secondary rounded text-xs">Margarita</span>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
