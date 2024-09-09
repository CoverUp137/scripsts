import os
import requests
from notify import send
# 视权益脚本
# 青龙变量: sqyck
# 自行抓包: 微信公众号---视权益---我的账户。 抓authorization的值
# authorization 可能时效性

authorization = os.getenv('sqyck')

#自定义UA
user_agent = 'Mozilla/5.0 (Linux; Android 4.2.1; M040 Build/JOP40D) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.59 Mobile Safari/537.36'

# 多个链接的列表
URLS = [
    "https://api.shiquanyi.cn/recovery/dccard/threeCardListJieByTagId?id=6&two_card_id=31", #腾讯
    "https://api.shiquanyi.cn/recovery/dccard/threeCardListJieByTagId?id=4&two_card_id=27", #爱奇艺
    "https://api.shiquanyi.cn/recovery/dccard/threeCardListJieByTagId?id=5&two_card_id=44" #优酷
    # 可以继续添加其他链接
]

def fetch_data(url):
    headers = {
        "Host": "api.shiquanyi.cn",
        "accept": "application/json, text/plain, */*",
        "authorization": authorization,
        "user-agent": user_agent,
        "origin": "https://m.shiquanyi.cn",
        "x-requested-with": "com.tencent.mm",
        "sec-fetch-site": "same-site",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://m.shiquanyi.cn/",
        "accept-encoding": "gzip, deflate",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    response = requests.get(url, headers=headers)
    return response.json()

def format_data(data):
    formatted_results = []
    for item in data.get('data', []):
        name = item.get('full_name', '')
        price = item.get('jd_price', 0) / 100  
        count = item.get('count', 0)
        formatted_results.append(f"《{name}》:   {price}元 {count}单")
    
    return "\n".join(formatted_results)

def main():
    all_formatted_outputs = []
    for url in URLS:
        data = fetch_data(url)
        formatted_output = format_data(data)
        all_formatted_outputs.append(formatted_output)
    
    
    final_output = "\n\n".join(all_formatted_outputs)
    send("视权益价格通知", final_output) 

if __name__ == "__main__":
    main()
