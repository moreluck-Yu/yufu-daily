import argparse  
import os  
import time  
import random  
import json  # 添加此行  
import requests  
from dotenv import load_dotenv  
from BingImageCreator import ImageGen  
from quota import make_quota  

# required settings. config in github secrets  
# -------------  
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']  
TG_BOT_TOKEN = os.environ['TG_BOT_TOKEN']  
TG_CHAT_ID = os.environ['TG_CHAT_ID']  
WEATHER_CITY_CODE = os.environ.get('WEATHER_CITY_CODE', '101210101')  

# Optional Settings. config in github secrets.  
TIAN_API_KEY = os.environ.get('TIAN_API_KEY', '')  
BING_COOKIE = os.environ.get('BING_COOKIE', '')  

load_dotenv()  

# Load the OPENAI_URL from GitHub Secrets  
OPENAI_URL = os.environ.get('OPENAI_URL', 'https://api.openai.com/v1')  

# Message list  
MESSAGES = ['#每日诗歌\r\n又到了新的一天了！']  

# get today's weather  
def make_weather(city_code):  
    print(f'Start making weather...')  
    WEATHER_API = f'http://t.weather.sojson.com/api/weather/city/{city_code}'  
    DEFAULT_WEATHER = "未查询到天气，好可惜啊"  
    WEATHER_TEMPLATE = "今天是{date} {week}的天气是{type}，{high}，{low}，空气量指数{aqi}"  
  
    try:  
        r = requests.get(WEATHER_API)  
        if r.ok:  
            weather = WEATHER_TEMPLATE.format(  
                date=r.json().get("data").get("forecast")[0].get("ymd"), week=r.json().get("data").get("forecast")[0].get("week"),  
                city=r.json().get("data").get("forecast")[0].get("city"),  
                type=r.json().get("data").get("forecast")[0].get("type"), high=r.json().get("data").get("forecast")[0].get("high"),  
                low=r.json().get("data").get("forecast")[0].get("low"), aqi=r.json().get("data").get("forecast")[0].get("aqi")  
            )  
            return weather  
        return DEFAULT_WEATHER  
    except Exception as e:  
        print(type(e), e)  
        return DEFAULT_WEATHER  

def get_poem():  
    SENTENCE_API = "https://v1.jinrishici.com/all"  
    DEFAULT_SENTENCE
