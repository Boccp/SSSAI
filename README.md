# AI API 客户端

这是一个简单的AI API客户端程序，用于与AI平台进行交互。

## 安装

1. 确保您已安装 Python 3.7 或更高版本
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 配置

1. 设置环境变量 `AI_API_KEY`：
   - Windows:
     ```bash
     set AI_API_KEY=你的API密钥
     ```
   - Linux/Mac:
     ```bash
     export AI_API_KEY=你的API密钥
     ```

2. 在 `ai_client.py` 中修改 `base_url` 为您的实际API地址

## 使用方法

运行程序：
```bash
python ai_client.py
```

## 注意事项

- 请确保妥善保管您的API密钥
- 不要将API密钥直接硬编码在代码中
- 建议使用环境变量来管理API密钥 