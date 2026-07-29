"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, RefreshCcw } from 'lucide-react';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { ChatInput } from '@/components/chat/ChatInput';
import { Block } from '@/components/sdui/types';
import { connectSSEChat } from '@/lib/sseClient';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  blocks?: Block[];
  quickReplies?: string[];
}

interface ChatHistoryMessage {
  id?: string;
  role: 'user' | 'assistant';
  content?: string;
  ui_blocks?: Block[];
  quick_replies?: string[];
}

export default function ChatRoom() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat history on mount
  useEffect(() => {
    if (!sessionId) return;
    
    const fetchHistory = async () => {
      try {
        const sessionToken = sessionStorage.getItem(`pourmind:session:${sessionId}`);
        if (!sessionToken) {
          throw new Error('Missing session credentials');
        }
        const response = await fetch(`/api/v1/chat/history?session_id=${sessionId}`, {
          headers: { 'X-Session-Token': sessionToken },
        });
        if (!response.ok) throw new Error('Failed to fetch history');
        const data = await response.json();
        
        if (data.messages && data.messages.length > 0) {
          const loadedMessages: ChatMessage[] = (data.messages as ChatHistoryMessage[]).map((m) => ({
            id: m.id || crypto.randomUUID(),
            role: m.role,
            content: m.content || '',
            blocks: m.ui_blocks || [],
            quickReplies: m.quick_replies || []
          }));
          setMessages(loadedMessages);
        } else {
          // If no history, we could show a welcome message, but usually the init API returns one.
          // For now, we'll let it be empty until the user chats.
        }
      } catch (err) {
        console.error("History fetch error:", err);
      }
    };

    fetchHistory();
    
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [sessionId]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;
    
    setError(null);
    const sessionToken = sessionStorage.getItem(`pourmind:session:${sessionId}`);
    if (!sessionToken) {
      setError('Phiên đăng nhập không hợp lệ. Vui lòng bắt đầu phiên mới.');
      return;
    }
    setIsStreaming(true);

    const userMessageId = crypto.randomUUID();
    const assistantMessageId = crypto.randomUUID();

    // Optimistically add user message and empty assistant message
    setMessages(prev => [
      ...prev, 
      { id: userMessageId, role: 'user', content: text },
      { id: assistantMessageId, role: 'assistant', content: '' }
    ]);

    abortControllerRef.current = new AbortController();

    await connectSSEChat(
      '/api/v1/chat/message',
      { session_id: sessionId, content: text },
      {
        onToken: (token) => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: msg.content + token }
              : msg
          ));
        },
        onBlocks: (blocks, quickReplies) => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, blocks, quickReplies }
              : msg
          ));
        },
        onComplete: () => {
          setIsStreaming(false);
          abortControllerRef.current = null;
        },
        onError: (err) => {
          console.error("SSE Error:", err);
          setError(err.message || 'Có lỗi xảy ra trong quá trình xử lý.');
          setIsStreaming(false);
          abortControllerRef.current = null;
        }
      },
      abortControllerRef.current.signal,
      sessionToken
    );
  };

  const handleAction = (actionType: string, payload: unknown) => {
    // Handling quick replies or button clicks from SDUI blocks
    if (actionType === 'QUICK_REPLY') {
      handleSendMessage(payload as string);
    } else if (actionType === 'view_recipe') {
      handleSendMessage(`Cho tôi xem công thức pha chế chi tiết của món có ID: ${payload}`);
    } else if (actionType === 'details') {
      handleSendMessage(`Cho tôi xem chi tiết đánh giá về địa điểm có ID: ${payload}`);
    } else if (actionType === 'directions') {
      handleSendMessage(`Làm sao để tôi di chuyển tới địa điểm có ID: ${payload}?`);
    } else {
      console.log(`Unhandled action: ${actionType}`, payload);
    }
  };

  const currentQuickReplies = messages.length > 0 ? messages[messages.length - 1].quickReplies : [];

  return (
    <div className="flex flex-col h-full bg-bg-deepest text-text-primary">
      {/* Header */}
      <header className="flex items-center justify-between p-4 bg-bg-elevated border-b border-border-default shadow-sm z-10 sticky top-0">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push('/')}
            className="p-2 hover:bg-bg-surface rounded-full transition-colors text-text-secondary hover:text-text-primary"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-h3 font-semibold">The Mixologist</h1>
            <p className="text-micro text-text-tertiary">Mã phiên: {sessionId.substring(0,8)}...</p>
          </div>
        </div>
        
        {/* Simple reset button */}
        <button 
          onClick={() => {
            const sessionToken = sessionStorage.getItem(`pourmind:session:${sessionId}`);
            if (!sessionToken) return;
            fetch(`/api/v1/chat/${sessionId}`, {
              method: 'DELETE',
              headers: { 'X-Session-Token': sessionToken },
            }).then(() => {
              sessionStorage.removeItem(`pourmind:session:${sessionId}`);
              router.push('/');
            });
          }}
          className="p-2 hover:bg-bg-surface rounded-full transition-colors text-red-400"
          title="Xóa phiên"
        >
          <RefreshCcw size={20} />
        </button>
      </header>

      {/* Message List */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:px-24">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-text-tertiary">
            Chưa có tin nhắn nào. Hãy bắt đầu trò chuyện!
          </div>
        )}
        
        {messages.map((msg) => (
          <MessageBubble 
            key={msg.id}
            role={msg.role}
            content={msg.content}
            blocks={msg.blocks}
            onAction={handleAction}
          />
        ))}

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center mx-auto max-w-lg">
            {error}
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="p-4 bg-bg-deepest border-t border-border-default/50 z-10 sticky bottom-0">
        <div className="max-w-4xl mx-auto flex flex-col gap-3">
          {/* Quick Replies */}
          {currentQuickReplies && currentQuickReplies.length > 0 && !isStreaming && (
            <div className="flex flex-wrap gap-2 px-1">
              {currentQuickReplies.map((qr, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(qr)}
                  className="px-4 py-2 bg-bg-surface border border-primary-500/30 hover:border-primary-500 text-primary-400 rounded-full text-sm font-medium transition-all"
                >
                  {qr}
                </button>
              ))}
            </div>
          )}

          <ChatInput 
            onSend={handleSendMessage} 
            disabled={isStreaming} 
          />
        </div>
      </footer>
    </div>
  );
}
