"""
cron: */10 * * * *
new Env('妖火新帖推送');
"""
# 妖火新贴推送
# 变量: yhck
# 使用alook浏览器登录yaohuo.me然后开发者工具---cookies拷贝全部

import requests
from bs4 import BeautifulSoup
from notify import send
import os

yaohuo = os.getenv('yhck')

URL = "https://yaohuo.me/bbs/book_list.aspx?gettotal=2024&action=new"

HEADERS = {
    "Host": "yaohuo.me",
    "sec-ch-ua": "\"Chromium\";v=\"118\", \"Android WebView\";v=\"118\", \"Not=A?Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": "\"Android\"",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "x-requested-with": "XBrowser",
    "sec-fetch-site": "none",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "referer": "https://yaohuo.me/bbs/",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cookie": yaohuo
}

def extract_posts(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    posts = []
    
    
    for div in soup.find_all('div', class_='listdata'):
        title_tag = div.find('a', class_='topic-link')
        if title_tag:
            title = title_tag.get_text().strip()  
            link = title_tag['href']  
            posts.append({
                'title': title,
                'link': f"https://yaohuo.me{link}"
            })
    return posts

def load_sent_links(file_path):
    try:
        with open(file_path, 'r') as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def save_sent_links(file_path, links):
    with open(file_path, 'a') as f:
        for link in links:
            f.write(f"{link}\n")

def main():
    sent_links_file = "yaohuo.txt"
    sent_links = load_sent_links(sent_links_file) 
    
    response = requests.get(URL, headers=HEADERS)
    
    if response.status_code == 200:
        posts = extract_posts(response.text)
        
        new_posts = [post for post in posts if post['link'] not in sent_links]
        
        if new_posts:
            message_lines = ["====== 妖火最新帖子 ======"]
            for idx, post in enumerate(new_posts, 1):
                message_lines.append(f"【{post['title']}】\n   链接: {post['link']}\n")
            message_lines.append("======================")
            
            message = "\n".join(message_lines)
            send("妖火最新帖子", message)
            
            save_sent_links(sent_links_file, [post['link'] for post in new_posts])
    else:
        send("请求失败", f"状态码: {response.status_code}")

if __name__ == "__main__":
    main()