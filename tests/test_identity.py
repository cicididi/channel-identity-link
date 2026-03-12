#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨渠道身份关联 - 单元测试
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 导入被测试模块
from link-identity import (
    IdentityManager, Config, BindingCode, Channel, User,
    generate_binding_code, verify_identity
)


class TestBindingCode(unittest.TestCase):
    """绑定码测试"""
    
    def test_generate_code_format(self):
        """测试绑定码格式"""
        code = generate_binding_code("DAD")
        self.assertTrue(code.startswith("PANGTOU-"))
        parts = code.split('-')
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(parts[2]), 6)  # 6 位随机码
    
    def test_code_expiry(self):
        """测试绑定码过期"""
        code = BindingCode(
            code="TEST-CODE",
            channel_platform="feishu",
            channel_id="test123",
            user_name="Test",
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            status="pending"
        )
        self.assertTrue(code.is_expired())


class TestIdentityManager(unittest.TestCase):
    """身份管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config = Config(
            workspace_dir=self.test_dir,
            identity_dir=self.test_dir / "identity",
            log_file=self.test_dir / "logs" / "test.log"
        )
        self.manager = IdentityManager(self.config)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.test_dir)
    
    def test_create_binding_request(self):
        """测试创建绑定请求"""
        result = self.manager.create_binding_request(
            "feishu",
            "test_channel_123",
            "测试用户"
        )
        
        self.assertTrue(result['success'])
        self.assertIn('binding_code', result)
        self.assertIn('expires_at', result)
    
    def test_confirm_binding(self):
        """测试确认绑定"""
        # 先生成绑定请求
        create_result = self.manager.create_binding_request(
            "feishu",
            "new_channel_456",
            "爸爸"
        )
        
        # 确认绑定
        confirm_result = self.manager.confirm_binding(
            create_result['binding_code'],
            "main_channel_789"
        )
        
        self.assertTrue(confirm_result['success'])
        self.assertEqual(confirm_result['user_name'], "爸爸")
    
    def test_verify_identity(self):
        """测试验证身份"""
        # 先绑定
        create_result = self.manager.create_binding_request(
            "wecom",
            "verify_test_123",
            "验证用户"
        )
        self.manager.confirm_binding(
            create_result['binding_code'],
            "main_789"
        )
        
        # 验证
        verify_result = self.manager.verify_identity(
            "wecom",
            "verify_test_123"
        )
        
        self.assertTrue(verify_result['verified'])
        self.assertEqual(verify_result['user_name'], "验证用户")
    
    def test_revoke_binding(self):
        """测试解除绑定"""
        # 先绑定
        create_result = self.manager.create_binding_request(
            "telegram",
            "revoke_test",
            "测试"
        )
        self.manager.confirm_binding(
            create_result['binding_code'],
            "main_123"
        )
        
        # 解除
        revoke_result = self.manager.revoke_binding(
            "telegram",
            "revoke_test"
        )
        
        self.assertTrue(revoke_result['success'])
    
    def test_cleanup_expired_codes(self):
        """测试清理过期绑定码"""
        # 创建过期绑定码
        codes_data = {
            "codes": {
                "EXPIRED-CODE": {
                    "code": "EXPIRED-CODE",
                    "channel_platform": "feishu",
                    "channel_id": "test",
                    "user_name": "Test",
                    "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "expires_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                    "status": "pending"
                }
            }
        }
        
        # 清理
        cleaned = self.manager._cleanup_expired_codes(codes_data)
        
        # 应该被清理掉
        self.assertEqual(len(cleaned['codes']), 0)


if __name__ == '__main__':
    unittest.main()
