import pandas as pd
import json
import time
import os
import re
import random

# --- CẤU HÌNH ---
INPUT_FILE = 'fine_tune.csv'   
OUTPUT_FILE = 'training_data.jsonl' 
NUM_VARIANTS = 10 

# System Prompt cố định (Nhân cách của Bot)
SYSTEM_PROMPT = """Bạn là trợ lý du lịch thông minh, am hiểu về du lịch Việt Nam, đặc biệt là các tỉnh thành Miền Trung. 
Hãy trả lời một cách thân thiện, chính xác và nhiệt tình. Sử dụng emoji phù hợp để tạo cảm giác gần gũi với người dùng."""

QUESTION_TEMPLATES = [
    "{q}",  # Câu gốc
    "Xin hỏi, {q}",
    "Cho mình hỏi {q}",
    "Bạn ơi, {q}",
    "Ê ad ơi, {q}",
    "Tư vấn giúp mình: {q}",
    "Mình muốn biết {q}",
    "{q} được không?",
    "{q} nhỉ?",
    "Có ai biết {q} không?",
    "Đang cần thông tin về việc {q}",
    "Giúp mình với, {q}",
    "Hỏi nhanh: {q}",
    "Cho hỏi là {q}",
    "Mọi người cho mình xin thông tin {q}",
]

def generate_question_variants(original_question, num_variants=10):
    """
    Tạo các biến thể của câu hỏi bằng cách:
    1. Thay đổi cấu trúc câu
    2. Thêm/bớt từ lịch sự
    3. Thay đổi ngữ điệu (formal/informal)
    4. Thêm ngữ cảnh
    """
    variants = []
    q_lower = original_question.lower()
    
    # Loại bỏ số thứ tự và dấu chấm ở đầu câu (1. 2. ...)
    q_clean = re.sub(r'^\d+\.\s*', '', original_question).strip()
    q_clean_lower = re.sub(r'^\d+\.\s*', '', q_lower).strip()
    
    # Tạo các biến thể từ templates
    available_templates = QUESTION_TEMPLATES.copy()
    random.shuffle(available_templates)
    
    for i, template in enumerate(available_templates):
        if i >= num_variants:
            break
            
        # Quyết định dùng câu gốc hay lowercase
        if i == 0:
            variant = q_clean  # Giữ nguyên câu đầu tiên
        elif i % 2 == 0:
            variant = template.format(q=q_clean_lower)
        else:
            variant = template.format(q=q_clean)
        
        # Làm sạch kết quả
        variant = re.sub(r'\s+', ' ', variant).strip()
        variant = variant[0].upper() + variant[1:] if variant else variant
        
        # Đảm bảo kết thúc bằng dấu chấm hỏi nếu là câu hỏi
        if not variant.endswith('?') and not variant.endswith('.'):
            variant += '?'
            
        variants.append(variant)
    
    # Đảm bảo có đủ số lượng variants
    while len(variants) < num_variants:
        variants.append(q_clean)
    
    return variants[:num_variants]

def call_llm_to_paraphrase(original_question, num_variants=10):
    """
    Hàm tạo các biến thể của câu hỏi.
    
    HƯỚNG DẪN TÍCH HỢP API:
    Nếu muốn dùng Gemini hoặc OpenAI API, thay thế phần return bên dưới bằng:
    
    ```python
    import google.generativeai as genai
    genai.configure(api_key="YOUR_API_KEY")
    model = genai.GenerativeModel('gemini-pro')
    
    prompt = f'''Hãy viết lại câu hỏi sau thành {num_variants} biến thể khác nhau về cách hỏi,
    giữ nguyên ý nghĩa. Mỗi biến thể trên một dòng, không đánh số:
    
    Câu gốc: {original_question}
    
    Yêu cầu:
    - Đa dạng về phong cách: lịch sự, thân mật, trực tiếp
    - Giữ nguyên nội dung và địa điểm
    - Không thêm thông tin mới
    '''
    
    response = model.generate_content(prompt)
    variants = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
    return variants[:num_variants]
    ```
    """
    return generate_question_variants(original_question, num_variants)

def validate_data(df):
    """Kiểm tra tính hợp lệ của dữ liệu"""
    if df.empty:
        raise ValueError("File CSV rỗng!")
    
    if 'Question' not in df.columns or 'Answer' not in df.columns:
        raise ValueError("File CSV phải có cột 'Question' và 'Answer'")
    
    # Đếm số dòng trống
    empty_questions = df['Question'].isna().sum()
    empty_answers = df['Answer'].isna().sum()
    
    if empty_questions > 0 or empty_answers > 0:
        print(f"  Cảnh báo: Có {empty_questions} câu hỏi trống và {empty_answers} câu trả lời trống")
        df = df.dropna(subset=['Question', 'Answer'])
        print(f"   Đã loại bỏ các dòng trống. Còn lại {len(df)} dòng hợp lệ.")
    
    return df

def main():
    print("="*60)
    print("BẮT ĐẦU QUY TRÌNH FINE-TUNE DATA AUGMENTATION")
    print("="*60)
    
    # Bước 1: Kiểm tra file tồn tại
    if not os.path.exists(INPUT_FILE):
        print(f"   Lỗi: Không tìm thấy file {INPUT_FILE}")
        print(f"   Vui lòng đảm bảo file CSV nằm cùng thư mục với script này.")
        return
    
    # Bước 2: Đọc file CSV
    print(f"\n Bước 1: Đọc file {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE, encoding='utf-8')
        print(f"    Đọc thành công {len(df)} dòng dữ liệu")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
            print(f"    Đọc thành công {len(df)} dòng dữ liệu (UTF-8 with BOM)")
        except Exception as e:
            print(f"    Lỗi đọc file: {e}")
            return
    except Exception as e:
        print(f"    Lỗi đọc file: {e}")
        return
    
    # Bước 3: Validate dữ liệu
    print(f"\n Bước 2: Kiểm tra tính hợp lệ của dữ liệu...")
    try:
        df = validate_data(df)
        print(f"    Dữ liệu hợp lệ!")
    except ValueError as e:
        print(f"    {e}")
        return
    
    # Bước 4: Data Augmentation
    print(f"\n Bước 3: Tiến hành nhân bản dữ liệu (Data Augmentation)...")
    print(f"   Mỗi câu hỏi sẽ tạo ra {NUM_VARIANTS} biến thể")
    print()
    
    jsonl_data = []
    total_rows = len(df)
    
    for index, row in df.iterrows():
        question_goc = str(row['Question']).strip()
        answer_goc = str(row['Answer']).strip()

        # Gọi hàm để sinh ra các biến thể câu hỏi
        try:
            list_cau_hoi_moi = call_llm_to_paraphrase(question_goc, NUM_VARIANTS)
        except Exception as e:
            print(f"       Lỗi khi tạo biến thể: {e}. Sử dụng câu gốc.")
            list_cau_hoi_moi = [question_goc]

        # Tạo từng dòng JSONL cho mỗi biến thể
        for q_variant in list_cau_hoi_moi:
            entry = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q_variant},
                    {"role": "assistant", "content": answer_goc}
                ]
            }
            jsonl_data.append(entry)
    
    # Bước 5: Lưu kết quả
    print(f"\nBước 4: Lưu kết quả vào {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for entry in jsonl_data:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print(f"   Lưu thành công!")
    except Exception as e:
        print(f"   Lỗi khi lưu file: {e}")
        return
    
    # Bước 6: Thống kê kết quả
    print("\n" + "="*60)
    print("HOÀN TẤT QUY TRÌNH!")
    print("="*60)
    print(f"Thống kê:")
    print(f"   • Số câu hỏi gốc: {total_rows}")
    print(f"   • Số biến thể/câu: {NUM_VARIANTS}")
    print(f"   • Tổng mẫu training: {len(jsonl_data)}")
    print(f"   • File output: {OUTPUT_FILE}")
    print(f"   • Kích thước: {os.path.getsize(OUTPUT_FILE) / 1024:.2f} KB")
    print("="*60)
  

if __name__ == "__main__":
    main()