# deepseek_finance_project_V3/financial_brain.py

"""
==========================================================================================
【文件定义】
文件名: financial_brain.py
类名  : FinancialBrainRAG
==========================================================================================
【函数清单与逻辑流 (Function Logic Flow)】

1. __init__(persist_directory)
   [Init ChromaDB Client] -> [Load SentenceTransformer Model] -> [Call _init_collections]

2. _init_collections
   [Get/Create Collection: research_reports, market_history, financial_news]

3. reset_all_memories
   [Loop: Delete Collections] -> [Re-init]

4. ingest_pdf_report(file_path, tag)
   [DocumentProcessor.extract_text] -> [Split] -> [Store to DB]

5. ingest_online_research(url, tag)
   [Fetch News] -> [Store to DB]

6. auto_fetch_institutional_views(top_n)
   [AkShare API] -> [Filter Orgs] -> [Format] -> [Store to DB]

7. retrieve_expert_logic
   [Query knowledge_base]

8. memorize_market_state
   [Store to experience_base]

9. recall_similar_history
   [Query experience_base]

10. retrieve_recent_news
    [Query news_base]

11. get_context_for_analysis
    [Combined Query]

12. get_collection_stats
    [Count]
==========================================================================================
"""

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

# [Fix] 适配 LangChain v0.2+
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        pass # Will handle later or assume basic split

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# [Fix] 引用解耦后的 DocumentProcessor
from document_processor import DocumentProcessor

class FinancialBrainRAG:
    """
    金融大脑RAG系统 - 研报知识库 + 历史经验记忆
    """
    def __init__(self, persist_directory="./brain_memory"):
        self.persist_directory = persist_directory
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
            
        print("🧠 初始化 RAG 记忆体 (ChromaDB + M3E)...")
        self.embeddings = HuggingFaceEmbeddings(model_name="moka-ai/m3e-small")
        
        # 兼容性 Client
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        self.target_institutions = [
            "中信证券", "中金公司", "华泰证券", "国泰君安", "海通证券", 
            "广发证券", "招商证券", "申万宏源", "银河证券", "天风证券",
            "Goldman Sachs", "Morgan Stanley", "UBS", "摩根", "高盛", "瑞银"
        ]
        
        self.doc_processor = DocumentProcessor()
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
        """重置所有记忆库"""
        try:
            for name in ["research_reports", "market_history", "financial_news"]:
                try: self.client.delete_collection(name)
                except: pass
            self._init_collections()
            print("✅ RAG 记忆库已全部重置")
            return True
        except Exception as e:
            print(f"❌ RAG 重置失败: {e}")
            return False

    def ingest_pdf_report(self, file_path: str, tag: str = "general") -> bool:
        """摄入PDF研报"""
        print(f"🧠 学习研报: {os.path.basename(file_path)}")
        try:
            # 使用解耦后的 DocumentProcessor
            text = self.doc_processor.extract_text_from_pdf(file_path)
            
            if not text.strip():
                print(f"❌ 无法从 {file_path} 提取文本")
                return False

            # 分块
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = splitter.split_text(text)

            ids = [f"{tag}_{os.path.basename(file_path)}_{i}" for i in range(len(chunks))]
            metadatas = [{
                "source": file_path, 
                "tag": tag, 
                "date": datetime.datetime.now().isoformat(),
                "chunk_size": len(c)
            } for c in chunks]

            self.knowledge_base.add(documents=chunks, ids=ids, metadatas=metadatas)
            print(f"✅ 已存入 {len(chunks)} 个知识片段")
            return True
        except Exception as e:
            print(f"❌ 研报处理失败: {e}")
            return False

    def ingest_online_research(self, url: str, tag: str) -> bool:
        """从在线资源摄入研报"""
        try:
            news_data = ak.news_roll(field="财经")
            if not news_data.empty:
                documents = news_data['title'].head(10).tolist()
                ids = [f"news_{tag}_{i}_{datetime.datetime.now().timestamp()}" for i in range(len(documents))]
                metadatas = [{"source": url, "tag": tag, "type": "news"} for _ in documents]
                self.news_base.add(documents=documents, ids=ids, metadatas=metadatas)
                print(f"✅ 已存入 {len(documents)} 条新闻")
                return True
        except Exception as e:
            print(f"❌ 在线资源处理失败: {e}")
        return False

    def auto_fetch_institutional_views(self, top_n: int = 50):
        """自动获取顶级投行研报"""
        print("🌍 正在连接机构研报数据库 (Source: EastMoney)...")
        try:
            df = ak.stock_report_layout_4_0(prefix="策略报告")
            if df.empty:
                print("⚠️ 未获取到研报数据")
                return

            print(f"📄 获取到 {len(df)} 条最新研报，正在筛选顶级机构观点...")
            
            # Debug Print
            cols_to_show = [c for c in ['report_date', 'org_name', 'title'] if c in df.columns]
            if not cols_to_show: cols_to_show = df.columns[:3]
            print("\n📋 [数据透视] (前10条):")
            print(df[cols_to_show].head(10).to_string(index=False))
            print("-" * 60)
            
            # Map columns
            found_map = {}
            for target, candidates in {
                '报告名称': ['title', '报告名称', 'infoTitle'],
                '机构': ['org_name', '机构名称', 'orgName'],
                '日期': ['report_date', 'publishDate', 'datetime']
            }.items():
                for c in candidates:
                    if c in df.columns:
                        found_map[c] = target
                        break
            df = df.rename(columns=found_map)
            
            if '机构' not in df.columns: return

            pattern = '|'.join(self.target_institutions)
            target_df = df[df['机构'].astype(str).str.contains(pattern, na=False)].head(top_n)
            
            if target_df.empty:
                print(f"⚠️ 最近没有目标机构 ({self.target_institutions[:3]}...) 的研报更新。")
                return
                
            print(f"🔍 筛选出 {len(target_df)} 份高价值研报...")
            
            count = 0
            ids = []
            docs = []
            metas = []
            
            for _, row in target_df.iterrows():
                title = row.get('报告名称', 'No Title')
                org = row.get('机构', 'Unknown')
                date = row.get('日期', str(datetime.datetime.now().date()))
                content = f"【机构观点】{date} {org} 发布策略报告：{title}。"
                doc_id = f"report_{date}_{org}_{count}_{datetime.datetime.now().timestamp()}"
                
                docs.append(content)
                ids.append(doc_id)
                metas.append({"source": "akshare_auto", "organ": org, "date": str(date)})
                count += 1
                print(f"   📥 捕获: [{org}] {title[:30]}...")

            if docs:
                self.knowledge_base.add(documents=docs, ids=ids, metadatas=metas)
                print(f"✅ 已成功存入 {count} 条机构观点。")
            
        except Exception as e:
            print(f"❌ 抓取失败: {e}")

    def retrieve_expert_logic(self, query_topic: str, n_results: int = 3) -> List[str]:
        """检索专家观点"""
        try:
            results = self.knowledge_base.query(query_texts=[query_topic], n_results=n_results)
            return results['documents'][0] if results['documents'] else []
        except: return []

    def memorize_market_state(self, date: str, macro_summary: Dict, ai_prediction: str, actual_outcome: str) -> bool:
        """记忆市场状态"""
        try:
            state_text = f"状态:{json.dumps(macro_summary, ensure_ascii=False)}\n预测:{ai_prediction}\n结果:{actual_outcome}"
            self.experience_base.add(
                documents=[state_text],
                metadatas=[{"date": date, "outcome": actual_outcome}],
                ids=[f"hist_{date}_{datetime.datetime.now().timestamp()}"]
            )
            print(f"💾 已归档经验: {date}")
            return True
        except Exception as e:
            print(f"❌ 记忆失败: {e}")
            return False

    def recall_similar_history(self, current_macro_state: Dict, n_results: int = 2) -> List[str]:
        """回忆相似历史"""
        try:
            q = f"当前状态: {json.dumps(current_macro_state, ensure_ascii=False)}"
            results = self.experience_base.query(query_texts=[q], n_results=n_results)
            return results['documents'][0] if results['documents'] else []
        except: return []

    def retrieve_recent_news(self, topics: List[str], n_results: int = 5) -> List[str]:
        """检索新闻"""
        try:
            q = " ".join(topics)
            results = self.news_base.query(query_texts=[q], n_results=n_results)
            return results['documents'][0] if results['documents'] else []
        except: return []

    def get_context_for_analysis(self, symbol: str, sector: str, current_macro: Dict) -> Dict[str, Any]:
        """为分析提供综合上下文"""
        context = {
            "expert_views": [], "historical_patterns": [], "sector_news": []
        }
        queries = [f"{sector}行业分析", f"{symbol}投资价值", f"顶级投行 {sector}"]
        for q in queries:
            context["expert_views"].extend(self.retrieve_expert_logic(q, n_results=2))
        context["expert_views"] = list(set(context["expert_views"]))
        
        context["historical_patterns"] = self.recall_similar_history(current_macro)
        context["sector_news"] = self.retrieve_recent_news([sector, symbol], n_results=3)
        return context

    def get_collection_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        stats = {}
        try:
            stats["knowledge_base"] = self.knowledge_base.count()
            stats["experience_base"] = self.experience_base.count()
            stats["news_base"] = self.news_base.count()
        except: pass
        return stats