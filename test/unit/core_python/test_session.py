"""
@author: cunyue
@file: test_session.py
@time: 2025/9/9 15:12
@description: $END$
"""

import os
import pytest
import responses
from responses import registries

from swanlab.core_python import create_session
from swanlab.package import get_package_version


@pytest.mark.parametrize("url", ["https://api.example.com/retry", "http://api.example.com/retry"])
@responses.activate(registry=registries.OrderedRegistry)
def test_retry(url):
    """
    测试重试机制
    """

    [responses.add(responses.GET, url, body="Error", status=500) for _ in range(5)]
    responses.add(responses.GET, url, body="Success", status=200)
    s = create_session()
    resp = s.get(url)
    assert resp.text == "Success"
    assert len(responses.calls) == 6


@responses.activate(registry=registries.OrderedRegistry)
def test_session_headers():
    """
    测试会话是否包含正确的自定义请求头
    """
    # 1. 准备测试数据
    test_url = "https://api.example.com/test"
    expected_sdk_version = get_package_version()

    # 2. 模拟响应 - 捕获请求头
    captured_headers = {}

    def request_callback(request):
        # 捕获所有请求头
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return (200, {}, "OK")

    responses.add_callback(responses.GET, test_url, callback=request_callback)

    # 3. 创建会话并发送请求
    session = create_session()
    response = session.get(test_url)

    # 4. 验证
    assert response.status_code == 200

    # 验证自定义头存在且值正确
    assert "swanlab-sdk" in captured_headers
    assert captured_headers["swanlab-sdk"] == expected_sdk_version

    # 验证User-Agent等默认头也存在（可选）
    assert "User-Agent" in captured_headers

    # 打印所有捕获的请求头（调试用）
    print("\n捕获的请求头:", captured_headers)


@responses.activate(registry=registries.OrderedRegistry)
def test_header_merging():
    """
    测试请求级别headers与会话级别headers的合并
    """
    test_url = "https://api.example.com/merge"
    custom_header = {"X-Custom-Request-Header": "test-value"}

    captured_headers = {}

    def request_callback(request):
        nonlocal captured_headers
        captured_headers = dict(request.headers)
        return (200, {}, "OK")

    responses.add_callback(responses.GET, test_url, callback=request_callback)

    # 创建会话（自带swanlab-sdk头）
    session = create_session()

    # 发送带额外请求头的请求
    response = session.get(test_url, headers=custom_header)

    # 验证
    assert response.status_code == 200

    # 验证会话头依然存在
    assert "swanlab-sdk" in captured_headers

    # 验证请求级别头已添加
    assert "X-Custom-Request-Header" in captured_headers
    assert captured_headers["X-Custom-Request-Header"] == "test-value"

    # 验证合并而非覆盖（两个头都存在）
    assert len(captured_headers) >= 2


@responses.activate(registry=registries.OrderedRegistry)
def test_retry_with_custom_env_variables():
    """
    测试通过环境变量设置重试次数和backoff因子
    """
    # 保存原有环境变量值
    original_retry_total = os.environ.get("SWANLAB_RETRY_TOTAL")
    original_retry_backoff = os.environ.get("SWANLAB_RETRY_BACKOFF_FACTOR")
    
    try:
        # 设置环境变量
        os.environ["SWANLAB_RETRY_TOTAL"] = "3"
        os.environ["SWANLAB_RETRY_BACKOFF_FACTOR"] = "1.0"
        
        test_url = "https://api.example.com/retry-custom"
        
        # 添加3次失败的响应和1次成功的响应
        for _ in range(3):
            responses.add(responses.GET, test_url, body="Error", status=500)
        responses.add(responses.GET, test_url, body="Success", status=200)
        
        # 创建会话并请求
        s = create_session()
        resp = s.get(test_url)
        
        # 验证重试次数（3次失败 + 1次成功 = 4次调用）
        assert resp.text == "Success"
        assert len(responses.calls) == 4
    finally:
        # 恢复原有环境变量值
        if original_retry_total is None:
            os.environ.pop("SWANLAB_RETRY_TOTAL", None)
        else:
            os.environ["SWANLAB_RETRY_TOTAL"] = original_retry_total
        
        if original_retry_backoff is None:
            os.environ.pop("SWANLAB_RETRY_BACKOFF_FACTOR", None)
        else:
            os.environ["SWANLAB_RETRY_BACKOFF_FACTOR"] = original_retry_backoff


@responses.activate(registry=registries.OrderedRegistry)
def test_retry_default_values_without_env():
    """
    测试未设置环境变量时使用默认值（5次重试）
    """
    # 保存原有环境变量值
    original_retry_total = os.environ.get("SWANLAB_RETRY_TOTAL")
    original_retry_backoff = os.environ.get("SWANLAB_RETRY_BACKOFF_FACTOR")
    
    try:
        # 确保环境变量不存在
        os.environ.pop("SWANLAB_RETRY_TOTAL", None)
        os.environ.pop("SWANLAB_RETRY_BACKOFF_FACTOR", None)
        
        test_url = "https://api.example.com/retry-default"
        
        # 添加5次失败的响应和1次成功的响应
        for _ in range(5):
            responses.add(responses.GET, test_url, body="Error", status=500)
        responses.add(responses.GET, test_url, body="Success", status=200)
        
        # 创建会话并请求
        s = create_session()
        resp = s.get(test_url)
        
        # 验证默认重试次数（5次失败 + 1次成功 = 6次调用）
        assert resp.text == "Success"
        assert len(responses.calls) == 6
    finally:
        # 恢复原有环境变量值
        if original_retry_total is None:
            os.environ.pop("SWANLAB_RETRY_TOTAL", None)
        else:
            os.environ["SWANLAB_RETRY_TOTAL"] = original_retry_total
        
        if original_retry_backoff is None:
            os.environ.pop("SWANLAB_RETRY_BACKOFF_FACTOR", None)
        else:
            os.environ["SWANLAB_RETRY_BACKOFF_FACTOR"] = original_retry_backoff


@responses.activate(registry=registries.OrderedRegistry)
def test_retry_invalid_env_values_fallback_to_defaults():
    """
    测试当环境变量值无效时，使用默认值
    """
    # 保存原有环境变量值
    original_retry_total = os.environ.get("SWANLAB_RETRY_TOTAL")
    original_retry_backoff = os.environ.get("SWANLAB_RETRY_BACKOFF_FACTOR")
    
    try:
        # 设置无效的环境变量值
        os.environ["SWANLAB_RETRY_TOTAL"] = "invalid"
        os.environ["SWANLAB_RETRY_BACKOFF_FACTOR"] = "not_a_number"
        
        test_url = "https://api.example.com/retry-invalid"
        
        # 添加5次失败的响应和1次成功的响应（应该使用默认的5次重试）
        for _ in range(5):
            responses.add(responses.GET, test_url, body="Error", status=500)
        responses.add(responses.GET, test_url, body="Success", status=200)
        
        # 创建会话并请求
        s = create_session()
        resp = s.get(test_url)
        
        # 验证使用了默认重试次数（5次失败 + 1次成功 = 6次调用）
        assert resp.text == "Success"
        assert len(responses.calls) == 6
    finally:
        # 恢复原有环境变量值
        if original_retry_total is None:
            os.environ.pop("SWANLAB_RETRY_TOTAL", None)
        else:
            os.environ["SWANLAB_RETRY_TOTAL"] = original_retry_total
        
        if original_retry_backoff is None:
            os.environ.pop("SWANLAB_RETRY_BACKOFF_FACTOR", None)
        else:
            os.environ["SWANLAB_RETRY_BACKOFF_FACTOR"] = original_retry_backoff
