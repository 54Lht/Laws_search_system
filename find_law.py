import os
import fitz
import json
import re
from datetime import datetime
from typing import List, Dict, Optional

class FindLawProcessor:
    TARGET_DOCX = ["刑法.docx", "民法典.docx", "行政法.docx", "经济法.docx", "诉讼法.docx"]

    def __init__(self, pdf_dir: str = "laws_doc", index_file: str = "instance/laws_index.json"):
        self.pdf_dir = pdf_dir
        self.index_file = index_file
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要目录存在"""
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)

    def extract_pdf_content(self, pdf_path: str) -> Optional[Dict]:
        """提取文件内容并结构化"""
        try:
            doc = fitz.open(pdf_path)
            articles = []
            current_article = None
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    # 提取章节和条文
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if "第" in line and "章" in line:
                            # 章节信息
                            articles.append({
                                "type": "chapter",
                                "content": line,
                                "page": page_num + 1
                            })
                            current_article = None
                        elif "第" in line and "条" in line:
                            # 条文信息
                            current_article = {
                                "type": "article",
                                "content": line + " ",
                                "page": page_num + 1
                            }
                            articles.append(current_article)
                        elif current_article and line:
                            # 条文具体内容
                            current_article["content"] += line + " "
            
            # 如果没有提取到章节或条文
            if not articles:
                print(f"文件内容不符合要求 {pdf_path}: 未找到章节或条文")
                return None
            
            # 解析文件名获取信息
            filename = os.path.basename(pdf_path)
            name_part, _ = os.path.splitext(filename)
            parts = name_part.split("_")
            
            # 确保 title 仅包含法律名称，content 包含条文内容
            return {
                "title": parts[0] if len(parts) > 0 else "未知法律",
                "year": parts[1] if len(parts) > 1 else datetime.now().year,
                "filename": filename,
                "content": articles,
                "total_pages": len(doc),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(pdf_path)).strftime("%Y-%m-%d")
            }
        except Exception as e:
            print(f"处理PDF出错 {pdf_path}: {str(e)}")
            return None

    def build_index(self) -> List[Dict]:
        """为所有文件建立索引（仅保留章节和条文）"""
        index_data = []
        invalid_files = []
        
        # 确保目录存在
        if not os.path.exists(self.pdf_dir):
            os.makedirs(self.pdf_dir, exist_ok=True)
            print(f"文件目录 {self.pdf_dir} 不存在，已创建")
            return index_data
        
        # 遍历目录
        for filename in os.listdir(self.pdf_dir):
            if filename.lower().endswith(".pdf") or filename.lower().endswith(".docx"):
                file_path = os.path.join(self.pdf_dir, filename)
                law_info = self.extract_pdf_content(file_path)
                if law_info:
                    index_data.append(law_info)
                else:
                    invalid_files.append(filename)
        
        # 确保索引文件目录存在
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        
        # 保存索引
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "index_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_count": len(index_data),
                    "source": "本地文件",
                    "invalid_files": invalid_files
                },
                "laws": index_data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"已为 {len(index_data)} 个文件建立索引")
        if invalid_files:
            print(f"以下文件内容不符合要求，未包含在索引中: {', '.join(invalid_files)}")
        return index_data

    def search(self, keyword: str, law_type: str = "all") -> List[Dict]:
        """搜索索引中的关键词（完全匹配）"""
        # 检查索引是否存在，不存在则创建
        if not os.path.exists(self.index_file):
            print("索引文件不存在，正在创建...")
            self.build_index()
        
        # 加载索引数据
        with open(self.index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        keyword_lower = keyword.lower()
        
        for law in data["laws"]:
            # 筛选法律类型
            if law_type != "all" and law["title"].lower() != law_type.lower():
                continue
            
            # 搜索内容
            matched_articles = {}  # 使用字典来按条文组织匹配结果
            
            for item in law["content"]:
                content = item["content"]
                text_lower = content.lower()
                
                # 检查是否包含用户输入的关键词
                if keyword_lower in text_lower:
                    # 提取条文标题（如"第十四条"）
                    article_title = self.extract_article_title(content)
                    
                    # 如果这个条文还没有记录，初始化
                    if article_title not in matched_articles:
                        matched_articles[article_title] = {
                            "title": article_title,
                            "content": content,
                            "matches": []
                        }
                    
                    # 找到所有匹配位置
                    start = 0
                    while True:
                        idx = text_lower.find(keyword_lower, start)
                        if idx == -1:
                            break
                        
                        # 记录匹配位置
                        matched_articles[article_title]["matches"].append({
                            "start": idx,
                            "end": idx + len(keyword_lower)
                        })
                        start = idx + len(keyword_lower)
            
            # 为每个匹配的条文生成高亮内容
            matched_pages = []
            for article_title, article_data in matched_articles.items():
                # 高亮所有匹配的关键词
                highlighted_content = self.highlight_all_keywords(
                    article_data["content"], 
                    article_data["matches"],
                    keyword
                )
                
                matched_pages.append({
                    "title": article_title,
                    "snippet": highlighted_content,
                    "matched_term": keyword,
                    "match_count": len(article_data["matches"])
                })
            
            if matched_pages:
                results.append({
                    "title": law["title"],
                    "year": law["year"],
                    "filename": law["filename"],
                    "total_pages": law.get("total_pages", 1),
                    "matched_pages": matched_pages,
                    "total_matches": sum(page["match_count"] for page in matched_pages)
                })
        
        # 按匹配数量排序
        if not results:
            print(f"未找到与关键词 '{keyword}' 和法律类型 '{law_type}' 匹配的内容")
            return []
        return sorted(results, key=lambda x: x["total_matches"], reverse=True)

    def extract_article_title(self, content: str) -> str:
        """从内容中提取条文标题（如'第十四条'）"""
        # 查找"第X条"格式的标题
        match = re.search(r'第[零一二三四五六七八九十百千]+条', content)
        if match:
            return match.group(0)
        
        # 如果找不到条文标题，查找章节标题
        chapter_match = re.search(r'第[零一二三四五六七八九十百千]+章', content)
        if chapter_match:
            return chapter_match.group(0)
        
        # 如果都找不到，返回内容的前30个字符作为标题
        return content[:30] + "..." if len(content) > 30 else content

    def highlight_all_keywords(self, text: str, matches: List[Dict], keyword: str) -> str:
        """在文本中高亮显示所有匹配的关键词"""
        # 按匹配位置从后往前处理，避免索引偏移
        matches_sorted = sorted(matches, key=lambda x: x["start"], reverse=True)
        
        highlighted_text = text
        for match in matches_sorted:
            start = match["start"]
            end = match["end"]
            
            # 插入高亮标签
            highlighted_text = (
                highlighted_text[:start] +
                f'<span class="highlight">{highlighted_text[start:end]}</span>' +
                highlighted_text[end:]
            )
        
        return highlighted_text

    def get_law_types(self) -> List[str]:
        """获取所有法律类型"""
        if not os.path.exists(self.index_file):
            self.build_index()
        
        with open(self.index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return list(set(law["title"] for law in data["laws"]))