import React from 'react';
import { Block } from './types';
import { Carousel } from './Carousel';
import { RationaleBlock } from './RationaleBlock';
import { QuickReplies } from './QuickReplies';

import { VenueData, CocktailData } from './types';

// TextBlock wrapper to follow typography standards
export interface TextBlockProps {
  content?: string;
}

export const TextBlock: React.FC<TextBlockProps> = ({ content = '' }) => {
  return (
    <p className="text-body text-text-secondary whitespace-pre-line leading-relaxed text-left max-w-none">
      {content}
    </p>
  );
};

export interface BlockRendererProps {
  block: Block;
  onAction?: (actionType: string, payload: unknown) => void;
}

export interface RegistryComponentProps {
  content?: string;
  data?: (VenueData | CocktailData)[];
  actions?: string[];
  onAction?: (actionType: string, payload: unknown) => void;
}

/**
 * Registry mapping block typenames to React Components.
 * This registry acts as the routing table for Server-Driven UI (SDUI).
 */
export const BlockRegistry: Record<Block['type'], React.ComponentType<RegistryComponentProps>> = {
  text: TextBlock,
  carousel_venues: ({ data, onAction }) => (
    <Carousel data={data || []} type="venue" onAction={onAction} />
  ),
  carousel_cocktails: ({ data, onAction }) => (
    <Carousel data={data || []} type="cocktail" onAction={onAction} />
  ),
  rationale: ({ content }) => <RationaleBlock content={content} />,
  quick_replies: ({ actions, onAction }) => (
    <QuickReplies actions={actions || []} onSelect={(action) => onAction?.('quick_reply', action)} />
  ),
};

/**
 * BlockRenderer dynamically routes payloads to registry components
 */
export const BlockRenderer: React.FC<BlockRendererProps> = ({ block, onAction }) => {
  const Component = BlockRegistry[block.type];
  
  if (!Component) {
    // Graceful fallback for unexpected/new block types (data-driven, no hardcoded strings)
    return null;
  }

  // Pass down block properties and action handlers
  return <Component {...block} onAction={onAction} />;
};
