import argparse
import os
import time
import random

import pendulum
import requests
from dotenv import load_dotenv
from BingImageCreator import ImageGen

from quota import make_quota


load_dotenv()

# required settings. config in github secrets
# -------------
# Telegram Bot Token
TG_BOT_TOKEN = os.environ['TG_BOT_TOKEN']
# Telegram Chat ID to want to send the message to
TG_CHAT_ID = os.environ['TG_CHAT_ID']
# Get Weather Information: https://github.com/baichengzhou/weather.api/blob/master/src/main/resources/citycode-2019-08-23.json to find the city code
# Shanghai 101020100
# Hangzhou 101210101 by default
WEATHER_CITY_CODE = os.environ.get('WEATHER_CITY_CODE', '101210101')
# -------------

# Optional Settings. config in github secrets.
# -------------
# 每日一句名人名言 - TIAN_API_KEY: https://www.tianapi.com/console/
# https://www.tianapi.com/console/
TIAN_API_KEY = os.environ.get('TIAN_API_KEY', '')
# Bing Cookie if image to be generated from Dalle3. Leave empty to use OpenAI by default
BING_COOKIE = os.environ.get('BING_COOKIE', '')
# 每日待办事项 todoist

# -------------

# Message list
MESSAGES = ['#每日诗歌\r\n又到了新的一天了！']


# get today's weather
# city hard coded in API URL. You may change it based on city code list below
def make_weather(city_code):
    print(f'Start making weather...')
    WEATHER_API = f'http://t.weather.sojson.com/api/weather/city/{city_code}'
    # https://github.com/baichengzhou/weather.api/blob/master/src/main/resources/citycode-2019-08-23.json to find the city code
    DEFAULT_WEATHER = "未查询到天气，好可惜啊"
    WEATHER_TEMPLATE = "今天是{date} {week}的天气是{type}，{high}，{low}，空气质量指数{aqi}"

    try:
        r = requests.get(WEATHER_API)
        if r.ok:
            weather = WEATHER_TEMPLATE.format(
                date=r.json().get("data").get("forecast")[0].get("ymd"), week=r.json().get("data").get("forecast")[0].get("week"),
                city=r.json().get("cityInfo").get("city"),
                type=r.json().get("data").get("forecast")[0].get("type"), high=r.json().get("data").get("forecast")[0].get("high"),
                low=r.json().get("data").get("forecast")[0].get("low"), aqi=r.json().get("data").get("forecast")[0].get("aqi")
            )
            return weather
        return DEFAULT_WEATHER
    except Exception as e:
        print(type(e), e)
        return DEFAULT_WEATHER

# get random poem
# return sentence(used for make pic) and poem(sentence with author and origin)


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
                sentence=sentence, author=r.json().get("author"), origin=r.json().get("origin")
            )
            return sentence, poem
        return DEFAULT_SENTENCE, DEFAULT_POEM
    except Exception as e:
        print(type(e), e)
        return DEFAULT_SENTENCE, DEFAULT_POEM


# create pic from bing image generator
# once Dalle3 api is available, this might be retired.


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
            delay = retry_delay + random.uniform(0, 2)  # Add some randomness to the delay
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)

    return [], "Failed to generate images from Bing after multiple attempts"

# try Dalle-3 from Bing first,
