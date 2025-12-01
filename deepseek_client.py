# deepseek_finance_project_V2/deepseek_client.py

import os
import json
from openai import OpenAI
from datetime import datetime
import glob

class DeepSeekClient:
    def __init__(self, api_key=None, base_url="https://api.deepseek.com", conversation_dir="conversations"):
        """
        初始化DeepSeek客户端
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("未提供API密钥，请设置DEEPSEEK_API_KEY环境变量或在初始化时传入api_key参数")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url
        )
        
        # 可用模型配置
        self.models = {
            "chat": "deepseek-chat",
            "reasoner": "deepseek-reasoner",
            "latest": "deepseek-chat"
        }
        
        # 对话历史
        self.conversation_history = []
        self.conversation_dir = conversation_dir
        self.current_conversation_file = None
        
        # 创建对话目录
        if conversation_dir and not os.path.exists(conversation_dir):
            os.makedirs(conversation_dir)
            print(f"✓ 已创建对话目录: {conversation_dir}")
    
    def _get_next_conversation_filename(self):
        """生成下一个对话文件名"""
        today = datetime.now().strftime("%Y%m%d")
        
        # 查找今天已有的对话文件
        pattern = os.path.join(self.conversation_dir, f"Chat_{today}_*.json")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            # 今天还没有对话文件
            next_number = "01"
        else:
            # 提取现有文件的编号并找到最大的
            numbers = []
            for file_path in existing_files:
                filename = os.path.basename(file_path)
                # 从文件名中提取编号
                try:
                    number_part = filename.split('_')[2].split('.')[0]
                    numbers.append(int(number_part))
                except (IndexError, ValueError):
                    continue
            
            if numbers:
                max_number = max(numbers)
                next_number = str(max_number + 1).zfill(2)
            else:
                next_number = "01"
        
        filename = f"Chat_{today}_{next_number}.json"
        return os.path.join(self.conversation_dir, filename)
    
    def start_new_conversation(self):
        """开始新的对话会话"""
        if not self.conversation_dir:
            print("⚠ 未设置对话目录，无法创建新对话文件")
            return False
        
        self.current_conversation_file = self._get_next_conversation_filename()
        self.conversation_history = []
        print(f"✓ 已创建新对话文件: {os.path.basename(self.current_conversation_file)}")
        return True
    
    def load_conversation(self, file_path=None):
        """从文件加载对话历史"""
        if not file_path and not self.current_conversation_file:
            print("⚠ 未指定要加载的对话文件")
            return False
        
        target_file = file_path or self.current_conversation_file
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                self.conversation_history = json.load(f)
            self.current_conversation_file = target_file
            print(f"✓ 已加载对话历史: {os.path.basename(target_file)}，共{len(self.conversation_history)}条消息")
            return True
        except Exception as e:
            print(f"⚠ 加载对话历史失败: {e}")
            return False
    
    def save_conversation(self):
        """保存对话历史到文件"""
        if not self.current_conversation_file:
            # 如果没有当前对话文件，创建一个新的
            if not self.start_new_conversation():
                return False
        
        try:
            with open(self.current_conversation_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"⚠ 保存对话历史失败: {e}")
            return False
            
    def clear_all_conversations(self):
        """[新增] 清空所有对话文件"""
        if not self.conversation_dir or not os.path.exists(self.conversation_dir):
            return True
        
        try:
            files = glob.glob(os.path.join(self.conversation_dir, "Chat_*.json"))
            if not files:
                print("⚠️  没有可清除的对话记录")
                return True
                
            for f in files:
                os.remove(f)
            
            self.conversation_history = []
            self.current_conversation_file = None
            print(f"✅ 已清除 {len(files)} 个历史对话文件")
            return True
        except Exception as e:
            print(f"❌ 对话文件清除失败: {e}")
            return False
    
    def list_conversations(self):
        """列出所有可用的对话文件"""
        if not self.conversation_dir or not os.path.exists(self.conversation_dir):
            print("对话目录不存在或为空")
            return []
        
        conversation_files = []
        for file_path in glob.glob(os.path.join(self.conversation_dir, "Chat_*.json")):
            filename = os.path.basename(file_path)
            # 解析文件名获取日期和编号
            try:
                parts = filename.split('_')
                date_str = parts[1]
                number_str = parts[2].split('.')[0]
                
                # 格式化日期显示
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                formatted_date = date_obj.strftime("%Y年%m月%d日")
                
                conversation_files.append({
                    'filename': filename,
                    'filepath': file_path,
                    'date': formatted_date,
                    'number': number_str,
                    'full_date': date_str
                })
            except (IndexError, ValueError):
                # 如果文件名格式不正确，跳过
                continue
        
        # 按日期和编号排序
        conversation_files.sort(key=lambda x: (x['full_date'], x['number']), reverse=True)
        return conversation_files
    
    def add_to_history(self, role, content):
        """添加消息到历史记录"""
        self.conversation_history.append({"role": role, "content": content})
        self.save_conversation()
    
    def clear_history(self):
        """清空当前对话历史"""
        self.conversation_history = []
        if self.current_conversation_file:
            self.save_conversation()
        print("✓ 当前对话历史已清空")
    
    def chat(self, message, model_type="chat", system_prompt="You are a helpful assistant", use_history=True):
        """与DeepSeek进行对话"""
        if model_type not in self.models:
            raise ValueError(f"不支持的模型类型: {model_type}，可选: {list(self.models.keys())}")
        
        model = self.models[model_type]
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史记录（如果启用）
        if use_history:
            messages.extend(self.conversation_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            
            result = self._handle_stream_response(response, model_type)
            
            # 保存到历史记录
            if use_history:
                self.add_to_history("user", message)
                self.add_to_history("assistant", result["content"])
            
            return result
                
        except Exception as e:
            return {
                "content": f"API调用错误: {str(e)}",
                "usage": None,
                "cost": 0.0
            }
    
    def _handle_stream_response(self, response, model_type):
        """处理流式响应并收集使用统计"""
        full_response = ""
        print("DeepSeek回复: ", end="", flush=True)
        
        usage_info = None
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
            
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
        
        print()  # 换行
        
        # 计算费用
        cost = 0.0
        if usage_info:
            input_tokens = usage_info.prompt_tokens
            output_tokens = usage_info.completion_tokens
            
            if model_type == "chat":
                cost = (input_tokens * 0.14 + output_tokens * 0.28) / 1_000_000
            else:  # reasoner
                cost = (input_tokens * 0.56 + output_tokens * 1.12) / 1_000_000
        
        return {
            "content": full_response,
            "usage": usage_info,
            "cost": cost
        }
    
    def interactive_chat(self, model_type="chat", system_prompt="You are a helpful assistant that responds in Chinese"):
        """交互式聊天模式（支持连续对话）"""
        # 确保有当前对话文件
        if not self.current_conversation_file and self.conversation_dir:
            self.start_new_conversation()
        
        print(f"=== DeepSeek API 交互模式 ===")
        print(f"模型: {model_type}")
        if self.current_conversation_file:
            print(f"当前对话文件: {os.path.basename(self.current_conversation_file)}")
        print(f"对话历史: {len(self.conversation_history)} 条消息")
        print(f"命令: 'quit'退出, 'clear'清空历史, 'history'查看历史, 'new'新对话, 'list'列出所有对话")
        print("=" * 40)
        
        while True:
            try:
                user_input = input("\n你: ").strip()
                
                if user_input.lower() in ['quit', '退出', 'exit']:
                    print("对话结束，再见！")
                    break
                elif user_input.lower() == 'clear':
                    self.clear_history()
                    continue
                elif user_input.lower() == 'history':
                    self.show_history()
                    continue
                elif user_input.lower() == 'new':
                    self.start_new_conversation()
                    continue
                elif user_input.lower() == 'list':
                    self.show_conversation_list()
                    continue
                
                if not user_input:
                    print("请输入有效内容")
                    continue
                
                result = self.chat(user_input, model_type, system_prompt)
                
                # 显示使用统计
                if result["usage"]:
                    usage = result["usage"]
                    print(f"\n[使用统计] 输入Token: {usage.prompt_tokens}, 输出Token: {usage.completion_tokens}, 总计: {usage.total_tokens}")
                    print(f"[费用估算] ￥{result['cost']:.6f}")
                
            except KeyboardInterrupt:
                print("\n\n对话被用户中断，再见！")
                break
            except Exception as e:
                print(f"\n发生错误: {str(e)}")
    
    def show_history(self):
        """显示当前对话历史"""
        if not self.conversation_history:
            print("当前对话历史为空")
            return
        
        print(f"\n=== 对话历史 ({os.path.basename(self.current_conversation_file) if self.current_conversation_file else '未保存'}) ===")
        for i, msg in enumerate(self.conversation_history, 1):
            role = "用户" if msg["role"] == "user" else "助手"
            # 截断长消息以便显示
            content = msg["content"]
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"{i}. {role}: {content}")
        print("=" * 40)
    
    def show_conversation_list(self):
        """显示所有对话文件列表"""
        conversations = self.list_conversations()
        if not conversations:
            print("没有找到对话文件")
            return
        
        print(f"\n=== 所有对话文件 ({len(conversations)}个) ===")
        for i, conv in enumerate(conversations, 1):
            current_indicator = " ✓" if self.current_conversation_file and os.path.basename(self.current_conversation_file) == conv['filename'] else ""
            print(f"{i}. {conv['filename']} ({conv['date']} 第{conv['number']}次对话){current_indicator}")
        print("=" * 40)
        
        # 提供加载选项
        try:
            choice = input("输入编号加载对话 (直接回车返回): ").strip()
            if choice:
                index = int(choice) - 1
                if 0 <= index < len(conversations):
                    self.load_conversation(conversations[index]['filepath'])
                else:
                    print("无效的编号")
        except ValueError:
            print("请输入有效数字")