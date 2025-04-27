"""
name: 携趣全自动更换ip
cron: */5 * * * *
"""
#代理用完后，ip自动切换列表中的下一个账号
#如家宽ip变更，则继续绑定之前的套餐，只有套餐剩余ip低于50个，或者用完，白名单ip才会更换到下个套餐

import requests
import os
from datetime import datetime
import json
import time
import re

BASE_URL = "http://op.xiequ.cn"
ACCOUNTS = [
    {"uid": "账号1", "ukey": "账号1", "remark": "备注"}, 
    {"uid": "账号2", "ukey": "账号2", "remark": "备注2"},

]

IP_FILE = "xiequ_ip.txt"
MAX_RETRIES = 3
RETRY_DELAY = 2
MIN_REMAINING_IPS = 50  # 自定义剩余IP阈值，小于这个阀值则更换白名单ip到其他套餐

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

def get_public_ip():
    services = [
        "https://ip.3322.net",
        "https://4.ipw.cn"
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

def find_current_binding_account(current_ip):
    """查找当前IP绑定的账号"""
    for account in ACCOUNTS:
        white_ips = get_white_ips(account)
        if current_ip in white_ips:
            return account
    return None

def manage_ip_allocation(current_ip):
    print_separator()
    print("开始检查各账号状态...")
    
    current_binding = find_current_binding_account(current_ip)
    
    original_binding = None
    for account in ACCOUNTS:
        white_ips = get_white_ips(account)
        if white_ips:  
            original_binding = account
            break
    

    target_account = current_binding if current_binding else original_binding
    
    if target_account:
        status = check_free_package(target_account)   
        if status.get('has_free') and status['remaining_ips'] >= MIN_REMAINING_IPS:
            if not current_binding or current_binding != target_account:
                print(f"🔄 正在恢复绑定到原账号 {target_account.get('remark')}...")
                if clear_white_ips(target_account) and add_white_ip(target_account, current_ip):
                    print(f"✅ 已恢复绑定到 {target_account.get('remark')}")
                    return True
            else:
                print(f"✅ 当前IP仍绑定在有效账号 {target_account.get('remark')}，剩余IP充足({status['remaining_ips']})")
                return True
        else:
            print(f"⚠️ 原绑定账号 {target_account.get('remark')} 剩余IP不足({status.get('remaining_ips', 0)})，准备切换...")
    
   
    best_account = None
    max_remaining = 0
    
    for account in ACCOUNTS:
        status = check_free_package(account)
        if status.get('has_free') and status['remaining_ips'] >= MIN_REMAINING_IPS:
            if status['remaining_ips'] > max_remaining:
                max_remaining = status['remaining_ips']
                best_account = account
    
   
    if best_account is None:
        for account in ACCOUNTS:
            status = check_free_package(account)
            if status.get('has_free'):
                if status['remaining_ips'] > max_remaining:
                    max_remaining = status['remaining_ips']
                    best_account = account
    
    if not best_account:
        print("❌ 没有找到任何有效的套餐账号")
        return False
    
    if target_account and best_account != target_account:
        print(f"准备从账号 {target_account.get('remark')} 切换到 {best_account.get('remark')}...")
        if not clear_white_ips(target_account):
            print(f"❌ 清理原账号白名单失败")
            return False
    
    print(f"尝试绑定到账号 {best_account.get('remark')}...")
    
    if not clear_white_ips(best_account):
        print(f"❌ 清空白名单失败，跳过此账号")
        return False
        
    if add_white_ip(best_account, current_ip):
        if verify_ip_binding(best_account, current_ip):
            print(f"✅ 成功绑定IP到 {best_account.get('remark')}")
            return True
        else:
            print(f"❌ 验证绑定失败")
    else:
        print(f"❌ 添加IP失败")
    
    return False

def main():
    print(f"\n携趣多账号自动管理")
    print(f"## 开始执行... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"最小剩余IP阈值: {MIN_REMAINING_IPS}")
    
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