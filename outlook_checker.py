import imaplib
import ssl
import time
from concurrent.futures import ThreadPoolExecutor


def check_single_account(email, password, timeout=10):
    """检测单个Outlook账号是否可登录"""
    try:
        # 创建SSL上下文
        context = ssl.create_default_context()

        # 连接Outlook IMAP服务器
        imap = imaplib.IMAP4_SSL('outlook.office365.com', 993, ssl_context=context)
        imap.login(email, password)
        imap.logout()
        return {'email': email, 'status': 'active', 'error': None}
    except imaplib.IMAP4.error as e:
        if 'Authentication failed' in str(e):
            return {'email': email, 'status': 'locked', 'error': '密码错误或账号锁定'}
        return {'email': email, 'status': 'banned', 'error': str(e)}
    except Exception as e:
        return {'email': email, 'status': 'error', 'error': str(e)}


def batch_check_accounts(accounts, max_workers=5):
    """批量检测，max_workers控制并发数（避免被微软封IP）"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for email, password in accounts:
            futures.append(executor.submit(check_single_account, email, password))
            time.sleep(0.5)  # 每个请求间隔0.5秒

        for future in futures:
            results.append(future.result())
    return results