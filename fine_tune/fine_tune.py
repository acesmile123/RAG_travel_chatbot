import pandas as pd
import json
import time
import os
import re
import requests

# ============= CẤU HÌNH =============
INPUT_FILE = 'fine_tune1.csv'
OUTPUT_FILE = 'training_data_safe.jsonl'
NUM_VARIANTS = 5  # Giảm xuống 5 để nhanh và an toàn hơn
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên nghiệp, am hiểu sâu sắc về du lịch Việt Nam, đặc biệt là 6 tỉnh/thành: Hà Nội, Đà Nẵng, Hồ Chí Minh, Quảng Ninh, Tây Ninh và Đà Lạt. 
Hãy trả lời một cách thân thiện, chính xác, chi tiết với địa chỉ cụ thể và nhiệt tình. Sử dụng emoji phù hợp 🇻🇳🏖️🍲☕🏞️."""

def test_ollama():
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print(f"Ollama đang chạy.")
            return True
        return False
    except:
        print("ERROR: Ollama chưa bật!")
        return False

def extract_location(text):
    """Trích xuất tên địa danh từ câu hỏi"""
    locations = ['Hà Nội', 'Đà Nẵng', 'Hồ Chí Minh', 'Sài Gòn', 'Quảng Ninh', 
                 'Hạ Long', 'Tây Ninh', 'Đà Lạt']
    for loc in locations:
        if loc in text:
            return loc
    return None

def generate_variants_safe(question):
    """
    Gen biến thể AN TOÀN - KHÔNG CHO PHÉP thay đổi địa danh
    """
    location = extract_location(question)
    
    prompt = f"""Bạn là chuyên gia viết lại câu hỏi du lịch. Hãy viết lại câu sau thành {NUM_VARIANTS} cách khác nhau.

Câu gốc: "{question}"

 QUY TẮC NGHIÊM NGẶT - PHẢI TUÂN THỦ:
1. TUYỆT ĐỐI KHÔNG ĐƯỢC thay đổi hoặc thêm tên địa điểm/tỉnh thành khác
2. BẮT BUỘC giữ nguyên 100% tên địa danh có trong câu gốc
3.  Chỉ được thay đổi: cách hỏi, từ ngữ, phong cách (Gen Z/trang trọng/ngắn gọn)
4.  Đa dạng phong cách: "Cho mình hỏi...", "Bạn ơi...", "Anh chị tư vấn...", "...ạ", "...nhể", "...vậy?"
5.  Dùng từ địa phương: ghé, check-in, chill, xịn, chuẩn, đỉnh, ngon
6.  KHÔNG thêm địa danh mới như "Ở Đà Nẵng", "Tại Hà Nội" nếu câu gốc không có
7.  Chỉ trả về danh sách câu hỏi, mỗi câu 1 dòng, KHÔNG đánh số, KHÔNG giải thích

VÍ DỤ:
- Câu gốc: "Ở Hà Nội cafe trứng quán nào ngon?"
-  ĐÚNG: "Cafe trứng Hà Nội chỗ nào đỉnh?"
-  ĐÚNG: "Cho mình hỏi quán cafe trứng ngon tại Hà Nội ạ"
-  SAI: "Ở Đà Nẵng cafe trứng quán nào ngon?" (thay đổi địa danh)
-  SAI: "Cafe trứng Quảng Ninh..." (thêm địa danh mới)

Danh sách {NUM_VARIANTS} câu hỏi:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,  # Giảm từ 0.8 → 0.5 để ít sáng tạo hơn
                    "top_p": 0.85,
                    "num_predict": 150  # Giới hạn tokens
                }
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 10]
            
            # Xử lý sạch output
            cleaned = []
            for line in lines:
                # Bỏ qua lời giới thiệu
                if any(x in line.lower() for x in ["dưới đây", "danh sách", "cách viết", "ví dụ"]):
                    continue
                
                # Xóa nhãn phong cách và số thứ tự
                line = re.sub(r'^(Câu|Phong cách|Kiểu)\s+[\w\s]+:\s*', '', line, flags=re.IGNORECASE)
                line = re.sub(r'^[\-\*\d\.\)\s]+', '', line).strip()
                
                # VALIDATE: Kiểm tra địa danh có đúng không
                if location and location not in line:
                    continue  # Bỏ qua câu không có địa danh gốc
                
                # Kiểm tra không có địa danh lạ
                other_locations = [loc for loc in ['Hà Nội', 'Đà Nẵng', 'Hồ Chí Minh', 
                                                    'Quảng Ninh', 'Tây Ninh', 'Đà Lạt'] 
                                   if loc != location]
                if any(other_loc in line for other_loc in other_locations):
                    continue  # Bỏ qua câu có địa danh lạ
                
                if len(line) > 15:
                    cleaned.append(line)
            
            return cleaned[:NUM_VARIANTS]
        return None
    except Exception as e:
        print(f" Lỗi API: {str(e)[:50]}")
        return None

def main():
    print("\n" + "="*70)
    print(" GEN DATA AN TOÀN - VALIDATE CHẶT CHẼ ĐỊA DANH")
    print("   Nguồn: fine_tune1.csv → training_data_safe.jsonl")
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
        print(f" Đã hoàn thành {len(processed_answers)} mẫu. Đang chạy tiếp...\n")

    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig').dropna(subset=['Question', 'Answer'])
    total = len(df)
    success_count = 0
    fail_count = 0
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            q_raw = str(row['Question']).strip()
            ans = str(row['Answer']).strip()
            
            if ans in processed_answers: continue

            print(f" [{idx+1}/{total}] {q_raw[:50]}...")
            
            variants = generate_variants_safe(q_raw)
            
            if variants and len(variants) >= 3:  # Chấp nhận từ 3 câu trở lên
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
                success_count += 1
                print(f"   OK: {len(variants)} biến thể")
            else:
                # Fallback: Dùng câu gốc
                entry = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": q_raw},
                        {"role": "assistant", "content": ans}
                    ]
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                fail_count += 1
                print(f"   Dùng gốc (AI lỗi hoặc validate fail)")
            
            time.sleep(0.1)

    print("\n" + "="*70)
    print(f" HOÀN THÀNH!")
    print(f"   Thành công: {success_count} | Dùng gốc: {fail_count}")
    print(f"   File: {OUTPUT_FILE}")
    print("="*70)

if __name__ == "__main__":
    main()
