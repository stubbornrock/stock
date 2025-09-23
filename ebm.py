import sys
import yaml
import time
import random
import os
from datetime import datetime
from mail import send_email 
from sdk import get, post
from logger_utils import get_logger
from multiprocessing import Process

#macros
MONITOR_INTERVAL_SECONDS = 10
CONFIG_FILE = "config.yaml"
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
    # 获取资源信息
    region_id = stock.get('region_id')
    az_name = stock.get('az_name')
    device_type = stock.get('device_type')
    resource_name = stock.get('resource_name')
    logger.info(f"Monitoring {resource_name}-{device_type} in {region_id}, {az_name}")

    # 初始化变量
    last_available_stock = -1 #库存初始化
    last_api_ok = True

    # API错误计数
    ERROR_THRESHOLD = 3
    api_error_count = 0

    if not region_id or not az_name or not device_type or not resource_name:
        logger.error("Invalid stock data. Please check the input data.")
        return

    while True:
        now = datetime.now()
        current_stock = get_ebm_stocks(region_id, az_name, device_type)
        if current_stock is not None:
            # API调用成功

            # 如果之前是失败的，则发送恢复邮件
            if not last_api_ok: 
                title = f"【恢复】{resource_name}库存查询服务恢复!"
                content = (
                    f"亲爱的同事：\n\n"
                    f"{resource_name}库存查询服务已从故障中恢复。请继续关注。\n\n"
                    f"⏰ 恢复时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"此致，\n库存监控系统"
                )
                send_email(receiver_emails, resource_name, title, content)
                logger.info("Email: 恢复邮件发送成功！")

            # 成功，重置错误计数
            api_error_count = 0
            last_api_ok = True

            # 获取可用库存
            available = current_stock.get("available")
            logger.info(f"Current stock data: {current_stock}")
            if available != last_available_stock:
                title = f"【提醒】{resource_name}库存变化!"
                content = (
                    f"亲爱的同事：\n\n"
                    f"{resource_name}库存发生了变化，请及时关注。\n\n"
                    f"📊 上次可用库存: {last_available_stock if last_available_stock != -1 else '无记录'} 台\n"
                    f"📊 当前可用库存: {available} 台\n"
                    f"⏰ 监控时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"此致，\n库存监控系统"
                )
                # 发送邮件
                if last_available_stock == -1:
                    logger.info(f"Email: 库存监控进程启动成功，不发送邮件！")
                else:
                    send_email(receiver_emails, resource_name, title, content)
                    logger.info(f"Email: 库存变化邮件发送成功： {content}")
                last_available_stock = available
            else:
                # 没有变化
                pass
        else:
            # API调用失败
            api_error_count += 1
            logger.error(f"Stock API error count: {api_error_count}")

            if api_error_count == ERROR_THRESHOLD:
                logger.error(f"Stock API error count exceeded threshold ({ERROR_THRESHOLD}). Exiting...")
                title = f"【异常】{resource_name} 库存查询服务失败!"
                content = (
                    f"亲爱的同事:\n\n"
                    f"{resource_name}库存查询失败，可能是 API 服务异常或网络故障，已经连续失败{ERROR_THRESHOLD}次 请尽快检查。\n\n"
                    f"⏰ 失败时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"此致，\n库存监控系统"
                )
                # 发送邮件, EBM库存查询失败了
                if last_api_ok == True:
                    send_email(receiver_emails, resource_name, title, content)
                logger.error(f"Email: sent due to stock API failure.")
            elif api_error_count > ERROR_THRESHOLD:
                # API持续错误，持续失败，不再重复发送告警，只记录日志
                logger.error(f"Stock API error count: {api_error_count}")
            else:
                # 错误计数小于阈值，不发送邮件
                pass
            last_api_ok = False
            last_available_stock = -1
        #time.sleep(MONITOR_INTERVAL_SECONDS)
        time.sleep(random.uniform(MONITOR_INTERVAL_SECONDS*0.5, MONITOR_INTERVAL_SECONDS*1.5))

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