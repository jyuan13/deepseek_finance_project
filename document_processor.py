import os
import glob
from typing import List
from .financial_brain import FinancialBrainRAG

class DocumentProcessor:
    """
    文档批量处理器 - 用于初始化知识库
    """
    
    def __init__(self, rag_engine: FinancialBrainRAG):
        self.rag_engine = rag_engine
    
    def process_research_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        处理整个研报目录
        """
        results = {
            "successful": 0,
            "failed": 0,
            "files_processed": []
        }
        
        # 支持多种格式
        pdf_files = glob.glob(os.path.join(directory_path, "**/*.pdf"), recursive=True)
        
        for pdf_file in pdf_files:
            # 从文件名推断标签
            filename = os.path.basename(pdf_file)
            tag = self._infer_tag_from_filename(filename)
            
            print(f"📄 处理: {filename} -> 标签: {tag}")
            
            if self.rag_engine.ingest_pdf_report(pdf_file, tag):
                results["successful"] += 1
                results["files_processed"].append({
                    "file": filename,
                    "tag": tag,
                    "status": "success"
                })
            else:
                results["failed"] += 1
                results["files_processed"].append({
                    "file": filename,
                    "tag": tag, 
                    "status": "failed"
                })
        
        return results
    
    def _infer_tag_from_filename(self, filename: str) -> str:
        """
        从文件名推断内容标签
        """
        filename_lower = filename.lower()
        
        if any(word in filename_lower for word in ['医药', '医疗', '生物', '创新药']):
            return "pharma"
        elif any(word in filename_lower for word in ['芯片', '半导体', '集成电路']):
            return "chips" 
        elif any(word in filename_lower for word in ['新能源', '光伏', '锂电池']):
            return "energy"
        elif any(word in filename_lower for word in ['金融', '银行', '保险', '券商']):
            return "finance"
        elif any(word in filename_lower for word in ['消费', '白酒', '零售']):
            return "consumption"
        else:
            return "general"