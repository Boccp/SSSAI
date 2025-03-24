import PyInstaller.__main__
import os
import shutil

print("开始打包AI聊天助手...")

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 清理之前的build文件夹
for dir_to_clean in ['build', 'dist']:
    if os.path.exists(dir_to_clean):
        print(f"清理 {dir_to_clean} 文件夹...")
        shutil.rmtree(dir_to_clean)

# 配置打包选项
PyInstaller.__main__.run([
    'ai_client.py',
    '--name=AI聊天助手',
    '--windowed',
    '--onefile',
    '--add-data=README.md;.',
    '--icon=NONE',
    f'--distpath={os.path.join(current_dir, "dist")}',
    f'--workpath={os.path.join(current_dir, "build")}',
    f'--specpath={current_dir}',
])

print("打包完成！程序已生成在dist文件夹中。")
print("提示：首次运行程序后，设置和聊天记录将保存在同一目录下。") 