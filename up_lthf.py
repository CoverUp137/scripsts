"""
name: 联通套餐详情
cron: 1 21 * * *

"""

#抓包--打开联通营业厅app--首页点击剩余话费或者剩余流量页面
# 复制完整的CK，一般是MUT_S开头的，完整ck！！！很长
# ck失效时间未知，没测试


# 目前已知问题:
# 1: 在同一个手机上通一个app抓包的ck，如果再切换另外的号抓，前者的ck会失效


# 解决办法
# 1: 尝试修改设备id看看，ck里面 devicedId就是
# 2: 元萝卜多开联通营业厅app抓包
# 3: 一个手机一个app一个账号（最有效）

import requests
import os
import re
import sys
from typing import Optional, List, Dict

class UnicomQuery:
    BASE_HEADERS = {
        "Host": "m.client.10010.com",
        "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36 EdgA/135.0.0.0",
        "content-type": "application/x-www-form-urlencoded",
        "x-requested-with": "com.sinovatech.unicom.ui",
        "origin": "https://img.client.10010.com"
    }
    
    COMMON_PARAMS = {
        "duanlianjieabc": "",
        "channelCode": "",
        "serviceType": "",
        "saleChannel": "",
        "externalSources": "",
        "contactCode": "",
        "language": "chinese"
    }

    def __init__(self, cookie: str = None, phone: str = None):
        self.session = requests.Session()
        self.cookies = cookie
        self.phone = phone or self._extract_phone_from_cookie()
        self.notify = self._load_notify()

    def _load_notify(self):
        try:
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from sendNotify import send
            return send
        except Exception:
            return None

    def _extract_phone_from_cookie(self) -> str:
        match = re.search(r'c_mobile=(\d{3})(\d{4})(\d{4})', self.cookies or "")
        return f"{match.group(1)}****{match.group(3)}" if match else "未知号码"

    def _make_request(self, url: str, extra_params: Dict = None) -> Optional[Dict]:
        try:
            headers = {**self.BASE_HEADERS, "Cookie": self.cookies}
            params = {**self.COMMON_PARAMS, **(extra_params or {})}
            response = self.session.post(url, headers=headers, data=params)
            return response.json()
        except Exception:
            return None

    def query_balance(self) -> str:
        result = self._make_request(
            "https://m.client.10010.com/servicequerybusiness/balancenew/accountBalancenew.htm",
            {"channel": "client"}
        )
        
        if not result:
            return "❌ 话费查询失败"
            
        return "\n".join([
            f"🕒 查询时间: {result.get('queryTime', '未知')}",
            f"📱 手机号码: {self.phone}",
            f"💰 剩余话费: {result.get('curntbalancecust', '0.00')}元",
            f"💳 本月存入话费: {result.get('freePayFeeTotal', '0.00')}元",
            f"💸 本月已消费: {result.get('realfeecustnew', '0.00')}元",
            f"📆 上个月结转话费: {result.get('newCarryForwardFromLastMonth', '0.00')}元"
        ])

    def query_traffic(self) -> str:
        result = self._make_request(
            "https://m.client.10010.com/servicequerybusiness/operationservice/queryOcsPackageFlowLeftContentRevisedInJune"
        )
        
        if not result:
            return "❌ 流量查询失败"
            
        traffic_info = []
        
        realname_result = self._make_request(
            "https://m.client.10010.com/servicebusiness/newOrdered/queryOrderRelationship"
        )
        if realname_result and realname_result.get("code") == "0000":
            if username := realname_result.get("data", {}).get("username"):
                traffic_info.append(f"👤 实名信息: {username}")
        
        if 'packageName' in result:
            traffic_info.append(f"📱 套餐名称: {result['packageName']}")
        
        if 'allUserFlow' in result:
            total_flow = self._format_flow(result['allUserFlow'])
            traffic_info.append(f"📊 总使用量: {total_flow}")
        
        if 'resources' in result:
            for resource in result['resources']:
                if resource['type'] == 'flow' and resource['details']:
                    traffic_info.append("\n📦 流量包明细:")
                    traffic_info.append("┌" + "─" * 20)
                    for detail in resource['details']:
                        if detail.get('hide', False) or not detail.get('feePolicyName'):
                            continue
                            
                        package_name = detail['feePolicyName']
                        flow_type = {
                            "1": "📡 通用流量",
                            "2": "🎯 定向流量",
                            "3": "🔮 其他流量"
                        }.get(detail.get('flowType'), "❓ 未知类型")
                        
                        total = self._format_flow(detail.get('total', '0'))
                        used = self._format_flow(detail.get('use', '0'))
                        remain = self._format_flow(detail.get('remain', '0'))
                        percent = detail.get('usedPercent', '0')
                        end_date = "长期有效" if detail.get('endDate') == "长期有效" else detail.get('endDate', '未知')
                        
                        traffic_info.extend([
                            f"│ {flow_type} | {package_name}",
                            f"│ ├─ 总量: {total}",
                            f"│ ├─ 已用: {used} ({percent}%)",
                            f"│ ├─ 剩余: {remain}",
                            f"│ └─ 有效期: {end_date}",
                            "├" + "─" * 20
                        ])
                    if traffic_info[-1].startswith("├"):
                        traffic_info[-1] = "└" + "─" * 20
        
        return "\n".join(traffic_info) if traffic_info else "暂无流量明细"

    def query_ordered_services(self) -> str:
        result = self._make_request(
            "https://m.client.10010.com/servicebusiness/newOrdered/queryOrderRelationship"
        )
        
        if not result or result.get("code") != "0000":
            return "❌ 已订购业务查询失败"
        
        service_info = []
        other_services = list({
            p["productName"].strip() 
            for p in result.get("data", {}).get("otherProductInfo", []) 
            if p.get("productName")
        })
        
        if other_services:
            service_info.append("📋 已订购业务明细:")
            service_info.append("┌" + "─" * 20)
            for i, s in enumerate(other_services[:15], 1):
                service_info.append(f"│ {i}️⃣ {s}")
            service_info.append("└" + "─" * 20)
        
        return "\n".join(service_info) if other_services else "暂无其他业务"

    def _format_flow(self, flow_str: str) -> str:
        try:
            flow = float(flow_str)
            if flow >= 1024 * 1024:  # TB
                return f"{flow/(1024*1024):.2f}TB"
            elif flow >= 1024:  # GB
                return f"{flow/1024:.2f}GB"
            else:  # MB
                return f"{flow:.2f}MB"
        except ValueError:
            return "0.00MB"

    def send_notification(self, title: str, content: str):
        if self.notify:
            self.notify(title, content)
        else:
            print(f"\n{title}\n{content}\n")

def main():
    cookies_str = os.getenv("UNICOM_COOKIE", "")
    if not cookies_str:
        print("❌ 错误：未设置UNICOM_COOKIE环境变量")
        return
    
    cookies_list = [c.strip() for c in cookies_str.split("#" if "#" in cookies_str else "\n\n") if c.strip()]
    
    if not cookies_list:
        print("❌ 错误：UNICOM_COOKIE中没有有效的Cookie")
        return
    
    for i, cookie in enumerate(cookies_list, 1):
        query = UnicomQuery(cookie=cookie)
        print(f"\n🔍 {'='*50} 正在查询第 {i} 个账号 ({query.phone}) {'='*50} 🔍")
        
        balance = query.query_balance()
        traffic = query.query_traffic()
        services = query.query_ordered_services()
        
        print(f"\n💳 话费查询结果:\n{balance}")
        print(f"\n📶 流量查询结果:\n{traffic}")
        if services != "暂无其他业务":
            print(f"\n{services}")
        
        query.send_notification(
            title=f"📱 联通账号{i}({query.phone})查询结果",
            content=f"【💳 话费信息】\n{balance}\n\n【📶 流量信息】\n{traffic}" + 
                   (f"\n\n{services}" if services != "暂无其他业务" else "")
        )
        
        print(f"\n✅ 第 {i} 个账号查询完成")

if __name__ == "__main__":
    main()
