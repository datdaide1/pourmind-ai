import React, { useState, useRef, useEffect } from 'react';
import { SendHorizontal, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled = false, placeholder = "Nhắn tin cho The Mixologist..." }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full bg-bg-elevated border border-border-default rounded-2xl p-2 flex items-end gap-2 shadow-lg focus-within:border-primary-500 focus-within:ring-1 focus-within:ring-primary-500 transition-all">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="w-full bg-transparent text-text-primary placeholder-text-tertiary outline-none resize-none px-3 py-2 text-body-md max-h-[120px] overflow-y-auto disabled:opacity-50"
      />
      
      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className="p-2 rounded-xl bg-primary-600 text-bg-deepest hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0 flex items-center justify-center w-10 h-10 mb-1"
        aria-label="Send message"
      >
        {disabled ? (
          <Loader2 size={20} className="animate-spin" />
        ) : (
          <SendHorizontal size={20} className="mr-0.5" />
        )}
      </button>
    </div>
  );
}
