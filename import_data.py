import os
from dotenv import load_dotenv
from criminal_law import CriminalLawProcessor

def main():
    # 加载环境变量
    load_dotenv()
    pdf_dir = os.getenv("PDF_DIR", "laws_pdf")
    index_file = os.getenv("INDEX_FILE", "instance/laws_index.json")
    
    # 初始化处理器
    processor = CriminalLawProcessor(pdf_dir, index_file)
    
    print(f"开始为 {pdf_dir} 目录下的PDF文件建立索引...")
    count = len(processor.build_index())
    print(f"索引建立完成，共处理 {count} 个PDF文件")
    print(f"索引文件已保存至 {index_file}")

if __name__ == "__main__":
    main()