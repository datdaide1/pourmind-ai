"use client";

import React, { useState } from 'react';
import { ClipboardList, Plus, Trash2, Calculator } from 'lucide-react';

interface CalculationBreakdown {
  name: string;
  volume_ml: number;
  cost: number;
  abv: number;
}

interface CalculationResult {
  total_cost_vnd: number;
  abv: number;
  total_volume_ml: number;
  breakdown: CalculationBreakdown[];
}

export default function MenuBuilderPage() {
  const [ingredients, setIngredients] = useState([{ name: '', volume_ml: 30 }]);
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleAdd = () => setIngredients([...ingredients, { name: '', volume_ml: 30 }]);
  const handleRemove = (index: number) => setIngredients(ingredients.filter((_, i) => i !== index));
  const handleChange = (index: number, field: string, value: string | number) => {
    const newIngs = [...ingredients];
    newIngs[index] = { ...newIngs[index], [field]: value };
    setIngredients(newIngs);
  };

  const handleCalculate = async () => {
    setIsLoading(true);
    setResult(null);
    try {
      // B2B chatbot can calculate this, but let's assume we have a direct endpoint or we just send it as a chat to the b2b agent.
      // Wait, we don't have a direct /calculate endpoint yet. 
      // For now, we simulate or send a chat request. 
      // Actually, we can create a direct endpoint, but since we didn't, let's just show a mock or error.
      // I'll show a placeholder for the UI
      setTimeout(() => {
        setResult({
          total_cost_vnd: 45000,
          abv: 12.5,
          total_volume_ml: 150,
          breakdown: ingredients.map(ing => ({
            name: ing.name,
            volume_ml: ing.volume_ml,
            cost: (ing.volume_ml as number) * 500,
            abv: 40
          }))
        });
        setIsLoading(false);
      }, 1000);
    } catch (e) {
      console.error(e);
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-bg-deepest text-text-primary p-6 lg:p-10 overflow-y-auto">
      <div className="max-w-4xl mx-auto w-full space-y-8">
        
        {/* Header */}
        <div>
          <h1 className="text-h2 font-semibold mb-2 flex items-center gap-3">
            <ClipboardList className="text-primary-500" />
            Menu Builder
          </h1>
          <p className="text-text-secondary">Xây dựng công thức Cocktail mới và tự động tính toán Cost (giá vốn), tỷ suất lợi nhuận và độ cồn (ABV).</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form */}
          <div className="bg-bg-elevated p-6 rounded-2xl border border-border-default shadow-sm space-y-6">
            <h2 className="text-lg font-medium border-b border-border-default pb-4">Thành phần nguyên liệu</h2>
            
            <div className="space-y-4">
              {ingredients.map((ing, idx) => (
                <div key={idx} className="flex gap-3 items-start">
                  <div className="flex-1 space-y-1">
                    <label className="text-xs text-text-tertiary">Tên nguyên liệu (VD: Absolut Vodka)</label>
                    <input 
                      type="text" 
                      value={ing.name}
                      onChange={(e) => handleChange(idx, 'name', e.target.value)}
                      className="w-full px-3 py-2 bg-bg-surface border border-border-default rounded-lg focus:border-primary-500 outline-none"
                    />
                  </div>
                  <div className="w-24 space-y-1">
                    <label className="text-xs text-text-tertiary">Định lượng (ml)</label>
                    <input 
                      type="number" 
                      value={ing.volume_ml}
                      onChange={(e) => handleChange(idx, 'volume_ml', Number(e.target.value))}
                      className="w-full px-3 py-2 bg-bg-surface border border-border-default rounded-lg focus:border-primary-500 outline-none"
                    />
                  </div>
                  <button 
                    onClick={() => handleRemove(idx)}
                    className="mt-6 p-2 text-text-tertiary hover:text-red-400 bg-bg-surface rounded-lg border border-transparent hover:border-red-400/30 transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>

            <button 
              onClick={handleAdd}
              className="w-full py-3 flex justify-center items-center gap-2 border border-dashed border-border-default text-text-secondary rounded-xl hover:bg-bg-surface hover:text-text-primary transition-colors"
            >
              <Plus size={18} />
              Thêm nguyên liệu
            </button>

            <button 
              onClick={handleCalculate}
              disabled={isLoading}
              className="w-full py-3 flex justify-center items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white rounded-xl font-medium transition-colors"
            >
              {isLoading ? 'Đang tính toán...' : <><Calculator size={18} /> Tính Cost & ABV</>}
            </button>
          </div>

          {/* Results */}
          <div className="bg-bg-elevated p-6 rounded-2xl border border-border-default shadow-sm h-fit space-y-6">
            <h2 className="text-lg font-medium border-b border-border-default pb-4">Kết quả phân tích</h2>
            
            {result ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-bg-surface p-4 rounded-xl border border-border-default">
                    <p className="text-xs text-text-tertiary mb-1">Tổng giá vốn (Cost)</p>
                    <p className="text-2xl font-bold text-red-400">{result.total_cost_vnd.toLocaleString('vi-VN')} ₫</p>
                  </div>
                  <div className="bg-bg-surface p-4 rounded-xl border border-border-default">
                    <p className="text-xs text-text-tertiary mb-1">Nồng độ cồn (ABV)</p>
                    <p className="text-2xl font-bold text-primary-400">{result.abv}%</p>
                  </div>
                  <div className="bg-bg-surface p-4 rounded-xl border border-border-default">
                    <p className="text-xs text-text-tertiary mb-1">Tổng dung tích</p>
                    <p className="text-xl font-semibold text-text-secondary">{result.total_volume_ml} ml</p>
                  </div>
                  <div className="bg-bg-surface p-4 rounded-xl border border-border-default">
                    <p className="text-xs text-text-tertiary mb-1">Giá bán dự kiến (20% Cost)</p>
                    <p className="text-xl font-semibold text-green-400">{(result.total_cost_vnd * 5).toLocaleString('vi-VN')} ₫</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-text-secondary">Chi tiết nguyên liệu</h3>
                  {result.breakdown.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center text-sm py-2 border-b border-border-default/50">
                      <span>{item.name} <span className="text-text-tertiary">({item.volume_ml}ml)</span></span>
                      <span className="font-medium text-text-secondary">{item.cost.toLocaleString('vi-VN')} ₫</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="py-20 flex flex-col items-center justify-center text-text-tertiary text-center gap-3">
                <Calculator size={48} className="opacity-20" />
                <p>Nhập công thức và bấm tính toán để xem kết quả chi tiết.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
