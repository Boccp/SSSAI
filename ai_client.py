import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import requests
import os
import time
import threading
import pickle
from typing import Dict, Any, List

class AIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.siliconflow.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.messages: List[Dict[str, str]] = []
        # 根据API文档添加完整参数列表
        self.parameters = {
            "model": "deepseek-ai/DeepSeek-V2.5",
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "stop": None,
            "system_prompt": ""  # 增加系统提示词
        }
        # 禁用代理设置
        self.proxies = {
            "http": None,
            "https": None
        }
        self.debug_mode = False
        self.max_retries = 3
        
    def save_state(self, filename="ai_client_state.pkl"):
        """保存客户端状态，包括参数和消息历史"""
        state = {
            "parameters": self.parameters,
            "messages": self.messages
        }
        try:
            with open(filename, 'wb') as f:
                pickle.dump(state, f)
            return True
        except Exception as e:
            print(f"保存状态失败: {e}")
            return False
            
    def load_state(self, filename="ai_client_state.pkl"):
        """加载客户端状态"""
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    state = pickle.load(f)
                self.parameters = state.get("parameters", self.parameters)
                self.messages = state.get("messages", [])
                return True
            return False
        except Exception as e:
            print(f"加载状态失败: {e}")
            return False

    def make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        
        # 调试模式 - 模拟响应
        if self.debug_mode:
            time.sleep(1)  # 模拟网络延迟
            return {
                "id": "debug-response",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "这是一个调试模式的模拟回复。实际使用时请关闭调试模式。"
                        },
                        "finish_reason": "stop"
                    }
                ]
            }
        
        # 打印请求数据，用于调试
        print("请求URL:", url)
        print("请求头:", self.headers)
        print("请求数据:", json.dumps(data, ensure_ascii=False, indent=2))
        
        # 实际API请求
        retries = 0
        while retries <= self.max_retries:
            try:
                # 使用无代理设置发送请求
                response = requests.post(url, headers=self.headers, json=data, proxies=self.proxies, timeout=15)
                
                # 打印响应状态和内容，用于调试
                print("响应状态码:", response.status_code)
                try:
                    print("响应内容:", json.dumps(response.json(), ensure_ascii=False, indent=2))
                except:
                    print("响应内容:", response.text)
                
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                print(f"HTTP错误: {e}")
                # 尝试获取详细的错误信息
                try:
                    error_detail = response.json()
                    return {"error": f"HTTP错误 {response.status_code}: {error_detail.get('error', {}).get('message', str(e))}"}
                except:
                    return {"error": f"HTTP错误 {response.status_code}: {str(e)}"}
            except requests.exceptions.ProxyError as e:
                return {"error": f"代理错误: {str(e)}. 请检查您的网络设置或禁用代理。"}
            except requests.exceptions.ConnectionError as e:
                if retries < self.max_retries:
                    retries += 1
                    wait_time = 2 ** retries  # 指数退避
                    time.sleep(wait_time)
                    continue
                return {"error": f"连接错误: {str(e)}. 请检查您的网络连接。"}
            except requests.exceptions.Timeout as e:
                if retries < self.max_retries:
                    retries += 1
                    wait_time = 2 ** retries
                    time.sleep(wait_time)
                    continue
                return {"error": f"请求超时: {str(e)}. 服务器没有及时响应。"}
            except requests.exceptions.RequestException as e:
                return {"error": f"请求错误: {str(e)}"}

    def test_connection(self) -> Dict[str, Any]:
        """测试API连接"""
        if self.debug_mode:
            return {"success": True, "message": "调试模式，连接测试跳过"}
            
        try:
            # 简单的消息请求，仅用于测试连接
            test_data = {
                "model": self.parameters["model"],
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5,
                "stream": False
            }
            
            # 使用更短的超时时间
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=self.headers, 
                json=test_data, 
                proxies=self.proxies, 
                timeout=5
            )
            
            print("测试连接响应码:", response.status_code)
            try:
                print("测试连接响应:", json.dumps(response.json(), ensure_ascii=False, indent=2))
            except:
                print("测试连接响应:", response.text)
            
            if response.status_code >= 200 and response.status_code < 300:
                return {"success": True, "message": f"连接成功! 状态码: {response.status_code}"}
            else:
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("error", {}).get("message", str(response.text))
                    return {"success": False, "message": f"API错误: {error_msg} (状态码: {response.status_code})"}
                except:
                    return {"success": False, "message": f"API错误: 状态码 {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"连接错误: {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"未知错误: {str(e)}"}

class SettingsWindow:
    def __init__(self, parent, callback, debug_callback, test_callback=None):
        self.window = tk.Toplevel(parent)
        self.window.title("设置")
        self.window.geometry("400x320")
        self.window.transient(parent)
        self.window.grab_set()
        
        # 创建主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # API密钥输入
        ttk.Label(main_frame, text="API密钥:").pack(anchor=tk.W)
        self.api_key_entry = ttk.Entry(main_frame, width=50, show="*")
        self.api_key_entry.pack(fill=tk.X, pady=5)
        
        # API端点输入
        ttk.Label(main_frame, text="API端点 (默认: https://api.siliconflow.cn/v1):").pack(anchor=tk.W)
        self.api_endpoint_entry = ttk.Entry(main_frame, width=50)
        self.api_endpoint_entry.insert(0, "https://api.siliconflow.cn/v1")
        self.api_endpoint_entry.pack(fill=tk.X, pady=5)
        
        # 调试模式复选框
        self.debug_var = tk.BooleanVar()
        self.debug_checkbox = ttk.Checkbutton(
            main_frame, 
            text="启用调试模式（不发送实际请求）", 
            variable=self.debug_var
        )
        self.debug_checkbox.pack(anchor=tk.W, pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20, fill=tk.X)
        
        # 测试连接按钮
        self.test_callback = test_callback
        if test_callback:
            self.test_button = ttk.Button(
                button_frame,
                text="测试连接",
                command=self.test_connection
            )
            self.test_button.pack(side=tk.LEFT, padx=5)
        
        # 保存按钮
        ttk.Button(
            button_frame, 
            text="保存", 
            command=self.save_settings
        ).pack(side=tk.RIGHT, padx=5)
        
        self.callback = callback
        self.debug_callback = debug_callback
        
    def test_connection(self):
        """测试API连接"""
        if not self.test_callback:
            return
            
        api_key = self.api_key_entry.get().strip()
        api_endpoint = self.api_endpoint_entry.get().strip()
        debug_mode = self.debug_var.get()
        
        if not api_key and not debug_mode:
            messagebox.showerror("错误", "请填写API密钥或启用调试模式")
            return
            
        # 如果端点留空，使用默认值
        if not api_endpoint:
            api_endpoint = "https://api.siliconflow.cn/v1"
            
        # 执行连接测试
        result = self.test_callback(api_key, api_endpoint, debug_mode)
        
        # 显示结果
        if result["success"]:
            messagebox.showinfo("测试结果", result["message"])
        else:
            messagebox.showerror("测试结果", result["message"])
        
    def save_settings(self):
        api_key = self.api_key_entry.get().strip()
        api_endpoint = self.api_endpoint_entry.get().strip()
        debug_mode = self.debug_var.get()
        
        if not api_key and not debug_mode:
            messagebox.showerror("错误", "请填写API密钥或启用调试模式")
            return
        
        # 如果端点留空，使用默认值
        if not api_endpoint:
            api_endpoint = "https://api.siliconflow.cn/v1"
            
        self.callback(api_key, api_endpoint)
        self.debug_callback(debug_mode)
        self.window.destroy()

class ParameterFrame(ttk.Frame):
    def __init__(self, parent, parameters, callback):
        super().__init__(parent)
        self.parameters = parameters
        self.callback = callback
        self.create_widgets()
        
    def create_widgets(self):
        # 可用的模型列表 - 根据文档更新
        model_options = [
            "Qwen/QwQ-32B", 
            "Pro/deepseek-ai/DeepSeek-R1", 
            "Pro/deepseek-ai/DeepSeek-V3", 
            "deepseek-ai/DeepSeek-R1", 
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
            "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
            "deepseek-ai/DeepSeek-V2.5",
            "Qwen/Qwen2.5-72B-Instruct-128K",
            "Qwen/Qwen2.5-72B-Instruct",
            "Qwen/Qwen2.5-32B-Instruct",
            "Qwen/Qwen2.5-14B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-Coder-32B-Instruct",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "Qwen/Qwen2-7B-Instruct",
            "Qwen/Qwen2-1.5B-Instruct"
        ]
        
        # 创建选项卡
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建基本参数选项卡
        basic_tab = ttk.Frame(self.notebook)
        self.notebook.add(basic_tab, text="基本参数")
        
        # 创建高级参数选项卡
        advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(advanced_tab, text="高级参数")
        
        # 创建系统提示词选项卡
        prompt_tab = ttk.Frame(self.notebook)
        self.notebook.add(prompt_tab, text="系统提示词")
        
        # 基本参数
        row = 0
        basic_params = ["model", "max_tokens", "temperature"]
        for param in basic_params:
            value = self.parameters[param]
            ttk.Label(basic_tab, text=f"{param}:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            # 如果是model参数，创建下拉菜单
            if param == "model":
                combo = ttk.Combobox(basic_tab, values=model_options, width=15)
                combo.set(value)
                combo.grid(row=row, column=1, padx=5, pady=2)
                combo.bind('<<ComboboxSelected>>', lambda e, p=param, cb=combo: self.update_parameter(p, cb.get()))
            # 数字类型参数
            elif isinstance(value, (int, float)):
                entry = ttk.Entry(basic_tab, width=10)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=5, pady=2)
                entry.bind('<KeyRelease>', lambda e, p=param, ent=entry: self.update_parameter(p, ent.get()))
            row += 1
        
        # 添加重置默认值按钮
        reset_button = ttk.Button(
            basic_tab, 
            text="重置默认值", 
            command=self.reset_defaults
        )
        reset_button.grid(row=row, column=0, columnspan=2, pady=10)
            
        # 高级参数
        row = 0
        advanced_params = ["top_p", "top_k", "frequency_penalty", "n", "stop"]
        for param in advanced_params:
            value = self.parameters[param]
            ttk.Label(advanced_tab, text=f"{param}:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
            
            # 对于None值的特殊处理
            if value is None:
                entry = ttk.Entry(advanced_tab, width=10)
                entry.insert(0, "")
                entry.grid(row=row, column=1, padx=5, pady=2)
                entry.bind('<KeyRelease>', lambda e, p=param, ent=entry: self.update_parameter(p, ent.get() or None))
            # 数字类型参数
            elif isinstance(value, (int, float)):
                entry = ttk.Entry(advanced_tab, width=10)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=5, pady=2)
                entry.bind('<KeyRelease>', lambda e, p=param, ent=entry: self.update_parameter(p, ent.get()))
            # 其他类型
            else:
                entry = ttk.Entry(advanced_tab, width=10)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, padx=5, pady=2)
                entry.bind('<KeyRelease>', lambda e, p=param, ent=entry: self.update_parameter(p, ent.get()))
            row += 1
        
        # 系统提示词文本区域
        ttk.Label(prompt_tab, text="系统提示词:").pack(anchor=tk.W, padx=5, pady=2)
        
        self.prompt_text = scrolledtext.ScrolledText(
            prompt_tab,
            wrap=tk.WORD,
            width=30,
            height=10
        )
        self.prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.prompt_text.insert(tk.END, self.parameters.get("system_prompt", ""))
        self.prompt_text.bind("<KeyRelease>", self.update_system_prompt)
        
        # 示例提示词按钮
        example_button = ttk.Button(
            prompt_tab, 
            text="插入示例提示词", 
            command=self.insert_example_prompt
        )
        example_button.pack(anchor=tk.W, padx=5, pady=5)
        
    def insert_example_prompt(self):
        """插入示例系统提示词"""
        example = "你是一个有用的AI助手。回答用户的问题时应该简洁明了，提供有价值的信息。"
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(tk.END, example)
        self.update_system_prompt(None)  # 更新参数
    
    def update_system_prompt(self, event):
        """更新系统提示词参数"""
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        self.parameters["system_prompt"] = prompt
        self.callback(self.parameters)
            
    def update_parameter(self, param: str, value: str):
        """更新参数值"""
        try:
            if param in ["max_tokens", "n"]:
                self.parameters[param] = int(value) if value else 0
            elif param in ["temperature", "top_p", "top_k", "frequency_penalty"]:
                self.parameters[param] = float(value) if value else 0.0
            elif param == "stop" and not value:
                self.parameters[param] = None
            else:
                self.parameters[param] = value
            self.callback(self.parameters)
        except ValueError:
            pass
            
    def reset_defaults(self):
        """重置为默认参数"""
        default_params = {
            "model": "deepseek-ai/DeepSeek-V2.5",
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1,
            "stop": None,
            "system_prompt": ""
        }
        
        # 保留原模型设置
        current_model = self.parameters.get("model", default_params["model"])
        default_params["model"] = current_model
        
        # 更新参数
        self.parameters.update(default_params)
        
        # 刷新界面
        self.notebook.destroy()
        self.create_widgets()
        
        # 回调更新
        self.callback(self.parameters)

class ChatWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 聊天助手")
        self.root.geometry("980x980")
        
        # 设置窗口样式
        self.root.configure(bg='#f0f0f0')
        
        # 创建主布局框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左侧参数框架
        self.param_frame = ttk.LabelFrame(self.main_frame, text="参数设置", padding="5")
        self.param_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # 创建右侧主框架
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建顶部设置按钮
        self.top_frame = ttk.Frame(self.right_frame)
        self.top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 添加一个空行
        ttk.Label(self.top_frame, text="").pack()
        
        # 创建按钮框架
        button_frame = ttk.Frame(self.top_frame)
        button_frame.pack(pady=5)
        
        # 设置按钮
        self.settings_button = ttk.Button(
            button_frame,
            text="设置API",
            command=self.show_settings,
            style='Accent.TButton'
        )
        self.settings_button.pack(side=tk.LEFT, padx=5)
        
        # 添加重启按钮
        self.restart_button = ttk.Button(
            button_frame,
            text="重启程序",
            command=self.restart_app,
            style='Accent.TButton'
        )
        self.restart_button.pack(side=tk.LEFT, padx=5)
        
        # 添加保存聊天记录按钮
        self.save_chat_button = ttk.Button(
            button_frame,
            text="保存聊天",
            command=self.save_chat_history,
            style='Accent.TButton'
        )
        self.save_chat_button.pack(side=tk.LEFT, padx=5)
        
        # 创建聊天显示区域
        self.chat_frame = ttk.Frame(self.right_frame)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            font=('微软雅黑', 10),
            bg='white'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # 创建输入区域
        self.input_frame = ttk.Frame(self.right_frame)
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.message_input = ttk.Entry(
            self.input_frame,
            font=('微软雅黑', 10)
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.send_button = ttk.Button(
            self.input_frame,
            text="发送",
            command=self.send_message
        )
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        # 清空聊天记录按钮
        self.clear_button = ttk.Button(
            self.input_frame,
            text="清空",
            command=self.clear_chat
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # 添加状态标签
        self.status_label = ttk.Label(
            self.right_frame,
            text="就绪",
            font=('微软雅黑', 9)
        )
        self.status_label.pack(anchor=tk.W, padx=10, pady=2)
        
        # 绑定回车键发送消息
        self.message_input.bind('<Return>', lambda e: self.send_message())
        
        # 初始化变量
        self.client = None
        self.api_key = None
        
        # 尝试加载保存的API密钥
        self.load_api_key()
        
        # 在程序关闭时保存状态
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 添加欢迎消息
        self.add_message("系统", "欢迎使用AI聊天助手！请先设置API密钥。", "system")
    
    def load_api_key(self):
        """尝试加载保存的API密钥和配置"""
        try:
            if os.path.exists("api_key.txt"):
                with open("api_key.txt", "r") as f:
                    api_key = f.read().strip()
                    if api_key:
                        self.api_key = api_key
                        self.client = AIClient(api_key)
                        # 加载保存的状态
                        self.client.load_state()
                        # 显示加载的消息历史
                        self.load_chat_history()
                        # 创建参数设置框架
                        self.parameter_frame = ParameterFrame(
                            self.param_frame,
                            self.client.parameters,
                            self.update_parameters
                        )
                        self.parameter_frame.pack(fill=tk.X, padx=5, pady=5)
                        self.add_message("系统", "已加载保存的API设置和聊天记录！", "system")
        except Exception as e:
            print(f"加载API密钥失败: {e}")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        try:
            # 保存API密钥
            if self.api_key:
                with open("api_key.txt", "w") as f:
                    f.write(self.api_key)
            
            # 保存客户端状态
            if self.client:
                self.client.save_state()
        except Exception as e:
            print(f"保存状态失败: {e}")
        
        # 关闭窗口
        self.root.destroy()
        
    def load_chat_history(self):
        """加载历史聊天记录到界面"""
        if not self.client or not self.client.messages:
            return
            
        # 清空当前显示
        self.chat_display.delete(1.0, tk.END)
        
        # 显示所有消息
        for msg in self.client.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                self.add_message("您", content, "user")
            elif role == "assistant":
                self.add_message("AI", content, "ai")
            elif role == "system":
                self.add_message("系统提示", content, "system")
    
    def save_chat_history(self):
        """保存聊天记录"""
        if not self.client:
            messagebox.showinfo("提示", "没有聊天记录可保存")
            return
            
        try:
            # 保存到文件
            filename = f"聊天记录_{time.strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for msg in self.client.messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    
                    role_text = "您" if role == "user" else "AI" if role == "assistant" else "系统"
                    f.write(f"{role_text}:\n{content}\n\n")
            
            messagebox.showinfo("成功", f"聊天记录已保存到 {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存聊天记录失败: {e}")
            
    def show_settings(self):
        SettingsWindow(self.root, self.update_settings, self.update_debug_mode, self.test_connection)
        
    def update_settings(self, api_key: str, api_endpoint: str):
        is_new_client = self.client is None
        
        self.api_key = api_key
        if is_new_client:
            self.client = AIClient(api_key)
            self.client.base_url = api_endpoint
        else:
            self.client.api_key = api_key
            self.client.base_url = api_endpoint
            self.client.headers["Authorization"] = f"Bearer {api_key}"
            
        # 如果是新客户端，尝试加载保存的状态
        if is_new_client:
            self.client.load_state()
            
        # 创建或更新参数设置框架
        if hasattr(self, 'parameter_frame'):
            self.parameter_frame.destroy()
            
        self.parameter_frame = ParameterFrame(
            self.param_frame,
            self.client.parameters,
            self.update_parameters
        )
        self.parameter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 显示加载的消息历史
        if is_new_client and self.client.messages:
            self.load_chat_history()
        else:
            self.add_message("系统", "API设置已更新，现在可以开始对话了！", "system")
    
    def update_debug_mode(self, debug_mode: bool):
        if self.client:
            self.client.debug_mode = debug_mode
            if debug_mode:
                self.add_message("系统", "已启用调试模式，不会发送实际API请求。", "system")
                self.status_label.config(text="调试模式")
            else:
                self.status_label.config(text="就绪")
        
    def update_parameters(self, parameters: Dict[str, Any]):
        if self.client:
            self.client.parameters = parameters
            
    def clear_chat(self):
        """清空聊天记录"""
        if not self.client:
            return
            
        if messagebox.askyesno("确认", "确定要清空聊天记录吗？"):
            # 保留系统提示词
            system_prompt = None
            for msg in self.client.messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content")
                    break
                    
            # 清空消息历史
            self.client.messages = []
            
            # 如果有系统提示词，重新添加
            if system_prompt:
                self.client.messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 清空聊天显示
            self.chat_display.delete(1.0, tk.END)
            
            # 保存状态
            self.client.save_state()
            
            self.add_message("系统", "聊天记录已清空。", "system")
    
    def send_message_thread(self, message):
        try:
            # 如果有系统提示词且是第一条消息，加入系统提示词
            if self.client.parameters["system_prompt"] and not self.client.messages:
                self.client.messages.append({
                    "role": "system",
                    "content": self.client.parameters["system_prompt"]
                })
            
            # 添加用户消息到历史记录
            self.client.messages.append({
                "role": "user",
                "content": message
            })
            
            # 按照API文档构建请求数据
            request_data = {
                "model": self.client.parameters["model"],
                "messages": self.client.messages,
                "temperature": self.client.parameters["temperature"],
                "max_tokens": self.client.parameters["max_tokens"],
                "stream": False,
                "top_p": self.client.parameters["top_p"],
                "top_k": self.client.parameters["top_k"],
                "frequency_penalty": self.client.parameters["frequency_penalty"],
                "n": self.client.parameters["n"]
            }
            
            # 添加可选参数
            if self.client.parameters["stop"] is not None:
                request_data["stop"] = self.client.parameters["stop"]
            
            # 更新UI状态
            self.root.after(0, lambda: self.status_label.config(text="正在请求中..."))
            
            # 发送请求
            response = self.client.make_request("chat/completions", request_data)
            
            # 保存当前状态
            self.client.save_state()
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self.handle_response(response))
        except Exception as e:
            # 捕获所有异常并在UI中显示
            error_msg = f"发送请求时出错: {str(e)}"
            print(error_msg)
            self.root.after(0, lambda: self.show_thread_error(error_msg))
            
    def handle_response(self, response):
        # 删除"发送中"消息
        self.chat_display.delete("end-3l", "end-1l")
        
        # 恢复状态
        self.status_label.config(text="就绪" if not self.client.debug_mode else "调试模式")
        self.send_button.config(state=tk.NORMAL)
        
        if "error" in response:
            self.show_error(f"错误: {response['error']}")
        else:
            try:
                # 显示AI回复 - 处理多种可能的响应格式
                ai_response = ""
                
                # 尝试解析不同格式的响应
                if "choices" in response:
                    choices = response["choices"]
                    if choices and isinstance(choices, list):
                        choice = choices[0]
                        
                        # 格式1: {"choices":[{"message":{"content":"回复内容"}}]}
                        if "message" in choice and isinstance(choice["message"], dict):
                            ai_response = choice["message"].get("content", "")
                        
                        # 格式2: {"choices":[{"text":"回复内容"}]}
                        elif "text" in choice:
                            ai_response = choice["text"]
                        
                        # 格式3: 其他可能的格式
                        else:
                            ai_response = str(choice)
                
                # 如果没有找到有效的响应内容
                if not ai_response:
                    ai_response = "收到响应，但无法解析内容。原始响应: " + str(response)
                
                self.add_message("AI", ai_response, "ai")
                
                # 添加AI回复到历史记录
                self.client.messages.append({
                    "role": "assistant",
                    "content": ai_response
                })
            except Exception as e:
                self.show_error(f"解析响应出错: {str(e)}\n原始响应: {str(response)}")
        
    def send_message(self):
        if not self.client:
            messagebox.showerror("错误", "请先设置API密钥")
            return
            
        message = self.message_input.get().strip()
        if not message:
            return
            
        # 清空输入框
        self.message_input.delete(0, tk.END)
        
        # 显示用户消息
        self.add_message("您", message, "user")
        
        # 显示发送中消息
        self.add_message("系统", "正在等待AI回复...", "system")
        
        # 禁用发送按钮
        self.send_button.config(state=tk.DISABLED)
        
        # 在新线程中发送请求
        thread = threading.Thread(target=self.send_message_thread, args=(message,))
        thread.daemon = True
        thread.start()
    
    def add_message(self, sender: str, message: str, sender_type: str):
        self.chat_display.insert(tk.END, f"\n{sender}:\n{message}\n")
        self.chat_display.see(tk.END)
        
        # 设置不同发送者的消息样式
        if sender_type == "user":
            self.chat_display.tag_add("user", "end-2c linestart", "end-1c")
            self.chat_display.tag_config("user", foreground="blue")
        elif sender_type == "ai":
            self.chat_display.tag_add("ai", "end-2c linestart", "end-1c")
            self.chat_display.tag_config("ai", foreground="green")
        else:
            self.chat_display.tag_add("system", "end-2c linestart", "end-1c")
            self.chat_display.tag_config("system", foreground="gray")
    
    def show_error(self, message: str):
        self.add_message("系统", message, "system")
    
    def show_thread_error(self, error_msg):
        # 删除"发送中"消息
        self.chat_display.delete("end-3l", "end-1l")
        
        # 恢复UI状态
        self.status_label.config(text="就绪" if not self.client.debug_mode else "调试模式")
        self.send_button.config(state=tk.NORMAL)
        
        # 显示错误信息
        self.show_error(error_msg)

    def restart_app(self):
        """重启应用程序，保留参数和聊天记录"""
        if messagebox.askyesno("确认", "确定要重启程序吗？聊天记录和参数设置将被保留。"):
            # 保存当前状态
            if self.client:
                self.client.save_state()
                
            # 清空聊天显示区域，保留消息历史
            self.chat_display.delete(1.0, tk.END)
            
            # 恢复状态
            self.status_label.config(text="就绪")
            self.send_button.config(state=tk.NORMAL)
            
            # 重新加载客户端
            if self.api_key:
                self.client = AIClient(self.api_key)
                self.client.load_state()
                
                # 重新加载消息历史到界面
                self.load_chat_history()
                
                # 刷新参数面板
                if hasattr(self, 'parameter_frame'):
                    self.parameter_frame.destroy()
                    
                self.parameter_frame = ParameterFrame(
                    self.param_frame,
                    self.client.parameters,
                    self.update_parameters
                )
                self.parameter_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # 添加欢迎消息
            self.add_message("系统", "程序已重启，参数设置和聊天记录已保留。", "system")

    def test_connection(self, api_key: str, api_endpoint: str, debug_mode: bool) -> Dict[str, Any]:
        """测试API连接"""
        # 创建临时客户端进行测试
        temp_client = AIClient(api_key)
        temp_client.base_url = api_endpoint
        temp_client.debug_mode = debug_mode
        
        # 执行连接测试
        result = temp_client.test_connection()
        return result

def main():
    root = tk.Tk()
    
    # 创建自定义样式
    style = ttk.Style()
    style.configure('Accent.TButton', font=('微软雅黑', 10, 'bold'))
    
    app = ChatWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main() 