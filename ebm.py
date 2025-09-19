import sys
import yaml
import time
import os
from datetime import datetime
from mail import send_email 
from sdk import get, post
from logger_utils import get_logger
from multiprocessing import Process

#macros
MONITOR_INTERVAL_SECONDS = 5
CONFIG_FILE = "config.yaml"
LOG_FILE = "stock_monitor.log"

logger = get_logger("EBMStock")

def load_config(config_file):
    """
    Loads email configuration and recipient list from a YAML file.
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['configs']
    except FileNotFoundError:
        logger.error(f"configuration file '{config_file}' not found.")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file '{config_file}': {e}")
        return None


def get_ebm_stocks(region_id, az_name, device_type):
    """
    Fetches EBM device stock information.
    Returns the stock dictionary or None if an error occurs.
    """
    query_params = {'regionID': region_id, 'azName': az_name}
    header_params = {'Content-Type': 'application/json;charset=UTF-8'}

    try:
        res = get("https://ebm-global.ctapi.ctyun.cn/v4/ebm/device-stock-list",
                  query_params=query_params,
                  header_params=header_params,
                  body_params={})

        response_data = res.json()

        if res.status_code == 200:
            results = response_data.get("returnObj", {}).get("results", [])
            if results:
                for s in results[0].get("stocks", []):
                    if s.get("deviceType") == device_type:
                        return s
                logger.info(f"Device type '{device_type}' not found in stocks list.")
                return None
            else:
                logger.info(f"No results in API response for {region_id}, {az_name}")
                return None
        else:
            error_message = response_data.get("message", "Unknown error")
            logger.error(f"Stock API access failed. Status: {res.status_code}, Message: {error_message}")
            return None
    except Exception as e:
        logger.exception(f"Exception while accessing EBM Stock API: {e}")
        return None


def monitor_stock(stock, receiver_emails):
    """
    Monitors EBM stocks and sends email notifications on changes or errors.
    """
    region_id = stock.get('region_id')
    az_name = stock.get('az_name')
    device_type = stock.get('device_type')
    info = stock.get('info')

    last_available_stock = -1  # Initialize with invalid value
    last_api_ok = -1
    if not region_id or not az_name or not device_type or not info:
        logger.error("Invalid stock data. Please check the input data.")
        return
    while True:
        now = datetime.now()
        current_stock = get_ebm_stocks(region_id, az_name, device_type)
        if current_stock is not None:
            available = current_stock.get("available")
            #logger.info(f"Current stock data: {current_stock}")
            if available != last_available_stock:
                title = f"【提醒】{info}库存变化!"
                content = (
                    f"亲爱的同事：\n\n"
                    f"{info}库存发生了变化，请及时关注。\n\n"
                    f"📊 上次可用库存: {last_available_stock if last_available_stock != -1 else '无记录'} 台\n"
                    f"📊 当前可用库存: {available} 台\n\n"
                    f"⏰ 监控时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"此致，\n库存监控系统"
                )
                if last_available_stock == -1:
                    logger.info(f"进程启动成功，不发送邮件！")
                else:
                    send_email(receiver_emails, info, title, content)
                    logger.info(f"Notification email sent: {content}")
                last_available_stock = available
                last_api_ok = 1
            else:
                pass
        else:
            title = f"【异常】{info}库存查询失败!"
            content = (
                f"亲爱的同事:\n\n"
                f"{info}库存查询失败，可能是 API 服务异常或网络故障，请尽快检查。\n\n"
                f"⏰ 失败时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"此致，\n库存监控系统"
            )
            if last_api_ok == 1:
                send_email(receiver_emails, info, title, content)
            logger.error("Error email sent due to stock API failure.")
        time.sleep(MONITOR_INTERVAL_SECONDS)

def main():
    logger.info("Starting EBM Monitor...")
    logger.info(f"Loading config from {CONFIG_FILE}...")
    CONF = load_config(CONFIG_FILE)
    monitor_stocks = CONF.get("resources", [])
    receiver_emails = CONF.get("mails", [])
    if not monitor_stocks:
        logger.error("No resources found in config.")
        sys.exit(1)
    if not receiver_emails:
        logger.error("No email addresses found in config.")
        sys.exit(1)

    # Start monitoring
    processes = []
    for stock in monitor_stocks:
        p = Process(target=monitor_stock, args=(stock, receiver_emails))
        p.start()
        processes.append(p)
    # Wait for all processes to finish
    logger.info(f"Starting {len(processes)} processes to monitor stocks...")
    for p in processes:
        p.join()
    logger.info("All processes finished.")

if __name__ == "__main__":
    main()
