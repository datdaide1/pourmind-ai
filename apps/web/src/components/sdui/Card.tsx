import React from 'react';
import Image from 'next/image';
import { VenueData, CocktailData } from './types';
import { RationaleBlock } from './RationaleBlock';

export interface CardProps {
  data: VenueData | CocktailData;
  type?: 'venue' | 'cocktail';
  onAction?: (actionType: string, id: string) => void;
}

export const Card: React.FC<CardProps> = ({ data, type, onAction }) => {
  // Infer card type if not explicitly passed
  const isCocktail = type === 'cocktail' || 'base_liquor' in data || 'alcoholic_type' in data;

  if (isCocktail) {
    const cocktail = data as CocktailData;
    const detailsText = [cocktail.alcoholic_type, cocktail.base_liquor]
      .filter(val => val && val !== 'None' && val !== 'null')
      .join(' · ');

    return (
      <div className="group flex flex-col bg-bg-elevated border border-border-subtle rounded-xl p-5 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] hover:border-border-default hover:-translate-y-0.5 hover:shadow-lg">
        {/* Cocktail Image (1:1 Aspect) */}
        <div className="relative w-full aspect-square rounded-lg overflow-hidden mb-4 bg-bg-surface">
          {cocktail.image_url && cocktail.image_url !== 'None' && cocktail.image_url !== 'null' ? (
            <Image
              src={cocktail.image_url}
              alt={cocktail.name}
              fill
              sizes="(max-width: 768px) 100vw, 280px"
              className="object-cover transition-transform duration-500 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full bg-gradient-to-br from-bg-surface to-bg-hover flex items-center justify-center">
              <span className="text-4xl">🍸</span>
            </div>
          )}
        </div>

        {/* Title + Category */}
        <div className="flex flex-col mb-3">
          <h4 className="text-h4 font-semibold text-text-primary flex items-center gap-1.5 text-left mb-1 line-clamp-1">
            <span>🍸</span>
            {cocktail.name}
          </h4>
          {detailsText && (
            <span className="text-caption text-text-tertiary text-left line-clamp-1 font-medium">
              {detailsText}
            </span>
          )}
        </div>

        {/* Rationale Block (Conditional) */}
        {cocktail.rationale && (
          <div className="mb-4">
            <RationaleBlock content={cocktail.rationale} />
          </div>
        )}

        {/* Stats Pill Bar (Optional fields mapping) */}
        {((cocktail.alcoholic_type && cocktail.alcoholic_type !== 'None') || 
          (cocktail.base_liquor && cocktail.base_liquor !== 'None')) && (
          <div className="grid grid-cols-2 gap-2 border border-border-subtle bg-bg-surface/50 rounded-lg p-2.5 mb-4 text-center">
            <div className="flex flex-col items-center justify-center">
              <span className="text-micro text-text-tertiary uppercase tracking-wider mb-0.5">Phân Loại</span>
              <span className="text-data-sm text-[var(--mode-accent)] font-medium line-clamp-1">
                {cocktail.alcoholic_type && cocktail.alcoholic_type !== 'None' ? cocktail.alcoholic_type : 'N/A'}
              </span>
            </div>
            <div className="flex flex-col items-center justify-center border-l border-border-subtle">
              <span className="text-micro text-text-tertiary uppercase tracking-wider mb-0.5">Rượu Nền</span>
              <span className="text-body-sm text-text-secondary font-medium line-clamp-1">
                {cocktail.base_liquor && cocktail.base_liquor !== 'None' ? cocktail.base_liquor : 'N/A'}
              </span>
            </div>
          </div>
        )}

        {/* Action Button */}
        <button
          onClick={() => onAction?.('view_recipe', cocktail.id || cocktail.name)}
          className="mt-auto w-full py-2 bg-[var(--mode-accent)] text-text-inverse text-body-sm font-semibold rounded-lg hover:scale-[1.02] active:scale-[0.98] transition-transform text-center cursor-pointer"
        >
          Xem Công Thức
        </button>
      </div>
    );
  }

  // Otherwise, render Venue Card
  const venue = data as VenueData;

  return (
    <div className="group flex flex-col bg-bg-elevated border border-border-subtle rounded-xl p-5 transition-all duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] hover:border-border-default hover:-translate-y-0.5 hover:shadow-lg">
      {/* Venue Image (16:9 Aspect) */}
      <div className="relative w-full aspect-[16/9] rounded-lg overflow-hidden mb-4 bg-bg-surface">
        {venue.image_url && venue.image_url !== 'None' && venue.image_url !== 'null' ? (
          <Image
            src={venue.image_url}
            alt={venue.name}
            fill
            sizes="(max-width: 768px) 100vw, 280px"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-bg-surface to-bg-hover flex items-center justify-center">
            <span className="text-4xl">🏢</span>
          </div>
        )}

        {/* Floating Badge representing the Venue's vibe */}
        {venue.vibe && (
          <div className="absolute top-3 left-3 bg-bg-surface/80 backdrop-blur-md border border-border-strong px-2 py-0.5 rounded text-overline text-text-primary tracking-widest font-semibold">
            {venue.vibe}
          </div>
        )}
      </div>

      {/* Title + Subtitle */}
      <div className="flex flex-col mb-3">
        <h4 className="text-h4 font-semibold text-text-primary text-left line-clamp-1 mb-1">
          {venue.name}
        </h4>
        {venue.vibe && (
          <span className="text-caption text-text-tertiary text-left line-clamp-1 font-medium">
            Vibe · {venue.vibe}
          </span>
        )}
      </div>

      {/* Rationale Block (Conditional) */}
      {venue.rationale && (
        <div className="mb-4">
          <RationaleBlock content={venue.rationale} />
        </div>
      )}

      {/* Tag Chips */}
      {venue.vibe_tags && venue.vibe_tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {venue.vibe_tags.map((tag, idx) => (
            <span
              key={idx}
              className="px-2 py-1 bg-bg-surface border border-border-subtle rounded text-caption text-text-secondary whitespace-nowrap"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Action Row */}
      <div className="mt-auto flex items-center justify-between gap-3 pt-2">
        <button
          onClick={() => onAction?.('directions', venue.id || venue.name)}
          className="flex-1 py-2 text-center text-body-sm font-medium border border-border-strong hover:bg-bg-hover text-text-primary rounded-lg transition-colors cursor-pointer"
        >
          Chỉ Đường
        </button>
        <button
          onClick={() => onAction?.('details', venue.id || venue.name)}
          className="flex-1 py-2 text-center text-body-sm font-semibold text-[var(--mode-accent)] hover:text-text-primary transition-colors cursor-pointer"
        >
          Xem Thêm →
        </button>
      </div>
    </div>
  );
};
