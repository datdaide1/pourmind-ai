import React from 'react';

export interface RationaleBlockProps {
  content?: string;
  title?: string; // Defaults to "Lý do chọn"
}

export const SparklesIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="w-4 h-4 text-[var(--mode-accent)]"
    {...props}
  >
    <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    <path d="m5 3 1 2.5L8.5 6 6 7 5 9.5 4 7 1.5 6 4 5.5z" />
    <path d="m19 17 1 2.5 2.5.5-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z" />
  </svg>
);

export const RationaleBlock: React.FC<RationaleBlockProps> = ({
  content = '',
  title = 'Lý do chọn',
}) => {
  return (
    <div className="border-l-2 border-[var(--mode-accent)] bg-[var(--mode-accent-soft)] py-3 px-4 rounded-r-md transition-all duration-300">
      <div className="flex items-center gap-1.5 mb-1 text-body-sm font-semibold text-text-primary">
        <SparklesIcon />
        <span>{title}</span>
      </div>
      <p className="text-body-sm italic text-text-secondary leading-normal whitespace-pre-line text-left">
        {content}
      </p>
    </div>
  );
};
