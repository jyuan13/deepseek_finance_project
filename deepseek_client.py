# deepseek_finance_project_V3/deepseek_client.py

import os
import json
from openai import OpenAI
from datetime import datetime
import glob

class DeepSeekClient:
    def __init__(self, api_key=None, base_url=None, provider="qwen", conversation_dir="conversations", max_history_rounds=10):
        """
        初始化多模态客户端 (支持 DeepSeek 和 Qwen)
        :param api_key: API Key
        :param base_url: 自定义 Base URL
        :param provider: "deepseek" 或 "qwen"
        :param conversation_dir: 对话保存目录
        :param max_history_rounds: [V3.9] 仅保留最近 N 轮对话，防止 Token 爆炸
        """
        self.provider = provider.lower()
        self.conversation_dir = conversation_dir
        self.current_conversation_file = None
        self.conversation_history = []
        self.max_history_rounds = max_history_rounds
        
        # --- 供应商配置初始化 ---
        if self.provider == "qwen":
            # 优先读取 Qwen_API_KEY，其次尝试 DASHSCOPE_API_KEY
            self.api_key = api_key or os.environ.get("Qwen_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
            self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.models = {
                "chat": "qwen-plus",
                "reasoner": "qwen-plus",  # Qwen-plus 配合 enable_thinking=True
                "latest": "qwen-max"
            }
            print(f"🔧 初始化 Qwen 客户端 (Model: {self.models['chat']})")
            
        else: # 默认为 deepseek
            self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
            self.base_url = base_url or "https://api.deepseek.com"
            self.models = {
                "chat": "deepseek-chat",
                "reasoner": "deepseek-reasoner",
                "latest": "deepseek-chat"
            }
            print(f"🔧 初始化 DeepSeek 客户端 (Model: {self.models['chat']})")

        if not self.api_key:
            env_var_name = 'Qwen_API_KEY' if self.provider == 'qwen' else 'DEEPSEEK_API_KEY'
            raise ValueError(f"❌ 未找到 {self.provider} 的API密钥！请设置环境变量 {env_var_name} 或在初始化时传入")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
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
        """清空所有对话文件"""
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
        """
        [V3.9] 添加消息到历史记录，并执行滑动窗口裁剪
        """
        self.conversation_history.append({"role": role, "content": content})
        
        # 记忆防爆：只保留最近 N 轮 (2*N 条消息)
        if len(self.conversation_history) > self.max_history_rounds * 2:
            self.conversation_history = self.conversation_history[-(self.max_history_rounds * 2):]
            
        self.save_conversation()
    
    def clear_history(self):
        """
        [V3.9] 清空当前内存中的对话历史 (用于任务隔离)
        """
        self.conversation_history = []
        if self.current_conversation_file:
            # 选择性保存，或者不保存空状态，视需求而定
            # 这里我们只重置内存，不覆盖文件，防止误删长期记忆
            pass
        # print("✓ 当前对话上下文已重置")
    
    def chat(self, message, model_type="chat", system_prompt="You are a helpful assistant", use_history=True, show_reasoning=False):
        """
        与模型进行对话 (自动适配 Qwen/DeepSeek)
        :param show_reasoning: 是否在控制台打印思考过程 (默认为 False，只打印结果)
        """
        if model_type not in self.models:
            print(f"⚠ 模型类型 {model_type} 未找到，回退到 chat 模式")
            model_type = "chat"
        
        model = self.models[model_type]
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # [V3.9] 仅当启用且有历史时添加
        if use_history and self.conversation_history:
            messages.extend(self.conversation_history)
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": message})
        
        # --- Qwen 特有配置: 开启思考模式 ---
        extra_body = {}
        # 如果是 Qwen 且 (显式请求 reasoner 或 使用的是 qwen-plus/max)
        if self.provider == "qwen" and (model_type == "reasoner" or "plus" in model or "max" in model):
            # 强制开启 Qwen 的思考能力
            extra_body["enable_thinking"] = True
            if show_reasoning:
                print("🧠 Qwen 深度思考模式已激活...")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                extra_body=extra_body if extra_body else None
            )
            
            result = self._handle_stream_response(response, model_type, show_reasoning)
            
            # 保存到历史记录
            if use_history:
                self.add_to_history("user", message)
                # 注意：这里我们只保存最终回复内容到历史，思考过程通常不作为对话历史上下文
                self.add_to_history("assistant", result["content"])
            
            return result
                
        except Exception as e:
            return {
                "content": f"API调用错误: {str(e)}",
                "reasoning": "",
                "usage": None,
                "cost": 0.0
            }
    
    def _handle_stream_response(self, response, model_type, show_reasoning):
        """处理流式响应 (支持 Qwen 的 reasoning_content)"""
        full_response = ""
        full_reasoning = ""
        is_answering = False
        usage_info = None
        
        print(f"\n[{self.provider.upper()}] 回复: ", end="", flush=True)
        
        # 打印思考过程分隔线 (针对 Qwen)，仅当 show_reasoning 为 True 时显示
        if self.provider == "qwen" and show_reasoning:
            print("\n" + "="*15 + " 思考过程 " + "="*15 + "\n", end="", flush=True)

        for chunk in response:
            # 1. 捕获 Usage 信息 (Qwen通常在最后返回，或者通过 stream_options 获取)
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
                # Qwen 有时会在最后一个chunk返回usage，但不一定带choices
                if not chunk.choices:
                    continue
            
            if not chunk.choices:
                continue
                
            delta = chunk.choices[0].delta
            
            # 2. 处理思考内容 (Qwen 特有字段 reasoning_content)
            # 兼容不同 SDK 版本，有的在 delta 属性里，有的可能需要 getattr
            reasoning = getattr(delta, 'reasoning_content', None)
            
            if reasoning:
                if show_reasoning:
                    print(reasoning, end="", flush=True)
                full_reasoning += reasoning
            
            # 3. 处理正式回复内容
            if hasattr(delta, 'content') and delta.content:
                # 如果从思考转为回复，打印分隔线 (仅当显示了思考过程时)
                if full_reasoning and not is_answering and show_reasoning:
                    print("\n\n" + "="*15 + " 完整回复 " + "="*15 + "\n", end="", flush=True)
                    is_answering = True
                elif not full_reasoning and not is_answering and self.provider == "qwen" and show_reasoning: 
                    # 针对 Qwen，如果一开始就是 content (没有思考) 且要求显示推理状态，也标记一下
                    print("\n\n" + "="*15 + " 完整回复 " + "="*15 + "\n", end="", flush=True)
                    is_answering = True
                
                print(delta.content, end="", flush=True)
                full_response += delta.content
        
        print("\n")  # 结束换行
        
        # 计算费用 (粗略估算)
        cost = 0.0
        if usage_info:
            input_tokens = usage_info.prompt_tokens
            output_tokens = usage_info.completion_tokens
            # 这里仅做简单示例，实际费率需根据模型调整
            cost = (input_tokens * 0.004 + output_tokens * 0.012) / 1000 
        
        return {
            "content": full_response,
            "reasoning": full_reasoning,
            "usage": usage_info,
            "cost": cost
        }
    
    def interactive_chat(self, model_type="chat", system_prompt="You are a helpful assistant that responds in Chinese"):
        """交互式聊天模式（支持连续对话）"""
        # 确保有当前对话文件
        if not self.current_conversation_file and self.conversation_dir:
            self.start_new_conversation()
        
        print(f"=== {self.provider.upper()} API 交互模式 ===")
        print(f"模型: {self.models.get(model_type, model_type)}")
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
                
                # 默认交互模式也不显示思考过程，保持界面整洁
                result = self.chat(user_input, model_type, system_prompt, show_reasoning=False)
                
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