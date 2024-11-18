import argparse
import os
import time
import random
import json
import pendulum
import requests
from dotenv import load_dotenv
from BingImageCreator import ImageGen
from quota import make_quota

load_dotenv()

# required settings. config in github secrets
# -------------
# Silicon Flow API Key
SILICON_FLOW_API_KEY = os.environ['SILICON_FLOW_API_KEY']

# Telegram Bot Token
TG_BOT_TOKEN = os.environ['TG_BOT_TOKEN']

# Telegram Chat ID to want to send the message to
TG_CHAT_ID = os.environ['TG_CHAT_ID']

# Get Weather Information: https://github.com/baichengzhou/weather.api/blob/master/src/main/resources/citycode-2019-08-23.json to find the city code
# Shanghai 101020100
# Hangzhou 101210101 by default
WEATHER_CITY_CODE = 101180801

# -------------
# Optional Settings. config in github secrets.
# -------------
# 每日一句名人名言 - TIAN_API_KEY: https://www.tianapi.com/console/
TIAN_API_KEY = os.environ.get('TIAN_API_KEY', '')

# Bing Cookie if image to be generated from Dalle3. Leave empty to use Silicon Flow by default
BING_COOKIE = os.environ.get('BING_COOKIE', '')

# Message list
MESSAGES = ['#每日诗歌\r\n又到了新的一天了！']

def make_weather():
    print(f'Start making weather...')
    WEATHER_API = f'http://t.weather.sojson.com/api/weather/city/101020100'
    DEFAULT_WEATHER = "未查询到天气，好可惜啊"
    WEATHER_TEMPLATE = "今天是{date} {week}的天气是{type}，{high}，{low}，空气量指数{aqi}"
    
    try:
        r = requests.get(WEATHER_API)
        if r.ok:
            weather = WEATHER_TEMPLATE.format(
                date=r.json().get("data").get("forecast")[0].get("ymd"),
                week=r.json().get("data").get("forecast")[0].get("week"),
                city=r.json().get("cityInfo").get("city"),
                type=r.json().get("data").get("forecast")[0].get("type"),
                high=r.json().get("data").get("forecast")[0].get("high"),
                low=r.json().get("data").get("forecast")[0].get("low"),
                aqi=r.json().get("data").get("forecast")[0].get("aqi")
            )
            return weather
        return DEFAULT_WEATHER
    except Exception as e:
        print(type(e), e)
        return DEFAULT_WEATHER

def get_poem():
    SENTENCE_API = "https://v1.jinrishici.com/all"
    DEFAULT_SENTENCE = "落日净残阳 雾水拈薄浪 "
    DEFAULT_POEM = "落日净残阳，雾水拈薄浪。 —— Xiaowen.Z / 卜算子"
    POEM_TEMPLATE = "{sentence} —— {author} / {origin}"
    
    try:
        r = requests.get(SENTENCE_API)
        if r.ok:
            sentence = r.json().get("content")
            poem = POEM_TEMPLATE.format(
                sentence=sentence,
                author=r.json().get("author"),
                origin=r.json().get("origin")
            )
            return sentence, poem
        return DEFAULT_SENTENCE, DEFAULT_POEM
    except Exception as e:
        print(type(e), e)
        return DEFAULT_SENTENCE, DEFAULT_POEM

def make_pic_from_silicon(sentence):
    url = "https://api.siliconflow.cn/v1/images/generations"
    
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell",
        "prompt": sentence,
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

def make_pic_from_bing(sentence, bing_cookie):
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            i = ImageGen(bing_cookie)
            images = i.get_images(sentence)
            if images and len(images) > 0:
                return images, "Images Powered by Bing DALL-E-3"
            else:
                print(f"No images generated on attempt {attempt + 1}")
        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {str(e)}")
        
        if attempt < max_retries - 1:
            delay = retry_delay + random.uniform(0, 2)
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    return [], "Failed to generate images from Bing after multiple attempts"

def make_pic(sentence):
    # 首先尝试使用Silicon Flow生成图片
    try:
        image_url, image_comment = make_pic_from_silicon(sentence)
        return [image_url], image_comment
    except Exception as e:
        print(f'Silicon Flow图片生成失败: {type(e)}')
        print(type(e), e)
        print('尝试使用Bing作为备选。')
    
    # 如果Silicon Flow失败且设置了Bing Cookie,则尝试使用Bing
    if BING_COOKIE:
        try:
            image_urls, image_comment = make_pic_from_bing(sentence, BING_COOKIE)
            if image_urls:
                return image_urls, image_comment
            else:
                print('Bing图片生成也失败了。')
        except Exception as e:
            print(f'Bing图片生成出错: {type(e)}')
            print(type(e), e)
    else:
        print('未设置Bing Cookie,无法使用Bing作为备选。')
    
    # 如果两种方法都失败,返回空列表和错误消息
    return [], "无法生成图片"


def make_poem():
    print(f'Start making poem...')
    sentence, poem = get_poem()
    sentence_processed = sentence.replace("，", " ").replace("。", " ").replace(".", " ")
    print(f'Processed Sentence: {sentence_processed}')
    image_urls, image_comment = make_pic(sentence_processed)
    poem_message = f'今日诗词和配图：\r\n{poem}\r\n\r\n{image_comment}'
    return image_urls, poem_message

def send_tg_message(tg_bot_token, tg_chat_id, message, images=None):
    print(f'Sending to Chat {tg_chat_id}')
    if images is None or len(images) == 0:
        try:
            request_url = "https://api.telegram.org/bot{tg_bot_token}/sendMessage".format(
                tg_bot_token=tg_bot_token)
            request_data = {'chat_id': tg_chat_id, 'text': message}
            response = requests.post(request_url, data=request_data)
            return response.json()
        except Exception as e:
            print("Failed sending message to Telegram Bot.")
            print(type(e), e)
            return ""
    else:
        try:
            media_group = [{'type': 'photo', 'media': image} for image in images]
            media_group[0]['caption'] = message  # 只在第一张图片上添加消息
            request_url = "https://api.telegram.org/bot{tg_bot_token}/sendMediaGroup".format(
                tg_bot_token=tg_bot_token)
            request_data = {'chat_id': tg_chat_id, 'media': json.dumps(media_group)}
            response = requests.post(request_url, data=request_data)
            return response.json()
        except Exception as e:
            print("Failed sending message to Telegram Bot with images.")
            print(type(e), e)
            return ""

def make_message(messages):
    message = "\r\n---\r\n".join(messages)
    return message

def main():
    print("Main started...")
    MESSAGES.append(make_weather(WEATHER_CITY_CODE))
    image_urls, poem_message = make_poem()
    MESSAGES.append(poem_message)

    if TIAN_API_KEY is not None and TIAN_API_KEY != '':
        MESSAGES.append(make_quota(TIAN_API_KEY))

    full_message = make_message(MESSAGES)
    print("Message constructed...")
    print()

    r_json = send_tg_message(tg_bot_token=TG_BOT_TOKEN,
                            tg_chat_id=TG_CHAT_ID,
                            message=full_message,
                            images=image_urls)
    print(r_json)

if __name__ == "__main__":
    main()
