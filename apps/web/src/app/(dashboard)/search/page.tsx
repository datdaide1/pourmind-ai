"use client";

import React, { useState } from 'react';
import { Search, Martini, MapPin, AlertCircle } from 'lucide-react';

interface SearchResult {
  name?: string;
  base_liquor?: string;
  alcoholic_type?: string;
  ingredients?: string;
  address?: string;
  district?: string;
  city?: string;
  rating?: number;
  price_range?: string;
}

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [type, setType] = useState<'cocktail' | 'venue'>('cocktail');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setError('');
    
    try {
      const res = await fetch(`/api/v1/search?query=${encodeURIComponent(query)}&type=${type}&limit=12`);
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setResults(data.results || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Đã có lỗi xảy ra');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-bg-deepest text-text-primary p-6 lg:p-10 overflow-y-auto">
      <div className="max-w-5xl mx-auto w-full space-y-8">
        
        {/* Header */}
        <div>
          <h1 className="text-h2 font-semibold mb-2">Khám Phá</h1>
          <p className="text-text-secondary">Tìm kiếm công thức Cocktail hoặc Quán Bar yêu thích của bạn.</p>
        </div>

        {/* Search Bar */}
        <div className="bg-bg-elevated p-6 rounded-2xl border border-border-default shadow-sm space-y-6">
          <form onSubmit={handleSearch} className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary" size={20} />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={type === 'cocktail' ? "Ví dụ: Margarita, Gin, chua ngọt..." : "Ví dụ: Quận 1, Speakeasy, không gian mở..."}
                className="w-full pl-12 pr-4 py-3 bg-bg-surface border border-border-default rounded-xl focus:outline-none focus:border-primary-500 transition-colors"
              />
            </div>
            <button 
              type="submit"
              disabled={isLoading || !query.trim()}
              className="px-8 py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-colors"
            >
              {isLoading ? 'Đang tìm...' : 'Tìm kiếm'}
            </button>
          </form>

          {/* Type Toggle */}
          <div className="flex items-center gap-4 border-t border-border-default pt-6">
            <button
              onClick={() => { setType('cocktail'); setResults([]); }}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-medium transition-all ${
                type === 'cocktail' 
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' 
                  : 'bg-bg-surface text-text-secondary border border-border-default hover:text-text-primary'
              }`}
            >
              <Martini size={18} />
              Cocktails
            </button>
            <button
              onClick={() => { setType('venue'); setResults([]); }}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-medium transition-all ${
                type === 'venue' 
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' 
                  : 'bg-bg-surface text-text-secondary border border-border-default hover:text-text-primary'
              }`}
            >
              <MapPin size={18} />
              Quán Bar
            </button>
          </div>
        </div>

        {/* Results */}
        {error && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3">
            <AlertCircle size={20} />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((item, idx) => (
            <div key={idx} className="bg-bg-elevated rounded-2xl border border-border-default overflow-hidden hover:border-primary-500/50 transition-colors flex flex-col">
              <div className="h-48 bg-bg-surface relative flex items-center justify-center">
                {/* Fallback Image logic */}
                <div className="text-text-tertiary flex flex-col items-center gap-2">
                  {type === 'cocktail' ? <Martini size={32} /> : <MapPin size={32} />}
                  <span className="text-sm font-medium">{item.name || 'Unknown'}</span>
                </div>
              </div>
              <div className="p-5 flex-1 flex flex-col">
                <h3 className="text-lg font-semibold mb-2">{item.name}</h3>
                {type === 'cocktail' ? (
                  <>
                    <p className="text-sm text-text-secondary mb-1"><span className="text-text-tertiary">Base:</span> {item.base_liquor}</p>
                    <p className="text-sm text-text-secondary mb-3"><span className="text-text-tertiary">Type:</span> {item.alcoholic_type}</p>
                    <div className="mt-auto pt-4 border-t border-border-default">
                      <p className="text-xs text-text-secondary line-clamp-2">{item.ingredients}</p>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-text-secondary mb-1"><span className="text-text-tertiary">Địa chỉ:</span> {item.address}, {item.district}</p>
                    <p className="text-sm text-text-secondary mb-3"><span className="text-text-tertiary">City:</span> {item.city}</p>
                    <div className="mt-auto pt-4 border-t border-border-default flex justify-between items-center">
                      <span className="text-xs font-medium text-yellow-500 flex items-center gap-1">★ {item.rating}</span>
                      <span className="text-xs text-primary-400">{item.price_range}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
        
        {results.length === 0 && !isLoading && !error && query && (
          <div className="text-center py-20 text-text-tertiary">
            Không tìm thấy kết quả phù hợp.
          </div>
        )}

      </div>
    </div>
  );
}
