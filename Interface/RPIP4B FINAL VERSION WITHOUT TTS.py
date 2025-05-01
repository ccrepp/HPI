#!/usr/bin/env python3
"""
智能植物监控系统 - 按需读取传感器，支持触摸/鼠标交互
- 默认显示Normal状态动画
- 通过触摸/鼠标点击屏幕按钮读取传感器数据
- 状态正常时显示当前数值，异常时显示对应动画
- 语音交互功能已暂时禁用
"""

import os
import time
import threading
import subprocess
import json
import pygame
from pygame.locals import *
import numpy as np

# 当在非树莓派环境运行时，允许模拟模式
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    print("警告: GPIO库不可用，运行在模拟模式")
    GPIO_AVAILABLE = False

# 暂时禁用语音功能
# 创建模拟类以避免导入错误
class SpeechRecognitionMock:
    class Recognizer:
        def __init__(self):
            pass
    class Microphone:
        def __enter__(self):
            return None
        def __exit__(self, *args):
            pass
        
class GTTSMock:
    def __init__(self, text=None, lang=None):
        pass
    def save(self, filename):
        pass

# 使用模拟类代替实际模块
sr = SpeechRecognitionMock
gTTS = GTTSMock
SPEECH_AVAILABLE = False

# I2C配置 (用于土壤湿度和光照传感器)
I2C_ADDRESS = 0x48  # PCF8591的默认I2C地址
try:
    import smbus
    bus = smbus.SMBus(1)  # 使用I2C-1
    I2C_AVAILABLE = True
except:
    print("警告: I2C总线不可用，运行在模拟模式")
    I2C_AVAILABLE = False

# 视频路径
VIDEOS = {
    "normal": "/home/UNM.RPI4B/videos/normal.mp4",    # 默认状态
    "dry": "/home/UNM.RPI4B/videos/dry.mp4",          # 干燥状态
    "wet": "/home/UNM.RPI4B/videos/wet.mp4",          # 湿润状态
    "dark": "/home/UNM.RPI4B/videos/dark.mp4",        # 光线不足状态
    "bright": "/home/UNM.RPI4B/videos/bright.mp4",    # 光线过强状态
    "hot": "/home/UNM.RPI4B/videos/hot.mp4",          # 温度过高状态
    "cold": "/home/UNM.RPI4B/videos/cold.mp4",        # 温度过低状态
    "humid": "/home/UNM.RPI4B/videos/humid.mp4"       # 湿度过高状态
}

# 传感器阈值配置
SENSOR_THRESHOLDS = {
    "moisture": {
        "dry": 160,    # 高于此值为干燥
        "wet": 140     # 低于此值为湿润
    },
    "light": {
        "dark": 80,    # 低于此值为光线不足
        "bright": 200  # 高于此值为光线过强
    },
    "temperature": {
        "cold": 15,    # 低于此值为寒冷
        "hot": 30      # 高于此值为炎热
    },
    "humidity": {
        "dry_air": 30, # 低于此值为空气干燥
        "humid": 70    # 高于此值为空气湿润
    }
}

# 全局变量
current_video = "normal"
video_process = None
is_stt_enabled = False  # 默认禁用语音功能
is_displaying_values = False
sensor_values = {
    "moisture": 0,
    "light": 0,
    "temperature": 0,
    "humidity": 0
}
sensor_status = {
    "moisture": "normal",
    "light": "normal",
    "temperature": "normal",
    "humidity": "normal"
}
lock = threading.Lock()

# 初始化pygame (用于屏幕显示和按钮处理)
pygame.init()
pygame.mixer.init()
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 480
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("植物监控系统")
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)

# 设置音频文件路径
audio_path = "/tmp/plant_speech.mp3"

# MPV播放器路径
MPV_PATH = "/usr/bin/mpv"

class DHTSensor:
    """DHT温湿度传感器类"""
    def __init__(self, pin=4, sensor_type=22):
        self.pin = pin
        self.sensor_type = sensor_type  # 11 for DHT11, 22 for DHT22

    def read(self):
        """读取DHT传感器数据"""
        try:
            # 使用已有的dht_test.py脚本获取温湿度
            output = subprocess.check_output(
                [sys.executable, "dht_test.py", str(self.sensor_type), str(self.pin)],
                stderr=subprocess.STDOUT
            ).decode("utf-8")
            
            # 解析输出
            if "Temp:" in output and "Humidity:" in output:
                parts = output.split()
                temp_index = parts.index("Temp:")
                humidity_index = parts.index("Humidity:")
                
                temperature = float(parts[temp_index + 1])
                humidity = float(parts[humidity_index + 1])
                
                return temperature, humidity
            else:
                return None, None
        except Exception as e:
            print(f"DHT读取错误: {e}")
            return None, None

def read_adc(channel):
    """从PCF8591读取ADC值，如果不可用则返回模拟值"""
    if I2C_AVAILABLE:
        try:
            bus.write_byte(I2C_ADDRESS, channel)
            bus.read_byte(I2C_ADDRESS)  # 虚拟读取以初始化ADC
            value = bus.read_byte(I2C_ADDRESS)
            return value
        except Exception as e:
            print(f"ADC读取错误: {e}")
            return 0
    else:
        # 模拟模式，返回合理的模拟值
        import random
        if channel == 0:  # 光照传感器
            return random.randint(80, 200)
        elif channel == 1:  # 土壤湿度传感器
            return random.randint(130, 170)
        return random.randint(100, 200)

def read_moisture():
    """读取土壤湿度传感器"""
    value = read_adc(1)  # AIN1通道
    with lock:
        sensor_values["moisture"] = value
        
        # 确定湿度状态
        if value > SENSOR_THRESHOLDS["moisture"]["dry"]:
            sensor_status["moisture"] = "dry"
        elif value < SENSOR_THRESHOLDS["moisture"]["wet"]:
            sensor_status["moisture"] = "wet"
        else:
            sensor_status["moisture"] = "normal"
    
    return value, sensor_status["moisture"]

def read_light():
    """读取光照传感器"""
    value = read_adc(0)  # AIN0通道
    with lock:
        sensor_values["light"] = value
        
        # 确定光照状态
        if value < SENSOR_THRESHOLDS["light"]["dark"]:
            sensor_status["light"] = "dark"
        elif value > SENSOR_THRESHOLDS["light"]["bright"]:
            sensor_status["light"] = "bright"
        else:
            sensor_status["light"] = "normal"
    
    return value, sensor_status["light"]

def read_dht():
    """读取DHT温湿度传感器"""
    if GPIO_AVAILABLE:
        dht = DHTSensor()
        temperature, humidity = dht.read()
    else:
        # 模拟模式，返回合理的模拟值
        import random
        temperature = random.uniform(15, 30)
        humidity = random.uniform(30, 70)
    
    if temperature is not None and humidity is not None:
        with lock:
            sensor_values["temperature"] = temperature
            sensor_values["humidity"] = humidity
            
            # 确定温度状态
            if temperature < SENSOR_THRESHOLDS["temperature"]["cold"]:
                sensor_status["temperature"] = "cold"
            elif temperature > SENSOR_THRESHOLDS["temperature"]["hot"]:
                sensor_status["temperature"] = "hot"
            else:
                sensor_status["temperature"] = "normal"
                
            # 确定湿度状态
            if humidity < SENSOR_THRESHOLDS["humidity"]["dry_air"]:
                sensor_status["humidity"] = "dry_air"
            elif humidity > SENSOR_THRESHOLDS["humidity"]["humid"]:
                sensor_status["humidity"] = "humid"
            else:
                sensor_status["humidity"] = "normal"
    
    return (temperature, humidity, 
            sensor_status["temperature"], 
            sensor_status["humidity"])

def play_video(video_key, duration=None):
    """播放指定视频，可选择播放时长"""
    global video_process, current_video
    
    # 无论有没有视频文件，都更新当前视频状态
    current_video = video_key
    
    # 如果视频进程在运行，先终止它
    if video_process and video_process.poll() is None:
        video_process.terminate()
        try:
            video_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            video_process.kill()
    
    # 检查视频文件是否存在
    video_path = VIDEOS.get(video_key)
    if not video_path or not os.path.exists(video_path):
        print(f"警告：视频文件不存在 - {video_path}")
        return
    
    # 构建MPV命令
    cmd = [
        MPV_PATH,
        "--loop" if duration is None else "--no-loop",
        "--fs",
        "--no-input-terminal",  # 禁止终端输入，避免干扰
        "--really-quiet",       # 减少输出
        "--no-osc",             # 禁用屏幕控件
        video_path
    ]
    
    # 设置环境变量确保正确的显示
    my_env = os.environ.copy()
    my_env["DISPLAY"] = ":0"
    
    try:
        video_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=my_env
        )
        
        # 如果指定了时长，则在指定时间后恢复正常视频
        if duration:
            def restore_normal():
                time.sleep(duration)
                play_video("normal")
            
            threading.Thread(target=restore_normal, daemon=True).start()
            
    except Exception as e:
        print(f"播放视频时发生错误: {e}")

def display_osd_value(sensor_type, value, status="normal"):
    """在屏幕上显示传感器值"""
    global is_displaying_values
    
    # 设置OSD消息
    osd_message = ""
    if sensor_type == "water":
        osd_message = f"Soil Moisture: {value} - {status.upper()}"
    elif sensor_type == "light":
        osd_message = f"Light Level: {value} - {status.upper()}"
    elif sensor_type == "temperature":
        osd_message = f"Temperature: {value}°C - {status.upper()}"
    elif sensor_type == "humidity":
        osd_message = f"Air Humidity: {value}% - {status.upper()}"
    
    # 更新视频的OSD
    if video_process and video_process.poll() is None:
        video_process.terminate()
        try:
            video_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            video_process.kill()
    
    # 仅当状态异常时才显示异常视频
    if status != "normal" and sensor_type in ["water", "light", "temperature", "humidity"]:
        video_key = {
            "water": {"dry": "dry", "wet": "wet"},
            "light": {"dark": "dark", "bright": "bright"},
            "temperature": {"hot": "hot", "cold": "cold"},
            "humidity": {"humid": "humid", "dry_air": "normal"}
        }
        
        status_video = video_key.get(sensor_type, {}).get(status)
        if status_video:
            play_video(status_video, duration=5)  # 播放5秒后恢复正常
    
    # 设置显示标志
    is_displaying_values = True
    
    # 启动一个线程来清除显示
    def clear_osd():
        time.sleep(3)  # 显示3秒
        global is_displaying_values
        is_displaying_values = False
    
    threading.Thread(target=clear_osd, daemon=True).start()

def speak_text(text):
    """将文本转换为语音并播放 - 已禁用"""
    print(f"语音已禁用，要说的文字: {text}")
    # 因为语音功能已禁用，这个函数不执行实际操作

def listen_speech():
    """监听用户语音并返回文本 - 已禁用"""
    print("语音功能已禁用")
    return "语音功能已禁用"

def process_speech(speech_text):
    """处理语音指令并返回回复 - 已禁用"""
    return "语音功能已禁用"

def stt_thread():
    """语音交互线程 - 已禁用"""
    global is_stt_enabled
    
    # 由于语音功能已禁用，保持线程运行但不执行实际操作
    is_stt_enabled = False
    while True:
        time.sleep(1)

def draw_ui(buttons, button_states):
    """绘制用户界面"""
    # 绘制背景
    screen.fill((0, 0, 0))
    
    # 绘制可点击按钮
    for btn in buttons:
        # 如果按钮处于按下状态，使用绿色填充
        is_pressed = button_states[btn["action"]]
        
        # 根据按钮状态选择颜色
        if btn["action"] == "voice":
            # 语音按钮始终显示为禁用状态
            color = (100, 100, 100)  # 语音禁用时为灰色
            text_color = (200, 200, 200)
            border = 2
        elif is_pressed:
            color = (100, 255, 100)  # 按下时为亮绿色
            text_color = (0, 0, 0)
            border = 0
        else:
            color = (80, 80, 80)  # 未按下时为灰色
            text_color = (255, 255, 255)
            border = 2
        
        # 绘制按钮
        pygame.draw.rect(screen, color, btn["rect"], border)
        text = font.render(btn["text"], True, text_color)
        text_x = btn["rect"].x + (btn["rect"].width - text.get_width()) // 2
        text_y = btn["rect"].y + (btn["rect"].height - text.get_height()) // 2
        screen.blit(text, (text_x, text_y))
    
    # 在顶部绘制当前视频状态
    status_text = f"当前状态: {current_video.upper()}"
    status = font.render(status_text, True, (255, 255, 255))
    screen.blit(status, (20, 20))
    
    # 显示当前传感器值
    if is_displaying_values:
        with lock:
            text_lines = [
                f"水分: {sensor_values['moisture']} ({sensor_status['moisture']})",
                f"光线: {sensor_values['light']} ({sensor_status['light']})",
                f"温度: {sensor_values['temperature']:.1f}°C ({sensor_status['temperature']})",
                f"湿度: {sensor_values['humidity']:.1f}% ({sensor_status['humidity']})"
            ]
        
        # 在屏幕右上方显示传感器数据面板
        panel_width = 300
        panel_height = 150
        panel_x = SCREEN_WIDTH - panel_width - 20
        panel_y = 20
        
        # 绘制半透明面板背景
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 180))  # 黑色半透明背景
        screen.blit(panel_surface, (panel_x, panel_y))
        
        # 添加标题
        title_text = "传感器数据"
        title = small_font.render(title_text, True, (255, 255, 255))
        screen.blit(title, (panel_x + 10, panel_y + 10))
        
        # 添加数据行
        for i, line in enumerate(text_lines):
            color = (255, 255, 255)  # 默认白色
            # 根据状态着色
            if "normal" not in line:
                color = (255, 100, 100)  # 异常状态为红色
                
            text = small_font.render(line, True, color)
            screen.blit(text, (panel_x + 10, panel_y + 40 + i * 25))
    
    # 如果语音功能已禁用，显示禁用状态
    voice_text = "语音功能已禁用"
    voice_status = small_font.render(voice_text, True, (255, 100, 100))
    screen.blit(voice_status, (SCREEN_WIDTH // 2 - voice_status.get_width() // 2, 60))
    
    pygame.display.flip()

def main():
    """主函数"""
    print("智能植物监控系统启动...")
    
    # 检查MPV路径
    if not os.path.exists(MPV_PATH):
        print(f"警告: MPV播放器未找到在 {MPV_PATH}，将使用模拟模式")
    
    # 检查视频文件
    missing_videos = []
    for key, path in VIDEOS.items():
        if not os.path.exists(path):
            missing_videos.append(f"{key}: {path}")
    
    if missing_videos:
        print("警告: 以下视频文件不存在:")
        for v in missing_videos:
            print(f"  - {v}")
        
        choice = input("是否继续? (y/n): ").lower()
        if choice != 'y':
            return
    
    # 启动已禁用的语音交互线程
    threading.Thread(target=stt_thread, daemon=True).start()
    
    # 播放默认视频（如果可用）
    if os.path.exists(VIDEOS["normal"]):
        play_video("normal")
    
    # 创建按钮定义
    buttons = [
        {"text": "Water", "rect": pygame.Rect(50, SCREEN_HEIGHT - 60, 150, 50), "action": "water"},
        {"text": "Light", "rect": pygame.Rect(225, SCREEN_HEIGHT - 60, 150, 50), "action": "light"},
        {"text": "DHT", "rect": pygame.Rect(400, SCREEN_HEIGHT - 60, 150, 50), "action": "dht"},
        {"text": "Voice", "rect": pygame.Rect(575, SCREEN_HEIGHT - 60, 150, 50), "action": "voice"}
    ]
    
    # 按钮状态
    button_states = {button["action"]: False for button in buttons}
    
    # 主循环
    clock = pygame.time.Clock()
    running = True
    
    try:
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    running = False
                elif event.type == MOUSEBUTTONDOWN:
                    # 检查点击是否在按钮上
                    pos = pygame.mouse.get_pos()
                    for button in buttons:
                        if button["rect"].collidepoint(pos):
                            # 设置按钮状态为按下
                            button_states[button["action"]] = True
                            
                            # 执行对应操作
                            if button["action"] == "water":
                                moisture, status = read_moisture()
                                display_osd_value("water", moisture, status)
                            elif button["action"] == "light":
                                light, status = read_light()
                                display_osd_value("light", light, status)
                            elif button["action"] == "dht":
                                temp, humid, temp_status, humid_status = read_dht()
                                if temp is not None and humid is not None:
                                    display_osd_value("temperature", temp, temp_status)
                                    # 2秒后显示湿度
                                    threading.Timer(2, lambda: display_osd_value("humidity", humid, humid_status)).start()
                            elif button["action"] == "voice":
                                # Voice按钮已禁用
                                print("语音功能已禁用")
                            
                            # 0.2秒后恢复按钮状态
                            def reset_button(action):
                                time.sleep(0.2)
                                button_states[action] = False
                            
                            threading.Thread(target=reset_button, args=(button["action"],), daemon=True).start()
            
            # 绘制UI
            draw_ui(buttons, button_states)
            
            # 限制帧率
            clock.tick(30)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    finally:
        # 清理资源
        if video_process and video_process.poll() is None:
            video_process.terminate()
        
        if GPIO_AVAILABLE:
            GPIO.cleanup()
        pygame.quit()
        print("程序已关闭")

if __name__ == "__main__":
    import sys
    main()