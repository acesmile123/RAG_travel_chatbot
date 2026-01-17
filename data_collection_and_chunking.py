import json
import uuid
import os
from selenium import webdriver
from readability import Document
from bs4 import BeautifulSoup
import markdownify
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter
)


def crawl_html(url, output_html):
    """Crawl HTML bằng Selenium và lưu file."""
    driver = webdriver.Chrome()
    driver.get(url)

    html = driver.page_source
    driver.quit()

    with open(output_html, "w", encoding="utf-8") as file:
        file.write(html)

    print(f"✅ Đã crawl và lưu HTML vào: {output_html}")
    return output_html


def extract_markdown_from_html(html_file):
    """Lấy main content từ HTML → chuyển sang Markdown."""
    # 1) ĐỌC RAW HTML
    with open(html_file, "r", encoding="utf-8") as f:
        raw_html = f.read()

    # 2) DÙNG READABILITY LẤY MAIN CONTENT (BỎ HẾT SCRIPT, HEADER, FOOTER, NAV…)
    doc = Document(raw_html)
    main_html = doc.summary()
    title = doc.short_title() or ""

  
    soup = BeautifulSoup(main_html, "html.parser")
    for t in soup(["script", "style", "noscript", "template", "svg", "iframe"]):
        t.decompose()
    clean_main_html = str(soup)

    # 3) CONVERT HTML → MARKDOWN
    markdown_text = markdownify.markdownify(clean_main_html, heading_style="ATX")

    return markdown_text, title


def detect_type(section):
    """Detect TYPE của section."""
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


def chunk_markdown(markdown_text, title, province, source="vinpearl"):
    """Chunk Markdown theo headers và chia nhỏ."""
    # 1) tách heading Markdown
    headers = [
        ("#", "title"),
        ("##", "section"),
        ("###", "subsection")
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
    md_docs = md_splitter.split_text(markdown_text)

    # 2) tạo splitter nhỏ
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=400,
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
                "id": str(uuid.uuid4()),
                "province": province,
                "source": source,
                "section": section_name,
                "type": section_type,
                "name": section_name,
                "content": chunk,
                "tokens": int(len(chunk.split()) * 1.3)
            })

    return final_chunks


def save_json(new_chunks, filename):
    out_path = os.path.join("mien_trung_data", filename)

    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            old_chunks = json.load(f)
    else:
        old_chunks = []

  
    merged_chunks = old_chunks + new_chunks

    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged_chunks, f, ensure_ascii=False, indent=2)

    print(
        f"💾 Saved: {out_path} "
        f"(+{len(new_chunks)} new, total {len(merged_chunks)})"
    )



def run():
    PROVINCE_URLS = {
    "da_nang": [
        "https://vinpearl.com/vi/du-lich-da-nang-vui-quen-loi-ve-tron-bo-cam-nang-a-z",
        "https://vinpearl.com/vi/tat-tan-tat-tu-a-z-cam-nang-du-lich-da-nang-tu-tuc",
        "https://vinwonders.com/vi/wonderpedia/news/du-lich-da-nang-day-du-chi-tiet/",
    ],
    "hue": [
        "https://vinpearl.com/vi/du-lich-hue-tong-hop-cac-thong-tin-can-biet",
        "https://vinwonders.com/vi/wonderpedia/news/kinh-nghiem-du-lich-hue-tu-tuc/",
        "https://vinpearl.com/vi/chua-thien-mu-hue-kham-pha-ngoi-chua-thieng-400-nam-tuoi",
        "https://vinpearl.com/vi/dai-noi-hue-huong-dan-tham-quan-tim-ve-dau-an-lich-su-co-do",
        "https://vinpearl.com/vi/lang-khai-dinh-hue-dinh-cao-kien-truc-lang-tam-thoi-nguyen",

    ],
    "quang_binh": [
        "https://vinpearl.com/vi/du-lich-quang-binh-cam-nang-tu-a-den-z",
    ],
    "nghe_an": [
        "https://vinpearl.com/vi/khu-du-lich-ve-nguon-hue-kinh-nghiem-di-lai-an-uong-vui-choi-tu-a-z"
    ]
}


    all_chunks = [] 

    for province, urls in PROVINCE_URLS.items():
        print(f"\n🚀 Crawling province: {province}")

        province_chunks = []

        for i, url in enumerate(urls):
            print(f"   🌐 Crawling URL {i+1}/{len(urls)}")

            html_file = f"{province}.html"


       # 1) Crawl HTML
            html_file = crawl_html(url, html_file)

       # 2) Extract Markdown
            markdown_text, title = extract_markdown_from_html(html_file)

        # 3) Chunk Markdown
            chunks = chunk_markdown(
              markdown_text,
              title,
              province=province,
              source="vinpearl"
        )
            province_chunks.extend(chunks)

            

        save_json(province_chunks, f"{province}_chunks.json")

        all_chunks.extend(province_chunks)

    # 4) Save JSON
    save_json(all_chunks, "vinpearl_vietnam_chunks.json")


if __name__ == "__main__":
    run()

