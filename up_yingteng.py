import time
import requests
from bs4 import BeautifulSoup
from notify import send  
# 影腾 流量信息推送
# 抓包微信公众号 影腾YIMTURM-----星彬卡
# 抓取 ACCESS_TOKEN , INFO_SN , OPEN_ID , REFRESH_TOKEN , gdt_fp 这5个值填到脚本下方。

credentials_list = [#账号1
{
        "ACCESS_TOKEN": "",
        "INFO_SN": "",
        "OPEN_ID": "",
        "REFRESH_TOKEN": "",
        "gdt_fp": "",
    },#下面账号2
    {
        "ACCESS_TOKEN": "",
        "INFO_SN": "",
        "OPEN_ID": "",
        "REFRESH_TOKEN": "",
        "gdt_fp": "",
    }
    # 以此类推添加更多
]

all_output_messages = []

for credentials in credentials_list:
    access_token = credentials["ACCESS_TOKEN"]
    info_sn = credentials["INFO_SN"]
    open_id = credentials["OPEN_ID"]
    refresh_token = credentials["REFRESH_TOKEN"]
    gdt_fp = credentials["gdt_fp"]

    
    headers = {
        "Host": "cloud.bs-iot.com",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/wxpic,image/tpg,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "X-Requested-With": "com.tencent.mm",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": (
            f"REFRESH_TOKEN={refresh_token}; "
            f"OPEN_ID={open_id}; "
            f"INFO_SN={info_sn}; "
            f"ACCESS_TOKEN={access_token}; "
            f"gdt_fp={gdt_fp}"
        )
    }

    url = "https://cloud.bs-iot.com/aurora"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        try:
            recharge_number = soup.find(string="充值号：").find_next().text.strip()
            
            def mask_recharge_number(number):
                if len(number) >= 14:
                    return number[:4] + "*" * (len(number) - 8) + number[-4:]
                return number 
            
            recharge_number_masked = mask_recharge_number(recharge_number)
            
            real_name_status = soup.find(string="实名状态：").find_next().text.strip()
            current_package = soup.find(string="当前套餐：").find_next().text.strip()
            valid_period = soup.find(string="有效期：").find_next().text.strip()

            package_used_elem = soup.find(string="套餐已用量").find_previous("div", class_="ordinal")
            package_remaining_elem = soup.find(string="套餐剩余量").find_previous("div", class_="ordinal")
            remaining_duration_elem = soup.find(string="剩余时长").find_previous("div", class_="ordinal")

            package_used = package_used_elem.text.strip() if package_used_elem else "未找到"
            package_remaining = package_remaining_elem.text.strip() if package_remaining_elem else "未找到"
            remaining_duration = remaining_duration_elem.text.strip() if remaining_duration_elem else "未找到"

            output_message = (
                f"📱充值号: {recharge_number_masked}\n"
                f"👮实名状态: {real_name_status}\n"
                f"⏳当前套餐: {current_package}\n"
                f"⏰有效期: {valid_period}\n"
                f"⌛️套餐已用量: {package_used}\n"
                f"⌛️套餐剩余量: {package_remaining}\n"
                f"🔋剩余时长: {remaining_duration}\n\n"
            )

            all_output_messages.append(output_message)

        except Exception as e:
            print(f"提取信息时出错: {e}")
    else:
        print(f"请求失败，状态码: {response.status_code}")
        
    time.sleep(3)

final_output_message = "\n".join(all_output_messages)

if final_output_message:
    send("影腾套餐信息", final_output_message)
else:
    print("没有获取到有效的账号信息。")