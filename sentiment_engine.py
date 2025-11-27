import akshare as ak
import tushare as ts
import datetime
import pandas as pd
from typing import Dict, List, Any

class SentimentEngine:
    """
    舆情分析引擎 - 负责收集和分析市场情绪数据
    """
    
    def __init__(self, tushare_token=None):
        self.pro = ts.pro_api(tushare_token) if tushare_token else None
        self.sector_keywords = {
            'pharma': ['医药', '生物', '医疗', '医保', '集采', '创新药', '疫苗'],
            'tech': ['半导体', '芯片', '人工智能', 'AI', '算力', '光刻机', '华为'],
            'finance': ['银行', '保险', '券商', '金融', '降准', '降息', '信贷'],
            'energy': ['新能源', '光伏', '锂电池', '储能', '碳中和', '绿色能源'],
            'consumption': ['消费', '白酒', '零售', '电商', '双十一', '旅游']
        }
    
    def get_sentiment_data(self, target_symbols: List[str] = None) -> Dict[str, Any]:
        """
        获取完整的舆情数据包，包括政策信号和散户热度
        target_symbols: 需要监控热度的标的代码列表
        """
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'policy_signals': self._get_policy_signals(),
            'market_rumors': self._get_market_rumors(),
            'sector_news': self._get_sector_specific_news(),
            'sentiment_indicators': self._get_sentiment_indicators(),
            'retail_attention': self._get_retail_attention(target_symbols) if target_symbols else {}
        }
    
    def _get_policy_signals(self) -> List[str]:
        """获取政策信号"""
        policy_signals = []
        
        try:
            # 新闻联播数据
            # 逻辑：尝试获取今天或昨天的数据（防止当天晚7点前数据未更新）
            for delta in [0, 1]: 
                date_str = (datetime.datetime.now() - datetime.timedelta(days=delta)).strftime('%Y%m%d')
                try:
                    cctv_news = ak.news_cctv_xwlb_em(date=date_str)
                    if not cctv_news.empty:
                        top_news = cctv_news.head(3)['title'].tolist()
                        policy_signals.extend([f"新闻联播({date_str}): {news}" for news in top_news])
                        break # 如果获取成功，就不再尝试前一天
                except:
                    continue # 获取失败则尝试前一天
            
            # 如果两天都没获取到
            if not policy_signals:
                policy_signals.append("新闻联播数据暂不可用")
                
        except Exception as e:
            policy_signals.append(f"新闻联播获取异常: {str(e)}")
        
        return policy_signals[:5]
    
    def _get_market_rumors(self) -> List[str]:
        """获取市场传闻"""
        rumors = []
        
        try:
            cls_news = ak.stock_tease_cls_impl(limit=30)
            if not cls_news.empty:
                macro_keywords = [
                    '美联储', '央行', '降息', '加息', '通胀', 'GDP',
                    '贸易', '关税', '制裁', '实体清单', '限售', '监管'
                ]
                
                for _, row in cls_news.iterrows():
                    content = row.get('content', '')
                    if any(keyword in content for keyword in macro_keywords):
                        simplified = content[:80] + "..." if len(content) > 80 else content
                        rumors.append(f"快讯: {simplified}")
        except Exception as e:
            rumors.append("市场快讯数据暂不可用")
        
        return rumors[:8]
    
    def _get_sector_specific_news(self) -> Dict[str, List[str]]:
        """获取行业特定新闻"""
        sector_news = {}
        
        try:
            industry_news = ak.news_industry()
            if not industry_news.empty:
                for sector in self.sector_keywords.keys():
                    sector_news[sector] = []
                    keywords = self.sector_keywords[sector]
                    
                    for _, row in industry_news.head(20).iterrows():
                        title = row.get('title', '')
                        if any(keyword in title for keyword in keywords):
                            simplified = title[:60] + "..." if len(title) > 60 else title
                            sector_news[sector].append(simplified)
        except Exception as e:
            pass
        
        return sector_news
    
    def _get_sentiment_indicators(self) -> Dict[str, Any]:
        """获取量化情绪指标"""
        indicators = {}
        
        try:
            sentiment_index = ak.stock_emotion_index()
            if not sentiment_index.empty:
                latest = sentiment_index.iloc[-1]
                indicators['market_sentiment'] = {
                    'score': latest.get('score', 'N/A'),
                    'level': latest.get('level', 'N/A')
                }
        except Exception as e:
            pass
        
        return indicators

    def _get_retail_attention(self, target_symbols: List[str]) -> Dict[str, Any]:
        """
        获取散户关注度数据 - 逆向指标核心
        target_symbols: 标的代码列表（不带后缀，如：['513120', '159995']）
        """
        attention_data = {
            'market_hottest': [],      # 全市场最热的股票
            'target_heat_rank': {}     # 关注标的的排名和状态
        }
        
        try:
            # 获取东方财富人气榜
            hot_df = ak.stock_hot_rank_em() 
            
            # 兼容性修复：检查列名是 '名称' 还是 '股票名称'
            name_col = '名称' if '名称' in hot_df.columns else '股票名称'
            
            if name_col in hot_df.columns:
                # 记录全市场前5名，用于判断市场风格
                attention_data['market_hottest'] = hot_df[[name_col, '最新价']].head(5).to_dict('records')
                
                # 检查关注标的是否在榜单上
                for target in target_symbols:
                    # 在人气榜中查找代码匹配
                    match = hot_df[hot_df['代码'] == target]
                    if not match.empty:
                        rank = match.iloc[0]['排名']
                        # 判断状态 - 逆向指标逻辑
                        status = "Overheated" if rank <= 10 else "Hot"
                        
                        attention_data['target_heat_rank'][target] = {
                            'rank': int(rank),
                            'status': status,
                            'warning': "Crowded Trade Risk" if rank <= 10 else "High Attention"
                        }
                    else:
                        # 不在榜单上，说明关注度低
                        attention_data['target_heat_rank'][target] = {
                            'rank': ">100",
                            'status': "Cold/Safe",
                            'warning': "None"
                        }
            else:
                print(f"警告：热度榜数据列名不匹配，现有列名: {hot_df.columns}")
                    
        except Exception as e:
            # 在非调试模式下可以选择pass，或者打印简要信息
            pass
            
        return attention_data

    def generate_nlp_prompt_segment(self, my_etf_list: List[Dict]) -> str:
        """
        生成专门用于NLP分析的提示词片段
        """
        # 提取代码列表用于热度扫描
        symbols = [item['symbol'].split('.')[0] for item in my_etf_list]
        sentiment_data = self.get_sentiment_data(symbols)
        
        prompt_segment = f"""
## 👂 市场舆情与情绪分析

### 📢 政策信号（政策风向标）
{self._format_list(sentiment_data.get('policy_signals', []))}

### 📡 市场传闻（实时快讯）
{self._format_list(sentiment_data.get('market_rumors', []))}

### 🔥 散户热度（逆向指标）
{self._format_retail_attention(sentiment_data.get('retail_attention', {}))}

### 📊 情绪指标
{self._format_sentiment_indicators(sentiment_data.get('sentiment_indicators', {}))}

### 🎯 行业动态
{self._format_sector_news(sentiment_data.get('sector_news', {}), my_etf_list)}
"""
        return prompt_segment

    def _format_list(self, items: List[str]) -> str:
        """格式化列表项"""
        if not items:
            return "暂无数据"
        return "\n".join([f"- {item}" for item in items])

    def _format_retail_attention(self, attention_data: Dict[str, Any]) -> str:
        """格式化散户热度数据"""
        if not attention_data:
            return "暂无散户热度数据"
        
        lines = []
        
        # 全市场最热
        hottest = attention_data.get('market_hottest', [])
        if hottest:
            lines.append("**全市场最热股票（反映当前炒作风格）:**")
            # 自动适配显示列名
            name_key = '名称' if '名称' in hottest[0] else '股票名称'
            for stock in hottest:
                lines.append(f"  - {stock.get(name_key, 'Unknown')} (最新价: {stock.get('最新价', 'N/A')})")
        
        # 关注标的的热度
        targets = attention_data.get('target_heat_rank', {})
        if targets:
            lines.append("\n**关注标的的热度排名（逆向指标）:**")
            for symbol, info in targets.items():
                warning_icon = "🚨" if info['status'] == "Overheated" else "⚠️" if info['status'] == "Hot" else "✅"
                lines.append(f"  - {symbol}: 排名 {info['rank']} ({info['status']}) {warning_icon}")
                lines.append(f"    警告: {info['warning']}")
        
        return "\n".join(lines) if lines else "无显著热度数据"

    def _format_sentiment_indicators(self, indicators: Dict[str, Any]) -> str:
        """格式化情绪指标"""
        if not indicators:
            return "暂无情绪指标数据"
        
        lines = []
        if 'market_sentiment' in indicators:
            sentiment = indicators['market_sentiment']
            lines.append(f"- 市场情绪指数: {sentiment.get('score', 'N/A')} ({sentiment.get('level', 'N/A')})")
        
        return "\n".join(lines)

    def _format_sector_news(self, sector_news: Dict[str, List[str]], etf_list: List[Dict]) -> str:
        """格式化行业新闻"""
        lines = []
        for etf in etf_list:
            sector = etf.get('sector')
            if sector in sector_news and sector_news[sector]:
                lines.append(f"**{etf['name']}相关新闻:**")
                for news in sector_news[sector][:2]:  # 每个ETF最多2条新闻
                    lines.append(f"  - {news}")
        return "\n".join(lines) if lines else "暂无显著的行业特定新闻"