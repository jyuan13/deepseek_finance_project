# deepseek_finance_project_V3/financial_brain.py

import chromadb
from chromadb.utils import embedding_functions
import pdfplumber
import os
import datetime
import json
import requests
from typing import List, Dict, Any, Optional
import akshare as ak
import pandas as pd

class FinancialBrainRAG:
    def __init__(self, persist_directory="./brain_memory"):
        """
        金融大脑RAG系统 - 研报知识库 + 历史经验记忆
        """
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 使用更适合中文的嵌入模型
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"  # 多语言模型，中文效果更好
        )

        self._init_collections()

    def _init_collections(self):
        """初始化所有集合"""
        self.knowledge_base = self.client.get_or_create_collection(
            name="research_reports",
            embedding_function=self.emb_fn,
            metadata={"description": "券商研报和行业分析"}
        )
        
        self.experience_base = self.client.get_or_create_collection(
            name="market_history", 
            embedding_function=self.emb_fn,
            metadata={"description": "历史市场状态和预测结果"}
        )
        
        self.news_base = self.client.get_or_create_collection(
            name="financial_news",
            embedding_function=self.emb_fn,
            metadata={"description": "财经新闻和政策动态"}
        )

    def reset_all_memories(self):
        """[新增] 重置所有记忆库"""
        try:
            # 删除现有集合
            for name in ["research_reports", "market_history", "financial_news"]:
                try:
                    self.client.delete_collection(name)
                except:
                    pass
            
            # 重新创建
            self._init_collections()
            print("✅ RAG 记忆库已全部重置")
            return True
        except Exception as e:
            print(f"❌ RAG 重置失败: {e}")
            return False

    # ==========================================
    # 📚 研报知识库管理
    # ==========================================

    def ingest_pdf_report(self, file_path: str, tag: str = "general") -> bool:
        """
        摄入PDF研报到知识库
        """
        print(f"🧠 学习研报: {os.path.basename(file_path)}")
        
        try:
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            if not full_text.strip():
                print(f"❌ 无法从 {file_path} 提取文本")
                return False

            # 智能分块 - 按段落分割
            paragraphs = [p for p in full_text.split('\n\n') if p.strip()]
            chunks = []
            current_chunk = ""
            
            for para in paragraphs:
                if len(current_chunk) + len(para) < 800:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
            
            if current_chunk:
                chunks.append(current_chunk.strip())

            # 存入向量数据库
            ids = [f"{tag}_{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
            metadatas = [{
                "source": file_path, 
                "tag": tag, 
                "date": datetime.datetime.now().isoformat(),
                "chunk_size": len(chunk)
            } for chunk in chunks]

            self.knowledge_base.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            
            print(f"✅ 已存入 {len(chunks)} 个知识片段")
            return True
            
        except Exception as e:
            print(f"❌ 研报处理失败: {e}")
            return False

    def ingest_online_research(self, url: str, tag: str) -> bool:
        """
        从在线资源摄入研报（简化版）
        """
        try:
            # 这里可以扩展为真实的网页抓取
            # 目前使用akshare获取财经新闻作为示例
            news_data = ak.news_roll(field="财经")
            if not news_data.empty:
                documents = news_data['title'].head(10).tolist()
                
                ids = [f"news_{tag}_{i}" for i in range(len(documents))]
                metadatas = [{"source": url, "tag": tag, "type": "news"} for _ in documents]
                
                self.news_base.add(
                    documents=documents,
                    ids=ids,
                    metadatas=metadatas
                )
                print(f"✅ 已存入 {len(documents)} 条新闻")
                return True
                
        except Exception as e:
            print(f"❌ 在线资源处理失败: {e}")
            
        return False

    def auto_fetch_institutional_views(self, top_n: int = 50):
        """
        [新增] 自动获取顶级投行（摩根/高盛/中金等）的最新研报观点并存入知识库
        """
        print("🌍 正在连接机构研报数据库 (Source: EastMoney)...")
        
        # 定义我们需要关注的顶级机构关键词
        target_orgs = ['摩根', '高盛', '瑞银', '中金', '中信', '天风']
        
        try:
            # 获取最新的研报列表
            report_df = ak.stock_research_report_em()
            
            if report_df is None or report_df.empty:
                print("❌ 未获取到研报数据")
                return

            print(f"📄 获取到 {len(report_df)} 条最新研报，正在筛选顶级机构观点...")
            
            # --- 修复列名匹配逻辑 ---
            # 定义可能的列名映射（优先级从左到右）
            col_mappings = {
                'organ': ['机构', '机构名称', 'orgName', 'institution'],
                'title': ['报告名称', '研报标题', 'title', 'infoCode'],
                'stock': ['股票简称', '股票名称', 'stockName', 'name'],
                'rating': ['东财评级', '评级', 'emRatingName', 'rate'],
                'date': ['日期', 'publishDate', 'createDate']
            }
            
            # 自动寻找存在的列名
            found_cols = {}
            for key, candidates in col_mappings.items():
                for col in candidates:
                    if col in report_df.columns:
                        found_cols[key] = col
                        break
            
            # 检查关键列是否存在
            if 'organ' not in found_cols:
                print(f"❌ 关键列名匹配失败。无法找到'机构'列。现有列: {report_df.columns.tolist()}")
                return

            org_col = found_cols['organ']
            print(f"✅ 适配成功: 机构列='{org_col}', 标题列='{found_cols.get('title')}'")

            # 筛选包含关键词的机构
            filtered_df = report_df[report_df[org_col].astype(str).str.contains('|'.join(target_orgs))]
            
            if filtered_df.empty:
                print("⚠️ 最近没有目标机构的研报更新")
                return

            # 准备存入知识库
            documents = []
            metadatas = []
            ids = []
            
            count = 0
            # 遍历筛选后的研报
            for _, row in filtered_df.head(top_n).iterrows():
                # 提取字段 (使用找到的列名，如果没找到则给默认值)
                date = row.get(found_cols.get('date'), 'Unknown')
                title = row.get(found_cols.get('title'), 'No Title')
                organ = row.get(org_col, 'Unknown')
                stock_name = row.get(found_cols.get('stock'), '')
                rating = row.get(found_cols.get('rating'), '')
                
                # 构建高价值的知识文本
                content = f"【机构观点】{date} {organ} 发布研报：{title}。涉及标的：{stock_name}。评级：{rating}。"
                
                # 检查是否重复 (简单通过ID判断，ID包含日期和标题哈希会更好，这里简化使用组合字符串)
                doc_id = f"report_{date}_{organ}_{stock_name}_{count}"
                
                documents.append(content)
                metadatas.append({
                    "source": "auto_fetch_akshare",
                    "tag": "institutional_view",
                    "date": str(date),
                    "organ": str(organ)
                })
                ids.append(doc_id)
                count += 1
                print(f"  - 捕获: {organ} -> {title[:30]}...")

            if documents:
                # 存入 knowledge_base
                self.knowledge_base.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"✅ 成功存入 {count} 条顶级机构观点到 RAG 知识库")
            else:
                print("⚠️ 筛选后无有效内容")

        except Exception as e:
            print(f"❌ 自动获取研报失败: {e}")
            import traceback
            traceback.print_exc()

    def retrieve_expert_logic(self, query_topic: str, n_results: int = 3) -> List[str]:
        """
        检索专家观点和研报逻辑
        """
        try:
            results = self.knowledge_base.query(
                query_texts=[query_topic],
                n_results=n_results
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            print(f"❌ 知识检索失败: {e}")
            return []

    # ==========================================
    # 🕰️ 历史经验记忆
    # ==========================================

    def memorize_market_state(self, date: str, macro_summary: Dict, 
                            ai_prediction: str, actual_outcome: str) -> bool:
        """
        记忆市场状态和预测结果
        """
        try:
            state_text = f"""
市场状态: {json.dumps(macro_summary, ensure_ascii=False)}
预测: {ai_prediction}
结果: {actual_outcome}
时间: {date}
"""
            self.experience_base.add(
                documents=[state_text],
                metadatas=[{
                    "date": date, 
                    "outcome": actual_outcome,
                    "prediction": ai_prediction
                }],
                ids=[f"history_{date}_{datetime.datetime.now().timestamp()}"]
            )
            print(f"💾 已归档历史经验: {date}")
            return True
            
        except Exception as e:
            print(f"❌ 历史记忆失败: {e}")
            return False

    def recall_similar_history(self, current_macro_state: Dict, n_results: int = 2) -> List[str]:
        """
        回忆相似的历史市场状态
        """
        try:
            query_text = f"当前市场状态: {json.dumps(current_macro_state, ensure_ascii=False)}"
            
            results = self.experience_base.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            print(f"❌ 历史回忆失败: {e}")
            return []

    # ==========================================
    # 📰 新闻和政策检索
    # ==========================================

    def retrieve_recent_news(self, topics: List[str], n_results: int = 5) -> List[str]:
        """
        检索相关新闻和政策动态
        """
        try:
            query_text = " ".join(topics)
            results = self.news_base.query(
                query_texts=[query_text],
                n_results=n_results
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            print(f"❌ 新闻检索失败: {e}")
            return []

    # ==========================================
    # 🧩 综合检索接口
    # ==========================================

    def get_context_for_analysis(self, symbol: str, sector: str, 
                               current_macro: Dict) -> Dict[str, Any]:
        """
        为分析提供综合上下文
        """
        context = {
            "expert_views": [],
            "historical_patterns": [],
            "sector_news": []
        }
        
        # 1. 检索专家观点
        expert_queries = [
            f"{sector}行业分析",
            f"{sector}投资逻辑", 
            f"{sector}政策影响",
            f"摩根大通 {sector}",  # 显式增加对顶级投行的检索权重
            f"高盛 {sector}"
        ]
        
        for query in expert_queries:
            views = self.retrieve_expert_logic(query, n_results=2)
            context["expert_views"].extend(views)
        
        # 去重
        context["expert_views"] = list(set(context["expert_views"]))
        
        # 2. 检索历史模式
        historical_patterns = self.recall_similar_history(current_macro)
        context["historical_patterns"] = historical_patterns
        
        # 3. 检索行业新闻
        sector_news = self.retrieve_recent_news([sector, "政策", "行业"], n_results=3)
        context["sector_news"] = sector_news
        
        return context

    def get_collection_stats(self) -> Dict[str, int]:
        """
        获取各记忆库的统计信息
        """
        stats = {}
        try:
            stats["knowledge_base"] = self.knowledge_base.count()
            stats["experience_base"] = self.experience_base.count() 
            stats["news_base"] = self.news_base.count()
        except Exception as e:
            print(f"❌ 获取统计失败: {e}")
            
        return stats