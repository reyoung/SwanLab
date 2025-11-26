"""
@author: cunyue
@file: session.py
@time: 2025/9/9 15:10
@description: 创建会话
"""

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from swanlab.env import SwanLabEnv
from swanlab.package import get_package_version

# 默认的重试配置
DEFAULT_RETRY_TOTAL = 5
DEFAULT_RETRY_BACKOFF_FACTOR = 0.5


def create_session() -> requests.Session:
    """
    创建一个带重试机制的会话
    重试次数和backoff因子可以通过环境变量SWANLAB_RETRY_TOTAL和SWANLAB_RETRY_BACKOFF_FACTOR设置
    :return: requests.Session
    """
    # 从环境变量读取重试配置，如果未设置或无效则使用默认值
    try:
        retry_total = int(os.getenv(SwanLabEnv.RETRY_TOTAL.value, str(DEFAULT_RETRY_TOTAL)))
        if retry_total < 0:
            retry_total = DEFAULT_RETRY_TOTAL
    except (ValueError, TypeError):
        retry_total = DEFAULT_RETRY_TOTAL
    
    try:
        retry_backoff_factor = float(os.getenv(SwanLabEnv.RETRY_BACKOFF_FACTOR.value, str(DEFAULT_RETRY_BACKOFF_FACTOR)))
        if retry_backoff_factor < 0:
            retry_backoff_factor = DEFAULT_RETRY_BACKOFF_FACTOR
    except (ValueError, TypeError):
        retry_backoff_factor = DEFAULT_RETRY_BACKOFF_FACTOR
    
    session = requests.Session()
    retry = Retry(
        total=retry_total,
        backoff_factor=retry_backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "PATCH"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["swanlab-sdk"] = get_package_version()
    return session
