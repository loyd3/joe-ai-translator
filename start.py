#!/usr/bin/env python3
"""
一键启动脚本
同时启动后端和前端开发服务器
"""

import subprocess
import sys
import os
import signal
import time

# 颜色输出
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}  {text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def check_command(cmd):
    """检查命令是否存在"""
    return subprocess.run(f"which {cmd}", shell=True, capture_output=True).returncode == 0

def run_command(cmd, cwd=None, env=None):
    """运行命令并返回进程"""
    return subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        env=env,
        preexec_fn=os.setsid if sys.platform != "win32" else None
    )

def main():
    print_header("🌐 AI Translator 启动脚本")
    
    # 获取项目根目录
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    frontend_dir = os.path.join(root_dir, "frontend")
    
    processes = []
    
    try:
        # 检查 Python
        print(f"{YELLOW}🔍 检查环境...{RESET}")
        if not check_command("python3") and not check_command("python"):
            print(f"{RED}❌ 未找到 Python，请安装 Python 3.11+{RESET}")
            sys.exit(1)
        
        python_cmd = "python3" if check_command("python3") else "python"
        
        # 检查 Node.js
        if not check_command("node"):
            print(f"{RED}❌ 未找到 Node.js，请安装 Node.js 20+{RESET}")
            sys.exit(1)
        
        # 检查 .env 文件
        env_file = os.path.join(root_dir, ".env")
        if not os.path.exists(env_file):
            print(f"{YELLOW}⚠️  .env 文件不存在，正在从模板创建...{RESET}")
            if os.path.exists(os.path.join(root_dir, ".env.example")):
                with open(os.path.join(root_dir, ".env.example")) as f:
                    content = f.read()
                with open(env_file, "w") as f:
                    f.write(content)
                print(f"{GREEN}✅ 已创建 .env 文件，请编辑配置你的 API Key{RESET}")
            else:
                print(f"{RED}❌ 找不到 .env.example 文件{RESET}")
                sys.exit(1)
        
        # 初始化数据库
        print(f"\n{YELLOW}🗄️  初始化数据库...{RESET}")
        result = subprocess.run([python_cmd, "init_db.py"], cwd=root_dir, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"{GREEN}✅ 数据库初始化完成{RESET}")
        else:
            print(f"{RED}❌ 数据库初始化失败: {result.stderr}{RESET}")
        
        # 安装后端依赖
        print(f"\n{YELLOW}📦 检查后端依赖...{RESET}")
        venv_dir = os.path.join(backend_dir, "venv")
        if not os.path.exists(venv_dir):
            print(f"  创建虚拟环境...")
            subprocess.run([python_cmd, "-m", "venv", "venv"], cwd=backend_dir)
        
        pip_cmd = os.path.join(venv_dir, "bin", "pip") if sys.platform != "win32" else os.path.join(venv_dir, "Scripts", "pip.exe")
        subprocess.run([pip_cmd, "install", "-q", "-r", "requirements.txt"], cwd=backend_dir)
        print(f"{GREEN}✅ 后端依赖已安装{RESET}")
        
        # 安装前端依赖
        print(f"\n{YELLOW}📦 检查前端依赖...{RESET}")
        if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
            print(f"  安装 npm 包...")
            subprocess.run(["npm", "install"], cwd=frontend_dir)
        print(f"{GREEN}✅ 前端依赖已安装{RESET}")
        
        # 启动后端
        print(f"\n{GREEN}🚀 启动后端服务...{RESET}")
        python_path = os.path.join(venv_dir, "bin", "python") if sys.platform != "win32" else os.path.join(venv_dir, "Scripts", "python.exe")
        backend_cmd = f"{python_path} -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        backend_process = run_command(backend_cmd, cwd=backend_dir)
        processes.append(backend_process)
        print(f"  {BLUE}后端: http://localhost:8000{RESET}")
        print(f"  {BLUE}API 文档: http://localhost:8000/docs{RESET}")
        
        # 等待后端启动
        time.sleep(2)
        
        # 启动前端
        print(f"\n{GREEN}🚀 启动前端开发服务器...{RESET}")
        frontend_process = run_command("npm run dev", cwd=frontend_dir)
        processes.append(frontend_process)
        print(f"  {BLUE}前端: http://localhost:5173{RESET}")
        
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}  ✅ AI Translator 已启动！{RESET}")
        print(f"{GREEN}{'='*60}{RESET}")
        print(f"\n访问 {YELLOW}http://localhost:5173{RESET} 开始使用")
        print(f"\n按 Ctrl+C 停止服务\n")
        
        # 等待进程
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}🛑 正在停止服务...{RESET}")
        for process in processes:
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()
            except:
                pass
        print(f"{GREEN}✅ 服务已停止{RESET}")

if __name__ == "__main__":
    main()
