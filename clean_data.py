import json
import re
import os

DELETE_SOURCE_AFTER_CLEAN = True  # Chỉ xóa file gốc nếu KHÔNG chứa '_cleaned'

# --- CÁC HÀM XỬ LÝ LOGIC (GIỮ NGUYÊN TỪ CODE CỦA BẠN) ---

def delete_original_file(path):
    """Xóa file gốc nếu không phải file đã clean."""
    filename = os.path.basename(path)
    if "_cleaned" in filename.lower():
        print(f"   • Bỏ qua xóa vì đã clean: {filename}")
        return
    try:
        os.remove(path)
        print(f"   • Đã xóa file gốc: {filename}")
    except OSError as exc:
        print(f"   • Không thể xóa {filename}: {exc}")

def remove_garbage_patterns(text):
    """Loại bỏ các pattern rác cụ thể như chuỗi số dài, widget lịch."""
    # 1. Mã code widget lịch (số dài)
    text = re.sub(r'\d{15,}', '', text)

    # 2. Chuỗi Thứ/Tháng (Date Picker) – cho phép xuất hiện dấu cách xen giữa
    date_pattern = r'(?:(?:C\s*N|T\s*\d|Thứ\s*\d|Chủ\s*Nhật)[\s,.-]*){3,}'
    text = re.sub(date_pattern, '', text, flags=re.IGNORECASE)

    # 3. Chuỗi tháng tiếng Anh/Viet lặp lại (January, February..., Tháng 1...)
    month_pattern = (
        r'(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|'
        r'dec(?:ember)?|tháng\s*(?:1|2|3|4|5|6|7|8|9|10|11|12|một|hai|ba|tư|năm|sáu|bảy|tám|chín|mười|mười\s+một|mười\s+hai))'
        r'[\s,;/\-]*){3,}'
    )
    text = re.sub(month_pattern, '', text, flags=re.IGNORECASE)

    return text

def clean_content(text):
    """Hàm làm sạch sâu: Xóa link, xóa chú thích ảnh, component rác."""
    if not text: return ""
    
    text = remove_garbage_patterns(text)
    
    # Các bước clean regex chuẩn
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text) # Markdown Image
    text = re.sub(r'\[(Hình ảnh|Ảnh|Image|Photo).*?\]', '', text, flags=re.IGNORECASE) # [Caption]
    text = re.sub(r'\((Ảnh|Nguồn|Source|Sưu tầm).*?\)', '', text, flags=re.IGNORECASE) # (Caption)
    text = re.sub(r'https?://\S+|data:image/\S+', '', text) # URL trần
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text) # Markdown Link -> Text
    
    text = text.replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_ad_chunk(item):
    """Lọc quảng cáo thông minh."""
    content = item.get("content", "")
    tokens = item.get("tokens", 0)
    content_lower = content.lower()
    section_lower = item.get("section", "").lower()
    name_lower = item.get("name", "").lower()
    source_lower = item.get("source", "").lower()
    
    junk_ui_keywords = [
        "đăng nhập", "đăng ký", "landscape mode", "chọn ngôn ngữ", 
        "tất cả quyền được bảo lưu", "vui lòng xoay"
    ]
    if any(kw in content_lower for kw in junk_ui_keywords):
        return True

    sales_keywords = ["voucher", "deal hời", "bán chạy"]
    has_sales_kw = any(kw in content_lower for kw in sales_keywords)

    promo_phrases = [
        "đảm bảo giá", "nâng hạng phòng", "ưu đãi", "khuyến mãi", "deal sốc",
        "đặt phòng ngay", "ưu đãi độc quyền", "ưu đãi giới hạn", "giảm giá", "flash sale"
    ]
    policy_keywords = [
        "trẻ em", "em bé", "dưới 4 tuổi", "nhận phòng", "trả phòng", "chính sách",
        "hoàn hủy", "thanh toán", "đặt cọc", "miễn phí hủy"
    ]
    utility_keywords = ["tìm kiếm", "lọc giá", "đảm bảo giá tốt nhất"]

    promo_hit = any(kw in content_lower for kw in promo_phrases)
    policy_hits = sum(1 for kw in policy_keywords if kw in content_lower)
    utility_hit = any(kw in content_lower for kw in utility_keywords)

    short_chunk = tokens < 120

    # Luật 1: chunk ngắn chứa từ bán hàng/promo -> loại
    if short_chunk and (has_sales_kw or promo_hit):
        return True

    # Luật 2: chunk ngắn nhưng chứa >=2 cụm chính sách -> loại (ví dụ chính sách trẻ em, hoàn hủy)
    if short_chunk and policy_hits >= 2:
        return True

    # Luật 3: chunk rất ngắn chỉ là thành phần UI tìm kiếm
    if tokens < 50 and utility_hit:
        return True

    # Luật 4: Promo riêng cho Klook / App marketing / Blog aggregator
    has_klook_brand = any("klook" in field for field in (content_lower, section_lower, name_lower, source_lower))
    if has_klook_brand:
        if "tải ứng dụng" in content_lower or "betteronapp" in content_lower:
            return True

        date_hits = len(re.findall(r'\d+\s*th\d+\s*20\d{2}', content_lower))
        if date_hits >= 2 and tokens < 250:
            return True

    # Luật 5: Các danh sách điểm đến dài dạng "1 ... 2 ..." chỉ là navigation
    if "điểm đến" in section_lower or "điểm đến" in content_lower:
        enumerated_items = re.findall(r'\b\d{1,2}(?=\s)', content)
        if len(enumerated_items) >= 8 and tokens < 200:
            return True
        
    return False

def post_check_valid(text):
    """Hậu kiểm: chỉ loại bỏ nếu sau khi clean còn dưới 20 token."""
    token_count = len(text.split())
    return token_count >= 20

# --- PHẦN XỬ LÝ FILE VÀ BÁO CÁO (NÂNG CẤP) ---

def process_file(input_file, output_file=None):
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_cleaned{ext}"

    with open(input_file, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Lỗi: File JSON hỏng - {input_file}")
            return

    original_count = len(data)
    cleaned_data = []
    
    # Bộ đếm lý do xóa (để debug nếu cần)
    removed_stats = {"ad_junk": 0, "too_short": 0}

    for item in data:
        # 1. Lọc quảng cáo / Junk chunk
        if is_ad_chunk(item):
            removed_stats["ad_junk"] += 1
            continue
            
        # 2. Làm sạch nội dung
        original_text = item.get("content", "")
        cleaned_text = clean_content(original_text)
        
        # 3. Hậu kiểm
        if post_check_valid(cleaned_text):
            token_count = len(cleaned_text.split())
            item["content"] = cleaned_text
            item["tokens"] = token_count
            cleaned_data.append(item)
        else:
            removed_stats["too_short"] += 1

    # Ghi file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

    if DELETE_SOURCE_AFTER_CLEAN:
        delete_original_file(input_file)
    
    # TÍNH TOÁN THỐNG KÊ
    final_count = len(cleaned_data)
    removed_total = original_count - final_count
    percent_lost = (removed_total / original_count * 100) if original_count > 0 else 0
    
    # IN BÁO CÁO RA MÀN HÌNH
    file_name = os.path.basename(input_file)
    status_icon = "✅"
    
    # Cảnh báo nếu xóa quá 20% dữ liệu
    if percent_lost > 20:
        status_icon = "⚠️ CẢNH BÁO (Xóa nhiều)"
    
    print("-" * 60)
    print(f"File: {file_name}")
    print(f"   • Gốc: {original_count} -> Còn: {final_count}")
    print(f"   • Đã xóa: {removed_total} chunks ({percent_lost:.1f}%)")
    print(f"   • Chi tiết xóa: {removed_stats['ad_junk']} (QC/Rác) + {removed_stats['too_short']} (Quá ngắn)")
    print(f"   • Trạng thái: {status_icon}")

def main():
    # Thư mục chứa data của bạn
    target_dirs = ["mien_nam_data", "mien_bac_data"] 
    
    found_files = False
    print("BẮT ĐẦU QUÉT DỮ LIỆU...\n")
    
    for folder in target_dirs:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                # Logic tìm file: đuôi json, có chữ 'chunks', không có chữ 'cleaned'
                if filename.endswith(".json") and "chunks" in filename and "_cleaned" not in filename:
                    found_files = True
                    full_path = os.path.join(folder, filename)
                    process_file(full_path)
    
    if not found_files:
        print("Không tìm thấy file JSON nào phù hợp để xử lý.")
    else:
        print("\n" + "-" * 60)
        print("HOÀN TẤT QUÁ TRÌNH LÀM SẠCH.")

if __name__ == "__main__":
    main()