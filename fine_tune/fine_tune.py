import pandas as pd
import json
import time
import os
import re
import requests

# ============= CẤU HÌNH =============
INPUT_FILE = 'fine_tune1.csv'
OUTPUT_FILE = 'training_data_ollama.jsonl'
NUM_VARIANTS = 10
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b" # Hoặc qwen2.5:7b để tiếng Việt chuẩn hơn

# SYSTEM_PROMPT mới cho quy mô toàn Việt Nam
SYSTEM_PROMPT = """Bạn là trợ lý du lịch thông minh, am hiểu sâu sắc về du lịch Việt Nam. 
Hãy trả lời một cách thân thiện, chính xác và nhiệt tình. Sử dụng emoji phù hợp 🇻🇳🏖️🍲."""

def test_ollama():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print(f" Ollama đang chạy.")
            return True
        return False
    except:
        print(" ERROR: Ollama chưa bật!")
        return False

def generate_variants_with_ollama(question):
    """
    Prompt được tối ưu để tạo biến thể câu hỏi du lịch Việt Nam tự nhiên và đa dạng
    """
    prompt = f"""Bạn là chuyên gia ngôn ngữ du lịch Việt Nam. Hãy viết lại câu hỏi sau thành {NUM_VARIANTS} cách khác nhau.

Câu gốc: "{question}"

YÊU CẦU NGHIÊM NGẶT:
1. Giữ nguyên nội dung và địa danh được nhắc đến trong câu gốc.
2. Đa dạng phong cách: Gen Z (slay, nhức nách), hỏi ngắn gọn, trang trọng lịch sự, hỏi tư vấn chi tiết.
3. Thay đổi cách diễn đạt nhưng vẫn giữ ý nghĩa: thay từ đồng nghĩa, đảo thứ tự, thêm cảm xúc.
4. TỶ LỆ:
   - 5 câu phải có tên Tỉnh/Thành phố rõ ràng (Hà Nội, Đà Nẵng, Hồ Chí Minh, Quảng Ninh, Tây Ninh, Đà Lạt).
   - 5 câu chỉ dùng tên địa danh cụ thể (Lăng Bác, Cầu Vàng, Mỹ Khê, phố Nguyễn Huệ, Bà Nà...) mà không cần nhắc tên tỉnh.
5. Sử dụng từ địa phương tự nhiên: ghé, chill, check-in, xịn, chuẩn, đỉnh, nhức nách...
6. Chỉ trả về danh sách câu hỏi, mỗi câu 1 dòng, KHÔNG đánh số, KHÔNG giải thích.

Danh sách câu hỏi:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8, "top_p": 0.9}
            },
            timeout=60
        )
        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
            
            # XỬ LÝ SẠCH OUTPUT NGAY TẠI ĐÂY (tương tự clean.py)
            cleaned = []
            for line in lines:
                # Bỏ qua lời giới thiệu của AI
                if "Dưới đây là" in line or "cách viết lại" in line or "danh sách" in line.lower():
                    continue
                
                # Xóa nhãn phong cách: "Câu Gen Z:", "Phong cách..."
                line = re.sub(r'^(Câu|Phong cách|Kiểu)\s+[\w\s]+:\s*', '', line, flags=re.IGNORECASE)
                
                # Xóa số thứ tự, dấu gạch đầu dòng, dấu sao
                line = re.sub(r'^[\-\*\d\.\)\s]+', '', line).strip()
                
                # Chỉ lưu câu có độ dài hợp lý
                if len(line) > 10:  # Tăng từ 5 lên 10 để lọc chặt hơn
                    cleaned.append(line)
            
            return cleaned[:NUM_VARIANTS]
        return None
    except Exception as e:
        print(f"  Lỗi API: {str(e)[:50]}")
        return None

def main():
    print("\n" + "="*70)
    print("GEN DATA DU LỊCH VIỆT NAM (6 TỈNH: HÀ NỘI, ĐÀ NẴNG, HCM, QUẢNG NINH, TÂY NINH, ĐÀ LẠT)")
    print("   Nguồn: fine_tune1.csv -> training_data_ollama.jsonl")
    print("="*70 + "\n")
    
    if not test_ollama(): return

    processed_answers = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    processed_answers.add(data['messages'][2]['content'])
                except: continue
        print(f"Đã hoàn thành {len(processed_answers)} mẫu. Đang chạy tiếp...\n")

    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig').dropna(subset=['Question', 'Answer'])
    total = len(df)
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            q_raw = str(row['Question']).strip()
            ans = str(row['Answer']).strip()
            
            if ans in processed_answers: continue

            print(f"[{idx+1}/{total}] Đang xử lý câu hỏi về: {q_raw[:50]}...")
            
            variants = generate_variants_with_ollama(q_raw)
            
            if variants and len(variants) >= 5:
                for v in variants:
                    entry = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": v},
                            {"role": "assistant", "content": ans}
                        ]
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                f.flush()
                print(f"   OK: Đã thêm {len(variants)} biến thể.")
            else:
                # Fallback nếu AI lỗi: Dùng câu gốc và thêm biến thể đơn giản
                for template in [q_raw, f"Bạn tư vấn giúp mình: {q_raw}", f"Cho mình hỏi về: {q_raw}"]:
                    entry = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": template},
                            {"role": "assistant", "content": ans}
                        ]
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                print(f"   AI lỗi: Đã dùng câu gốc + biến thể đơn giản làm dự phòng.")
            
            time.sleep(0.3) # Local nên chạy rất nhanh

    print("\n" + "="*70)
    print(f"HOÀN THÀNH! File: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()
