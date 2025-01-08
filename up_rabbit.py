"""
name: 兔子反代更换
cron: 1 */5 * * *
# 代码抄来的
"""

import requests
import time

# 配置项
BASE_URL = "http://192.168.2.7:1234"  # 后台地址，最后不要带 "/"
USERNAME = "123456"  # 登录用户名
PASSWORD = "789846"  # 登录密码
PROXY_LIST = [
    "rabbit.cfyes.tech",
    "mr-orgin.1888866.xyz",
    "jd-orgin.1888866.xyz",
    "mr.118918.xyz",
    "host.257999.xyz",
    "log.madrabbit.eu.org",
    "fd.gp.mba:6379",
]

GLOBAL_LOCK = False

def login(base_url, username, password):
    url = f"{base_url}/admin/auth"
    try:
        response = requests.post(url, json={"username": username, "password": password}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("access_token")
    except requests.RequestException as e:
        print(f"登录失败: {e}")
        return None

def get_config(base_url, token):
    url = f"{base_url}/admin/GetConfig"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"获取配置失败: {e}")
        return None

def save_config(base_url, token, config):
    url = f"{base_url}/admin/SaveConfig"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.post(url, headers=headers, json=config, timeout=10)
        response.raise_for_status()
        print(f"配置保存成功: {response.json()}")
        return True
    except requests.RequestException as e:
        print(f"配置保存失败: {e}")
        return False


def test_proxy(proxy):
    url = f"http://{proxy}/enc/M"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get("message", {}).get("data") == "no data"
    except Exception as e:
        print(f"测试失败: {proxy}, 错误: {e}")
        return False


def replace_proxy(base_url, username, password, proxies):
    global GLOBAL_LOCK
    if GLOBAL_LOCK:
        print("另一个自动更换反代正在运行中")
        return
    GLOBAL_LOCK = True

    try:
        token = login(base_url, username, password)
        if not token:
            raise ValueError("登录失败")

        config = get_config(base_url, token)
        if not config:
            raise ValueError("无法获取配置")

        current_proxy = config.get("ServerHost", None)
        if current_proxy and current_proxy.startswith("http://"):
            current_proxy = current_proxy[7:]
        print(f"当前反代地址: {current_proxy if current_proxy else '无'}")

        start_index = proxies.index(current_proxy) if current_proxy in proxies else 0
        for i in range(len(proxies)):
            proxy = proxies[(start_index + i) % len(proxies)]
            if test_proxy(proxy):
                print(f"找到可用反代: {proxy}")
                config["ServerHost"] = proxy
                if save_config(base_url, token, config):
                    print(f"反代地址已更新为: {proxy}")
                return
        print("没有找到可用的反代地址")
    except Exception as e:
        print(f"更换反代出错: {e}")
    finally:
        GLOBAL_LOCK = False


if __name__ == "__main__":
    replace_proxy(BASE_URL, USERNAME, PASSWORD, PROXY_LIST)