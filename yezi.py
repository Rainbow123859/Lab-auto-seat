import requests
import logging
import time
import concurrent.futures
import sys
import os
from datetime import datetime, time as dt_time

# ============== 配置区域（根据你的抓包数据修改）===============
BASE_CONFIG = {
    "cookies": {
        "ASP.NET_SessionId": "qljak1tvqi2xve4cg50gi4ev",
        "cookie_unit_name": "%e6%b9%96%e5%8d%97%e5%86%9c%e4%b8%9a%e5%a4%a7%e5%ad%a6%e5%9b%be%e4%b9%a6%e9%a6%86",
        "cookie_come_app": "D935AE54952F16C1",
        "cookie_come_timestamp": "1762756864",
        "cookie_come_sno": "DAD084FF07CB0C55B865F4CC47A8D55BBE7AF5FCE39EA877",
        "dt_cookie_user_name_remember": "6C72C7227D4D5EEFBEEBC75F707B38B08AAABBE15EF81E84"
    },
    "latitude": "28.186214447021484",
    "longitude": "113.07843780517578",
    "checkin_url": "http://libseat.hunau.edu.cn/apim/seat/SeatDateHandler.ashx",
    "headers": {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.57(0x1800392a) NetType/WIFI Language/zh_CN",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://libseat.hunau.edu.cn/mobile/html/index.html?v=20240107",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    },
    "seat_url_template": "http://url.tolib.cn/ckindex.aspx?unitcode=hunau&sno={}"
}

# 要签到的座位号列表
SEAT_LIST = ["HNND04492", "HNND20479", "HNND20480", "HNND20477"]

# ============== 日志配置 ================
LOG_DIR = "logging"
os.makedirs(LOG_DIR, exist_ok=True)
current_date = datetime.now().strftime("%Y%m%d")
LOG_FILE = os.path.join(LOG_DIR, f"checkin_{current_date}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ============== 签到类 ================
class AutoCheckin:
    def __init__(self, config):
        self.session = requests.Session()
        self.config = config
        self.session.headers.update(config["headers"])
        self.session.cookies.update(config["cookies"])

    def checkin_seat(self, seat):
        seat_url = self.config["seat_url_template"].format(seat)
        payload = {
            "data_type": "scanSign",
            "seatno": seat_url,
            "latitude": self.config["latitude"],
            "longitude": self.config["longitude"]
        }

        try:
            response = self.session.post(
                self.config["checkin_url"],
                data=payload,
                timeout=10
            )
            logging.info("签到请求响应：%s", response.text)
            if response.status_code == 200 and "签到成功" in response.text:
                logging.info("✅ 座位 %s 签到成功！", seat)
                return True
            else:
                logging.error("❌ 座位 %s 签到失败：%s", seat, response.text)
                return False
        except Exception as e:
            logging.error("⚠️ 座位 %s 签到异常：%s", seat, str(e), exc_info=True)
            return False

# ============== 主程序 ================
if __name__ == "__main__":
    checkin = AutoCheckin(BASE_CONFIG)
    logging.info("程序已启动，等待签到时间窗口...")

    # 定义时间窗口（跨午夜）
    start_time = dt_time(0, 59, 0)
    end_time = dt_time(23, 29, 0)  # 次日的 00:40:00

    while True:
        now = datetime.now()
        current_time = now.time()

        if current_time >= start_time and current_time <= end_time:
            logging.info("🕒 进入签到时间窗口，开始并发尝试...")

            # 使用线程池并发发送签到请求
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(SEAT_LIST)) as executor:
                futures = [executor.submit(checkin.checkin_seat, seat) for seat in SEAT_LIST]

                # 等待所有签到请求完成
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            logging.info("🎉 成功签到座位")
                    except Exception as e:
                        logging.error("并发请求异常：%s", str(e), exc_info=True)

            # 如果一轮并发后没有成功，可以继续下一轮尝试
        else:
            # 在时间窗口前稍微等待
            time.sleep(30)
