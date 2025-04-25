"""
name: 携趣全自动更换ip
cron: */5 * * * *
"""
#代理用完后，ip自动切换列表中的下一个账号
import requests
import os
from datetime import datetime
import json
import time
import re

BASE_URL = "http://op.xiequ.cn"
ACCOUNTS = [
    {"uid": "账号1 uid", "ukey": "账号1 key", "remark": "备注"},
    {"uid": "账号2 uid", "ukey": "账号2 key", "remark": "备注2"},
     {"uid": "账号3 uid", "ukey": "账号3 key", "remark": "备注3"},
]

IP_FILE = "current_ip.txt"
MAX_RETRIES = 3
RETRY_DELAY = 2

def print_separator():
    print("\n" + "="*50)

def print_account_status(account, status):
    remark = account.get('remark', account['uid'])
    if status.get('has_free'):
        print(f"\n{remark}: [{status['package_name']}]")
        print(f"IP总数: {status['total_ips']} | 已用: {status['used_ips']} | 剩余: {status['remaining_ips']}")
        print(f"到期时间: {status['end_date']}")
        
        white_ips = get_white_ips(account)
        if white_ips:
            print(f"✅ 当前绑定IP: {', '.join(white_ips)}")
        else:
            print("⚠️ 当前未绑定IP")
    else:
        error_msg = status.get('error', '')
        if error_msg == "package_exhausted":
            print(f"\n{remark}: 🔴 套餐已用完")
        elif error_msg == "empty_response":
            print(f"\n{remark}: 🔴 套餐无效(可能已到期)")
        else:
            print(f"\n{remark}: 🔴 无有效免费套餐 ({error_msg})")

#获取ip的url列表，可写多个
def get_public_ip():
    services = [
        "https://ip.3322.net",
        "https://4.ipw.cn",
        "http://ip.010504.xyz"
    ]
    for service in services:
        try:
            if "json" in service:
                response = requests.get(service, timeout=5)
                return response.json().get('ip', '').strip()
            else:
                response = requests.get(service, timeout=5)
                return response.text.strip()
        except:
            continue
    print("❌ 获取公网IP失败")
    return None

def check_free_package(account):
    url = f"{BASE_URL}/ApiUser.aspx?act=suitdt&uid={account['uid']}&ukey={account['ukey']}"
    try:
        response = requests.get(url, timeout=10)
        response_text = response.text.strip()
        
        if re.match(r'^ERR#', response_text):
            return {
                "has_free": False,
                "error": "package_exhausted",
                "raw_response": response_text
            }
            
        if not response_text:
            return {
                "has_free": False,
                "error": "empty_response",
                "raw_response": response_text
            }
               
        data = response.json()
        if data.get("success", "false").lower() == "true":
            for item in data.get("data", []):
                if "免费套餐" in item.get("type", ""):
                    return {
                        "has_free": True,
                        "total_ips": int(item.get("num", 0)),
                        "used_ips": int(item.get("use", 0)),
                        "remaining_ips": int(item.get("num", 0)) - int(item.get("use", 0)),
                        "end_date": item.get("enddate", "未知"),
                        "package_name": item.get("type", "免费套餐"),
                        "raw_response": data
                    }
            return {"has_free": False, "error": "no_free_package", "raw_response": data}
        return {"has_free": False, "error": "api_failure", "raw_response": data}
    except json.JSONDecodeError:
        return {
            "has_free": False,
            "error": "invalid_json",
            "raw_response": response_text
        }
    except Exception as e:
        return {
            "has_free": False,
            "error": str(e),
            "raw_response": response_text if 'response_text' in locals() else ""
        }

def get_white_ips(account):
    url = f"{BASE_URL}/IpWhiteList.aspx?uid={account['uid']}&ukey={account['ukey']}&act=get"
    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            ips = response.text.strip()
            return [ip for ip in ips.splitlines() if ip] if ips else []
        except:
            time.sleep(RETRY_DELAY)
    print(f"❌ 获取白名单失败({account.get('remark')})")
    return []

def clear_white_ips(account):
    url = f"{BASE_URL}/IpWhiteList.aspx?uid={account['uid']}&ukey={account['ukey']}&act=del&ip=all"
    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return True
        except:
            time.sleep(RETRY_DELAY)
    print(f"❌ 清空白名单失败({account.get('remark')})")
    return False

def add_white_ip(account, ip):
    url = f"{BASE_URL}/IpWhiteList.aspx?uid={account['uid']}&ukey={account['ukey']}&act=add&ip={ip}"
    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return True
        except:
            time.sleep(RETRY_DELAY)
    print(f"❌ 添加白名单失败({account.get('remark')})")
    return False

def verify_ip_binding(account, ip, max_checks=5):
    for i in range(max_checks):
        white_ips = get_white_ips(account)
        if ip in white_ips:
            return True
        if i < max_checks - 1:
            time.sleep(3)
    return False

def save_ip_to_file(ip):
    try:
        with open(IP_FILE, "w", encoding="utf-8") as f:
            f.write(ip)
    except:
        print("❌ 保存IP到文件失败")
def manage_ip_allocation(current_ip):
    print_separator()
    print("开始检查各账号状态...")
    
    for account in ACCOUNTS:
        status = check_free_package(account)
        print_account_status(account, status)
        
        if status.get('has_free') and status['remaining_ips'] > 0:
            white_ips = get_white_ips(account)
            if current_ip in white_ips:
                print(f"✅ IP {current_ip} 已经绑定到有效账号 {account.get('remark')}，无需操作")
                return True
    
    print_separator()
    print("开始处理IP分配...")
    
    for account in ACCOUNTS:
        status = check_free_package(account)
        if status.get('error') == "package_exhausted":
            print(f"检测到账号 {account.get('remark')} 套餐已用完，正在检查白名单...")
            white_ips = get_white_ips(account)
            if white_ips:
                print(f"发现已用完套餐账号 {account.get('remark')} 有绑定IP: {white_ips}")
                if clear_white_ips(account):
                    print(f"✅ 已清理 {account.get('remark')} 的白名单IP")
                else:
                    print(f"❌ 清理 {account.get('remark')} 白名单失败")
    
    for account in ACCOUNTS:
        status = check_free_package(account)
        if status.get('has_free') and status['remaining_ips'] > 0:
            print(f"尝试绑定到账号 {account.get('remark')}...")
            
            
            if not clear_white_ips(account):
                print(f"❌ 清空白名单失败，跳过此账号")
                continue
                
            if add_white_ip(account, current_ip):
                if verify_ip_binding(account, current_ip):
                    print(f"✅ 成功绑定IP到 {account.get('remark')}")
                    return True
                else:
                    print(f"❌ 验证绑定失败")
            else:
                print(f"❌ 添加IP失败")
    
    print("❌ 没有找到合适的账号绑定IP")
    return False
def main():
    print(f"\n携趣多账号自动管理")
    print(f"## 开始执行... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    current_ip = get_public_ip()
    if not current_ip:
        print("❌ 获取IP失败，脚本结束")
        return
    
    print(f"\n=== 当前公网IP: {current_ip} ===")
    save_ip_to_file(current_ip)
    
    if manage_ip_allocation(current_ip):
        print_separator()
        print("=== 最终状态汇总 ===")
        for account in ACCOUNTS:
            status = check_free_package(account)
            print_account_status(account, status)
    else:
        print("❌ IP分配过程中出现错误")
    
    print("\n脚本执行完成")

if __name__ == "__main__":
    main()