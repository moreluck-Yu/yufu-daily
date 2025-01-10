import argparse
import os
import random
import sys
import time
from pathlib import Path

import pendulum
import requests
from telegram import Bot

# 设置环境变量和常量
SILICON_FLOW_API_KEY = os.getenv("SILICON_FLOW_API_KEY")
BING_SUBSCRIPTION_KEY = os.getenv("BING_SUBSCRIPTION_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 检查必要的环境变量
if not all([SILICON_FLOW_API_KEY, BING_SUBSCRIPTION_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("请设置所有必要的环境变量")
    sys.exit(1)

def get_one_sentence():
    """获取一句诗词"""
    url = "https://v1.jinrishici.com/all"
    try:
        r = requests.get(url, timeout=10)
        if r.ok:
            return r.json().get("content", "")
        return ""
    except:
        return ""

def optimize_prompt(sentence):
    """使用 Qwen 模型优化提示词"""
    url = "https://api.siliconflow.cn/v1/chat/completions"
    
    payload = {
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": f"revise `{sentence}` to a stable diffusion prompt"
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {SILICON_FLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.ok:
            result = response.json()
            optimized_sentence = result['choices'][0]['message']['content']
            print(f'优化后的提示词: {optimized_sentence}')
            return optimized_sentence
        else:
            print(f'提示词优化失败: {response.status_code} - {response.text}')
            return sentence
    except Exception as e:
        print(f'提示词优化失败: {str(e)}')
        return sentence

def make_pic_from_silicon(sentence):
    """使用 Silicon Flow API 生成图片"""
    url = "https://api.siliconflow.cn/v1/images/generations"
    
    # 优化提示词
    optimized_prompt = optimize_prompt(sentence)
    
    payload = {
        "model": "black-forest-labs/FLUX.1-dev",
        "prompt": optimized_prompt,
        "num_inference_steps": 20,
        "prompt_enhancement": True,
        "image_size": "1024x1024"
    }
    
    headers = {
        "Authorization": f"Bearer {SILICON_FLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    print(f'正在调用 Silicon Flow API 生成图片...')
    response = requests.post(url, json=payload, headers=headers)
    
    if response.ok:
        result = response.json()
        image_url = result.get('data')[0].get('url')
        print(f'生成的图片URL: {image_url}')
        print(f'完整返回结果: {result}')
        return image_url, "图片由 Silicon Flow FLUX.1 提供支持"
    else:
        print(f'发生错误: {response.status_code} - {response.text}')
        raise Exception("图片生成失败")

def make_pic_from_bing(sentence):
    """使用 Bing DALL-E-3 生成图片"""
    endpoint = "https://api.bing.microsoft.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": BING_SUBSCRIPTION_KEY,
    }
    data = {"prompt": sentence}
    for _ in range(3):
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=60)
            if response.ok:
                result = response.json()
                return result["urls"][0], "图片由 Bing DALL-E-3 提供支持"
        except Exception as e:
            print(str(e))
            time.sleep(2)
    raise Exception("图片生成失败")

def get_weather_info():
    """获取天气信息"""
    try:
        # 使用和风天气 API 获取天气信息
        key = os.getenv("WEATHER_KEY", "")
        location = os.getenv("WEATHER_LOCATION", "")
        if not key or not location:
            return None
        url = f"https://devapi.qweather.com/v7/weather/now?key={key}&location={location}"
        r = requests.get(url, timeout=10)
        if r.ok:
            result = r.json()
            if result.get("code") == "200":
                now = result["now"]
                return f'当前温度{now["temp"]}°C, {now["text"]}, 体感温度{now["feelsLike"]}°C, 相对湿度{now["humidity"]}%, {now["windDir"]}{now["windScale"]}级'
    except:
        pass
    return None

def send_to_telegram(sentence, pic_url, weather_info=None, pic_info=""):
    """发送消息到 Telegram"""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    if weather_info:
        message = f"{sentence}\n\n{weather_info}"
    else:
        message = sentence
    
    if pic_info:
        message = f"{message}\n\n{pic_info}"
    
    try:
        bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=pic_url,
            caption=message
        )
        return True
    except Exception as e:
        print(f"发送失败: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--use_bing", action="store_true", help="使用 Bing DALL-E-3 替代 Silicon Flow")
    args = parser.parse_args()
    
    sentence = get_one_sentence()
    if not sentence:
        print("获取诗句失败")
        return
    print(f"获取到的诗句: {sentence}")
    
    try:
        if args.use_bing:
            pic_url, pic_info = make_pic_from_bing(sentence)
        else:
            pic_url, pic_info = make_pic_from_silicon(sentence)
        print(f"生成的图片 URL: {pic_url}")
        
        weather_info = get_weather_info()
        if weather_info:
            print(f"天气信息: {weather_info}")
        
        if send_to_telegram(sentence, pic_url, weather_info, pic_info):
            print("发送成功")
        else:
            print("发送失败")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()
