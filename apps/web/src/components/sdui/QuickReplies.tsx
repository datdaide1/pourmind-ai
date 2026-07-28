import React from 'react';

export interface QuickRepliesProps {
  actions: string[];
  onSelect?: (action: string) => void;
}

export const QuickReplies: React.FC<QuickRepliesProps> = ({ actions, onSelect }) => {
  return (
    <div className="flex flex-wrap gap-2 py-2 w-full">
      {actions.map((action, idx) => (
        <button
          key={idx}
          onClick={() => onSelect?.(action)}
          className="inline-flex h-9 items-center justify-center px-4 rounded-full bg-bg-surface border border-border-default hover:border-[var(--mode-accent)] hover:bg-bg-hover hover:text-text-primary text-body-sm font-medium text-text-secondary active:scale-95 transition-all duration-200 cursor-pointer"
        >
          {action}
        </button>
      ))}
    </div>
  );
};
