import React from 'react';
import { Card } from './Card';
import { VenueData, CocktailData } from './types';

export interface CarouselProps {
  data: (VenueData | CocktailData)[];
  type: 'venue' | 'cocktail';
  onAction?: (actionType: string, id: string) => void;
}

export const Carousel: React.FC<CarouselProps> = ({ data, type, onAction }) => {
  return (
    <div className="w-full relative">
      <div className="flex overflow-x-auto gap-4 pb-4 snap-x snap-mandatory scroll-smooth scrollbar-thin scrollbar-thumb-border-default scrollbar-track-transparent">
        {data.map((item) => (
          <div key={item.id} className="w-[280px] shrink-0 snap-start">
            <Card data={item} type={type} onAction={onAction} />
          </div>
        ))}
      </div>
    </div>
  );
};
