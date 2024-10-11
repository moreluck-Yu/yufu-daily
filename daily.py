import argparse  
import os  
import time  
import random  
import json  # 添加此行  
from openai import OpenAI  
import pendulum  
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

def make_pic_from_openai(sentence):  
    client = OpenAI(  
        api_key=OPENAI_API_KEY,  
        base_url=OPENAI_URL  # 使用自定义的 OPENAI_URL  
    )  
    print(f'calling open ai for image creation...')  
    response = client.images.generate(  
        prompt=sentence, n=1, size="1024x1024", model="dall-e-3", style="vivid")  
  
    image_url = response.data[0].url  
    print(f'image_url:{image_url}')  
    print(f'image_revised_prompt: {response.data[0].revised_prompt}')  
    print(f'full response: {response}')  
    return image_url, "Image Powered by OpenAI DELL.E-3"  

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

def make_pic(sentence):  
    if BING_COOKIE:  
        try:  
            image_urls, image_comment = make_pic_from_bing(sentence, BING_COOKIE)  
            if image_urls:  
                return image_urls, image_comment  
            else:  
                print('Bing image generation failed. Falling back to OpenAI.')  
        except Exception as e:  
            print(f'Image generation from Bing failed: {type(e)}')  
            print(type(e), e)  
            print('Falling back to OpenAI.')  
    else:  
        print('Bing Cookie is not set. Using OpenAI to generate Image.')  
      
    image_url, image_comment = make_pic_from_openai(sentence)  
    return [image_url], image_comment  

def make_poem():  
    print(f'Start making poem...')  
    sentence, poem = get_poem()  
    sentence_processed = sentence.replace(  
        "，", " ").replace("。", " ").replace(".", " ")  
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

def make_quota(tian_api_key):  # 假设你已经有了这个函数的实现  
    pass  

def main():  
    print("Main started...")  
    MESSAGES.append(make_weather(WEATHER_CITY_CODE))  
    image_urls, poem_message = make_poem()  
    MESSAGES.append(poem_message)  
  
    if TIAN_API_KEY is not None and TIAN_API_KEY != '':  
        MESSAGES.append(make_quota(TIAN_API_KEY))  
    if BING_COOKIE:  
        print('Bing Cookie is set. Using Bing to generate Image.')  
    else:  
        print('Bing Cookie is not set. Using OpenAI to generate Image.')  
      
    full_message = make_message(MESSAGES)  
    print("Message constructed...")  
    print()  
    print("Sending to Telegram...")  
    r_json = send_tg_message(tg_bot_token=TG_BOT_TOKEN,  
                             tg_chat_id=TG_CHAT_ID, message=full_message, images=image_urls)  
    print(r_json)  

if __name__ == "__main__":  
    main()
