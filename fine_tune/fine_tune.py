import pandas as pd
import json
import time
import os
import re
import requests

# Configuration
INPUT_FILE = 'fine_tune.csv'
OUTPUT_FILE = 'training_data_ollama.jsonl'
NUM_VARIANTS = 10
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """Bạn là trợ lý du lịch thông minh, am hiểu về du lịch Việt Nam, đặc biệt là Đà Lạt (Tây Nguyên). 
Hãy trả lời một cách thân thiện, chính xác và nhiệt tình. Sử dụng emoji phù hợp 🌲☕️."""


def test_ollama():
    """
    Kiểm tra Ollama service có đang chạy không.
    Returns: True nếu service đang chạy, False nếu không.
    """
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"Ollama running with {len(models)} model(s)")
            return True
        return False
    except:
        print("ERROR: Ollama not running")
        print("Install: https://ollama.com/download")
        print("Then run: ollama pull llama3.2:3b")
        return False


def generate_variants_with_ollama(question):
    """
    Gọi Ollama API để sinh các câu hỏi biến thể.
    
    Args:
        question (str): Câu hỏi gốc cần tạo variants
        
    Returns:
        list: Danh sách các câu hỏi variants, hoặc None nếu lỗi
    """
    prompt = f"""Viết lại câu hỏi sau thành {NUM_VARIANTS} cách khác nhau nhưng giữ nguyên ý nghĩa.

Câu gốc: "{question}"

YÊU CẦU:
- PHẢI thay đổi cấu trúc câu, dùng từ đồng nghĩa, đảo ngữ.
- Tạo ra: 1 câu Gen Z, 1 câu keyword ngắn, 1 câu trang trọng.
- Chỉ trả về danh sách câu hỏi, mỗi câu 1 dòng, KHÔNG đánh số.

Trả lời:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.9, "top_p": 0.95}
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '')
            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 5]
            cleaned = [re.sub(r'^\d+[\.\)]\s*', '', l).strip() for l in lines]
            return [l for l in cleaned if len(l) > 5][:NUM_VARIANTS]
        
        return None
        
    except Exception as e:
        print(f"  ERROR: {str(e)[:50]}")
        return None


def main():
    """
    Main function: Load CSV, generate variants with Ollama, save to JSONL.
    Supports resume from previous run.
    """
    print("\n" + "="*70)
    print("FINE-TUNE DATA GENERATION - Ollama Local")
    print("="*70 + "\n")
    
    if not test_ollama():
        return
    
    # Resume logic: Load processed answers
    processed_answers = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                processed_answers.add(data['messages'][2]['content'])
        print(f"Found {len(processed_answers)} processed samples, resuming...\n")
    
    # Load input CSV
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    df = df.dropna(subset=['Question', 'Answer'])
    total = len(df)
    
    print(f"Total questions: {total}")
    print(f"Estimated time: ~{(total * 15) / 60:.1f} minutes\n")
    
    success = 0
    failed = 0
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        for idx, row in df.iterrows():
            q_clean = re.sub(r'^\d+\.\s*', '', str(row['Question'])).strip()
            ans = str(row['Answer']).strip()
            
            if ans in processed_answers:
                continue
            
            print(f"[{idx+1}/{total}] Processing: {q_clean[:60]}...")
            
            variants = generate_variants_with_ollama(q_clean)
            
            if variants and len(variants) >= 5:
                success += 1
                print(f"  Generated {len(variants)} variants")
                
                for v in variants:
                    entry = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": v},
                            {"role": "assistant", "content": ans}
                        ]
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            else:
                failed += 1
                print(f"  Failed - using template fallback")
                for template in [q_clean, f"Cho mình hỏi {q_clean}", f"Bạn ơi, {q_clean}"]:
                    entry = {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": template},
                            {"role": "assistant", "content": ans}
                        ]
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            time.sleep(0.5)
    
    print("\n" + "="*70)
    print(f"COMPLETED: Success={success}/{total}, Failed={failed}/{total}")
    print(f"Output: {OUTPUT_FILE}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
