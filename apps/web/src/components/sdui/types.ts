export type Block =
  | TextBlock
  | CarouselVenuesBlock
  | CarouselCocktailsBlock
  | RationaleBlock
  | QuickRepliesBlock;

export interface TextBlock {
  type: 'text';
  content: string;
}

export interface VenueData {
  id: string;
  name: string;
  vibe: string;
  image_url?: string;
  vibe_tags?: string[];
  rationale?: string;
}

export interface CarouselVenuesBlock {
  type: 'carousel_venues';
  data: VenueData[];
}

export interface CocktailData {
  id: string;
  name: string;
  vibe?: string;
  image_url?: string;
  vibe_tags?: string[];
  rationale?: string;
  alcoholic_type?: string;
  base_liquor?: string;
}

export interface CarouselCocktailsBlock {
  type: 'carousel_cocktails';
  data: CocktailData[];
}

export interface RationaleBlock {
  type: 'rationale';
  content: string;
}

export interface QuickRepliesBlock {
  type: 'quick_replies';
  actions: string[];
}
