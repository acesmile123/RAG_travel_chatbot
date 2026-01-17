from selenium import webdriver
driver = webdriver.Chrome()
url = "https://2025.vietnam.travel/bac-ninh-diem-den-du-lich-hoi-tu-tinh-hoa-van-hoa/"
driver.get(url)
html = driver.page_source
driver.quit()
with open("output_BacNinh.html", "w", encoding="utf-8") as file:
    file.write(html)

from readability import Document
from bs4 import BeautifulSoup
import markdownify
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
import json

HTML_FILE = "output_BacNinh_2.html"
OUT_FILE  = "vinpearl_chunks_markdown_BacNinh_2.json"

# 1) ĐỌC RAW HTML
with open(HTML_FILE, "r", encoding="utf-8") as f:
    raw_html = f.read()

# 2) DÙNG READABILITY LẤY MAIN CONTENT (BỎ HẾT SCRIPT, HEADER, FOOTER, NAV…)
doc = Document(raw_html)
main_html = doc.summary()
title    = doc.short_title() or ""


soup = BeautifulSoup(main_html, "html.parser")
for t in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
    t.decompose()
clean_main_html = str(soup)

# 3) CONVERT HTML → MARKDOWN
markdown_text = markdownify.markdownify(clean_main_html, heading_style="ATX")

# 4) DÙNG MARKDOWN HEADER SPLITTER
headers = [
    ("#", "title"),
    ("##", "section"),
    ("###", "subsection"),
]

md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers
)

md_docs = md_splitter.split_text(markdown_text)

print("Số doc theo heading:", len(md_docs))

# 5) CHIA NHỎ THÊM NẾU SECTION DÀI
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=80,
)

chunks = []
for d in md_docs:
    small_chunks = text_splitter.split_text(d.page_content)
    for c in small_chunks:
        meta = d.metadata.copy()
        meta["page_title"] = title  # thêm title bài viết
        chunks.append({
            "content": c,
            "metadata": meta
        })

# 6) LƯU RA JSON
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(" Đã tạo", len(chunks), "chunks sạch (markdown-based)")
print(" Lưu tại:", OUT_FILE)
import uuid
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

PROVINCE = "bac_ninh"
SOURCE = "vinpearl"


# ---- 1. Hàm xác định TYPE (dựa trên heading) ----
def detect_type(section):
    s = section.lower()
    if any(k in s for k in ["địa điểm", "bãi biển", "chơi gì", "check in"]):
        return "destination"
    if any(k in s for k in ["khách sạn", "resort", "lưu trú"]):
        return "accommodation"
    if any(k in s for k in ["ăn gì", "ẩm thực", "món ăn", "nhà hàng"]):
        return "food"
    if any(k in s for k in ["di chuyển", "phương tiện", "xe", "máy bay"]):
        return "transportation"
    if any(k in s for k in ["chi phí", "giá", "vé"]):
        return "pricing"
    if any(k in s for k in ["thời điểm", "thời gian", "mùa"]):
        return "schedule"
    return "general"


# ---- 2. Tách heading Markdown ----
headers = [
    ("#", "title"),
    ("##", "section"),
    ("###", "subsection")
]
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
md_docs = md_splitter.split_text(markdown_text)   # markdown_text = HTML -> Markdown


# ---- 3. Chunk nhỏ hơn ----
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=900,
    chunk_overlap=100,
)

final_chunks = []

for doc in md_docs:
    small_chunks = text_splitter.split_text(doc.page_content)

    section_name = (
        doc.metadata.get("section")
        or doc.metadata.get("subsection")
        or doc.metadata.get("title")
        or "Nội dung"
    )

    section_type = detect_type(section_name)

    for chunk in small_chunks:
        final_chunks.append({
            "id": uuid.uuid4().hex[:12],
            "province": PROVINCE,
            "source": SOURCE,
            "section": section_name,
            "type": section_type,
            "name": section_name,  # đủ để nhận biết
            "content": chunk,
            "tokens": int(len(chunk.split()) * 1.3)
        })


print("Tổng số chunks:", len(final_chunks))

import json
with open("vinpearl_chunks_simple_BacNinh_2.json", "w", encoding="utf-8") as f:
    json.dump(final_chunks, f, ensure_ascii=False, indent=2)

print("Đã lưu file: vinpearl_chunks_simple_BacNinh_2.json")