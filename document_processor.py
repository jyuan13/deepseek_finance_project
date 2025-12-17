# deepseek_finance_project_V3/document_processor.py

"""
==========================================================================================
【文件定义】
文件名: document_processor.py
类名  : DocumentProcessor
==========================================================================================
【函数清单与逻辑流】

1. __init__
   [初始化] -> [无特殊依赖]

2. extract_text_from_pdf(pdf_path)
   [打开PDF (pdfplumber)] -> [遍历页面] -> [提取文本]
          ↓
   [清洗文本 (clean_text)] -> [返回纯文本字符串]

3. clean_text(text)
   [去除多余换行] -> [去除特殊字符] -> [标准化格式]
==========================================================================================
"""

import pdfplumber
import re
import os

class DocumentProcessor:
    """
    文档处理工具类
    职责：仅负责从各种文件中提取清洗后的文本。
    注意：此类不应依赖 FinancialBrain，以防止循环引用。
    """
    def __init__(self):
        pass

    def extract_text_from_pdf(self, pdf_path):
        """
        从PDF中提取全量文本
        :param pdf_path: PDF文件路径
        :return: 清洗后的字符串
        """
        if not os.path.exists(pdf_path):
            print(f"❌ 文件不存在: {pdf_path}")
            return ""
            
        full_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"📄 开始解析 PDF (共 {len(pdf.pages)} 页)...")
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            return self.clean_text(full_text)
            
        except Exception as e:
            print(f"❌ PDF 解析异常: {e}")
            return ""

    def clean_text(self, text):
        """
        文本清洗标准化
        """
        if not text: return ""
        
        # 1. 替换连续空格
        text = re.sub(r'\s+', ' ', text)
        # 2. 修复常见的中文章节断行 (可选)
        # text = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', text) 
        
        return text.strip()