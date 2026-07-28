import React from 'react';
import { User, Bot } from 'lucide-react';
import { BlockRenderer } from '../sdui/BlockRegistry';
import { Block } from '../sdui/types';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  blocks?: Block[];
  onAction?: (actionType: string, payload: unknown) => void;
}

export function MessageBubble({ role, content, blocks, onAction }: MessageBubbleProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex w-full gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-6`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${isUser ? 'bg-primary-500 text-bg-deepest' : 'bg-secondary-500 text-bg-deepest'}`}>
        {isUser ? <User size={20} /> : <Bot size={20} />}
      </div>

      {/* Message Content */}
      <div className={`flex flex-col max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Text bubble */}
        {content && (
          <div className={`px-4 py-3 rounded-2xl ${
            isUser 
              ? 'bg-primary-600 text-text-primary rounded-tr-sm' 
              : 'bg-bg-elevated border border-border-subtle text-text-primary rounded-tl-sm'
          }`}>
            <p className="text-body-md whitespace-pre-wrap leading-relaxed">{content}</p>
          </div>
        )}

        {/* SDUI Blocks (Assistant only) */}
        {blocks && blocks.length > 0 && (
          <div className="mt-4 flex flex-col gap-4 w-full">
            {blocks.map((block, idx) => (
              <BlockRenderer 
                key={`${block.type}-${idx}`} 
                block={block} 
                onAction={onAction}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
