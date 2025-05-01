#!/bin/bash
# 安装智能植物监控系统所需的依赖

echo "开始安装智能植物监控系统所需的依赖..."

# 更新软件包列表
sudo apt-get update

# 安装MPV视频播放器
sudo apt-get install -y mpv

# 安装Python依赖
pip3 install pygame RPi.GPIO smbus-cffi numpy SpeechRecognition gTTS

# 安装音频相关组件
sudo apt-get install -y python3-pyaudio

# 检查安装结果
echo "检查安装的软件包..."
command -v mpv >/dev/null 2>&1 || { echo "警告: mpv未安装成功，系统可能在模拟模式下运行"; }
command -v pip3 >/dev/null 2>&1 || { echo "错误: pip3未安装成功"; exit 1; }

echo "所有依赖安装完成!"
echo ""
echo "运行系统: python3 plant_monitor.py"
echo "注意: 在树莓派上可能需要用sudo运行: sudo python3 plant_monitor.py"