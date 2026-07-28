import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.agents.graph import graph
from langchain_core.messages import HumanMessage
from autoevals import Factuality, AnswerRelevancy
from app.core.config import settings

if settings.gemini_keys_list:
    os.environ["GEMINI_API_KEY"] = settings.gemini_keys_list[0]

async def run_single():
    print("=== ĐANG TEST THỬ 1 KỊCH BẢN ĐỂ TRÁNH RATE LIMIT ===\n")
    
    input_text = "Mình đang làm tiệc cho khoảng 150 người, dự định mua 2 chai Vodka, 1 chai Gin và 3 chai Rum. Bạn tính giúp mình chi phí tổng cộng và nồng độ cồn trung bình nhé."
    expected = "Tính toán chi phí B2B cho 2 Vodka, 1 Gin, 3 Rum bằng tool tính toán và trả về kết quả."
    
    print(f"Khách hàng hỏi: {input_text}\n")
    print("Đang gọi Llama 3.3 70B làm bài thi (Chờ 5-10s)...\n")
    
    try:
        state = {"messages": [HumanMessage(content=input_text)]}
        result = await graph.ainvoke(state)
        output = result["messages"][-1].content
        
        print("=== CÂU TRẢ LỜI CỦA LLAMA 3.3 ===")
        print(output)
        print("\n=================================")
        
        print("\nĐang gọi Gemini 3.1 Flash Lite chấm điểm (Chờ 5-10s)...")
        
        # Chấm điểm
        fac = Factuality(model="gemini/gemini-3.1-flash-lite")
        fac_score = fac(input=input_text, output=output, expected=expected, context="")
        print(f"✅ Điểm Bám sát yêu cầu (Factuality): {fac_score.score * 100}%")
        
        rel = AnswerRelevancy(model="gemini/gemini-3.1-flash-lite")
        rel_score = rel(input=input_text, output=output)
        print(f"✅ Điểm Trả lời đúng trọng tâm (Relevancy): {rel_score.score * 100}%")
        
        print("\nTest hoàn tất thành công 100%!")
        
    except Exception as e:
        print(f"\nLỗi rồi: {e}")

if __name__ == "__main__":
    asyncio.run(run_single())
