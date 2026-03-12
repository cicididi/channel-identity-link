#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨渠道身份关联 - 主脚本
处理绑定请求、生成绑定码、验证身份
"""

import os
import sys
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

# 配置
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
IDENTITY_DIR = WORKSPACE_DIR / "identity"
LINKED_CHANNELS_FILE = IDENTITY_DIR / "linked-channels.json"
BINDING_CODES_FILE = IDITY_DIR / "binding-codes.json"

# 绑定码有效期（分钟）
BINDING_CODE_EXPIRY_MINUTES = 30


def ensure_identity_dir():
    """确保身份目录存在"""
    IDENTITY_DIR.mkdir(parents=True, exist_ok=True)


def load_linked_channels():
    """加载已绑定的渠道"""
    if not LINKED_CHANNELS_FILE.exists():
        return {"users": [], "version": "1.0"}
    
    with open(LINKED_CHANNELS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_linked_channels(data):
    """保存已绑定的渠道"""
    ensure_identity_dir()
    with open(LINKED_CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_binding_codes():
    """加载待确认的绑定码"""
    if not BINDING_CODES_FILE.exists():
        return {"codes": {}}
    
    with open(BINDING_CODES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_binding_codes(data):
    """保存待确认的绑定码"""
    ensure_identity_dir()
    with open(BINDING_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_binding_code(user_name="DAD"):
    """
    生成绑定码
    格式：PANGTOU-{NAME}-{随机 4 位}
    """
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    name_short = user_name.upper()[:8]  # 限制长度
    return f"PANGTOU-{name_short}-{random_suffix}"


def create_binding_request(channel_platform, channel_id, user_name="用户"):
    """
    创建绑定请求
    
    Args:
        channel_platform: 渠道平台 (feishu, wecom, telegram, etc.)
        channel_id: 渠道用户 ID
        user_name: 用户名称
    
    Returns:
        dict: 绑定请求信息
    """
    ensure_identity_dir()
    
    binding_code = generate_binding_code(user_name)
    expires_at = (datetime.now() + timedelta(minutes=BINDING_CODE_EXPIRY_MINUTES)).isoformat()
    
    codes_data = load_binding_codes()
    codes_data["codes"][binding_code] = {
        "channel_platform": channel_platform,
        "channel_id": channel_id,
        "user_name": user_name,
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "status": "pending"  # pending, confirmed, expired
    }
    
    save_binding_codes(codes_data)
    
    return {
        "binding_code": binding_code,
        "expires_at": expires_at,
        "message": f"""🔑 生成绑定码：**{binding_code}**

请在你的主渠道输入"确认绑定 {binding_code}"完成关联。

⏰ 有效期：{BINDING_CODE_EXPIRY_MINUTES} 分钟
📱 新渠道：{channel_platform}"""
    }


def confirm_binding(binding_code, confirmer_channel_id):
    """
    确认绑定
    
    Args:
        binding_code: 绑定码
        confirmer_channel_id: 确认者的渠道 ID
    
    Returns:
        dict: 绑定结果
    """
    codes_data = load_binding_codes()
    
    if binding_code not in codes_data["codes"]:
        return {
            "success": False,
            "message": "❌ 绑定码不存在"
        }
    
    code_info = codes_data["codes"][binding_code]
    
    # 检查是否过期
    expires_at = datetime.fromisoformat(code_info["expires_at"])
    if datetime.now() > expires_at:
        code_info["status"] = "expired"
        save_binding_codes(codes_data)
        return {
            "success": False,
            "message": "❌ 绑定码已过期，请重新生成"
        }
    
    # 检查状态
    if code_info["status"] != "pending":
        return {
            "success": False,
            "message": f"❌ 绑定码状态：{code_info['status']}"
        }
    
    # 获取或创建用户记录
    linked_data = load_linked_channels()
    
    # 查找确认者是否是现有用户
    existing_user = None
    for user in linked_data["users"]:
        for channel in user["channels"]:
            if channel["channel_id"] == confirmer_channel_id:
                existing_user = user
                break
    
    if not existing_user:
        # 确认者不是现有用户，创建新用户
        existing_user = {
            "userId": f"user_{len(linked_data['users']) + 1:03d}",
            "name": code_info["user_name"],
            "channels": [],
            "createdAt": datetime.now().isoformat()
        }
        linked_data["users"].append(existing_user)
    
    # 添加新渠道
    new_channel = {
        "platform": code_info["channel_platform"],
        "channel_id": code_info["channel_id"],
        "bound_at": datetime.now().isoformat(),
        "is_primary": len(existing_user["channels"]) == 0  # 第一个渠道是主渠道
    }
    
    # 标记主渠道
    if len(existing_user["channels"]) > 0:
        # 已有渠道，新渠道不是主渠道
        new_channel["is_primary"] = False
    else:
        # 第一个渠道，设为主渠道
        new_channel["is_primary"] = True
        # 同时把确认者的渠道也标记为主渠道（如果是不同的）
        for ch in existing_user["channels"]:
            ch["is_primary"] = True
    
    existing_user["channels"].append(new_channel)
    
    # 更新绑定码状态
    code_info["status"] = "confirmed"
    save_binding_codes(codes_data)
    
    # 保存用户数据
    save_linked_channels(linked_data)
    
    return {
        "success": True,
        "message": f"""✅ 绑定成功！

{code_info['channel_platform']} 已关联到 {existing_user['name']}。
现在你可以在多个渠道无缝切换，我会记住你～

📋 已绑定渠道：{len(existing_user['channels'])} 个""",
        "user_id": existing_user["userId"],
        "user_name": existing_user["name"],
        "channels_count": len(existing_user["channels"])
    }


def get_user_channels(channel_id):
    """
    查询用户已绑定的所有渠道
    
    Args:
        channel_id: 渠道 ID
    
    Returns:
        dict: 渠道列表
    """
    linked_data = load_linked_channels()
    
    for user in linked_data["users"]:
        for channel in user["channels"]:
            if channel["channel_id"] == channel_id:
                return {
                    "success": True,
                    "user_name": user["name"],
                    "channels": user["channels"]
                }
    
    return {
        "success": False,
        "message": "未找到绑定的渠道"
    }


def verify_identity(channel_platform, channel_id):
    """
    验证身份
    
    Args:
        channel_platform: 渠道平台
        channel_id: 渠道 ID
    
    Returns:
        dict: 验证结果
    """
    linked_data = load_linked_channels()
    
    for user in linked_data["users"]:
        for channel in user["channels"]:
            if channel["channel_id"] == channel_id and channel["platform"] == channel_platform:
                return {
                    "verified": True,
                    "user_id": user["userId"],
                    "user_name": user["name"],
                    "is_primary": channel.get("is_primary", False),
                    "channels_count": len(user["channels"])
                }
    
    return {
        "verified": False,
        "message": "未绑定身份"
    }


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法：python link-identity.py <命令> [参数]")
        print("命令:")
        print("  generate <platform> <channel_id> [user_name]  - 生成绑定码")
        print("  confirm <binding_code> <channel_id>           - 确认绑定")
        print("  verify <platform> <channel_id>                - 验证身份")
        print("  list <channel_id>                             - 列出渠道")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate":
        if len(sys.argv) < 4:
            print("用法：python link-identity.py generate <platform> <channel_id> [user_name]")
            sys.exit(1)
        platform = sys.argv[2]
        channel_id = sys.argv[3]
        user_name = sys.argv[4] if len(sys.argv) > 4 else "用户"
        
        result = create_binding_request(platform, channel_id, user_name)
        print(result["message"])
    
    elif command == "confirm":
        if len(sys.argv) < 4:
            print("用法：python link-identity.py confirm <binding_code> <channel_id>")
            sys.exit(1)
        binding_code = sys.argv[2]
        channel_id = sys.argv[3]
        
        result = confirm_binding(binding_code, channel_id)
        print(result["message"])
    
    elif command == "verify":
        if len(sys.argv) < 4:
            print("用法：python link-identity.py verify <platform> <channel_id>")
            sys.exit(1)
        platform = sys.argv[2]
        channel_id = sys.argv[3]
        
        result = verify_identity(platform, channel_id)
        if result["verified"]:
            print(f"✅ 已验证：{result['user_name']} (用户 ID: {result['user_id']})")
            print(f"   主渠道：{'是' if result['is_primary'] else '否'}")
            print(f"   绑定渠道数：{result['channels_count']}")
        else:
            print(f"❌ {result['message']}")
    
    elif command == "list":
        if len(sys.argv) < 3:
            print("用法：python link-identity.py list <channel_id>")
            sys.exit(1)
        channel_id = sys.argv[2]
        
        result = get_user_channels(channel_id)
        if result["success"]:
            print(f"📋 {result['user_name']} 的已绑定渠道：")
            for ch in result["channels"]:
                primary = "🟢" if ch.get("is_primary") else "🔵"
                print(f"   {primary} {ch['platform']}: {ch['channel_id']}")
        else:
            print(f"❌ {result['message']}")
    
    else:
        print(f"未知命令：{command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
