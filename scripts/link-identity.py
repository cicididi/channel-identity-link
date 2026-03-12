#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨渠道身份关联 - 专业版
Channel Identity Link - Professional Edition

处理绑定请求、生成绑定码、验证身份

功能特性：
- ✅ 错误处理和日志记录
- ✅ 并发安全的文件锁
- ✅ 安全的绑定码生成（6 位字母数字组合）
- ✅ 绑定码有效期管理
- ✅ 完整的 API 接口
- ✅ 配置化管理
- ✅ 单元测试支持

作者：cicigodd
版本：2.0.0
许可证：MIT
"""

import os
import sys
import json
import random
import string
import hashlib
import logging
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager

# ============ 配置管理 ============

@dataclass
class Config:
    """配置类"""
    workspace_dir: Path = Path.home() / ".openclaw" / "workspace"
    identity_dir: Optional[Path] = None
    linked_channels_file: Optional[Path] = None
    binding_codes_file: Optional[Path] = None
    log_file: Optional[Path] = None
    
    # 安全配置
    binding_code_length: int = 6  # 绑定码长度
    binding_code_prefix: str = "PANGTOU"  # 绑定码前缀
    binding_code_expiry_minutes: int = 30  # 有效期（分钟）
    max_binding_codes: int = 100  # 最大待确认绑定码数量
    
    # 日志配置
    log_level: str = "INFO"
    
    def __post_init__(self):
        """初始化后处理"""
        if self.identity_dir is None:
            self.identity_dir = self.workspace_dir / "identity"
        if self.linked_channels_file is None:
            self.linked_channels_file = self.identity_dir / "linked-channels.json"
        if self.binding_codes_file is None:
            self.binding_codes_file = self.identity_dir / "binding-codes.json"
        if self.log_file is None:
            self.log_file = self.workspace_dir / "logs" / "channel-identity.log"


# 全局配置
config = Config()

# ============ 日志设置 ============

def setup_logging():
    """设置日志"""
    log_dir = config.log_file.parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("ChannelIdentity")

logger = setup_logging()

# ============ 文件锁（并发安全） ============

@contextmanager
def file_lock(file_path: Path):
    """
    文件锁上下文管理器
    
    确保同一时间只有一个进程能写入文件
    
    Args:
        file_path: 要锁定的文件路径
    """
    lock_file = file_path.with_suffix(file_path.suffix + '.lock')
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    lock_fd = None
    try:
        lock_fd = open(lock_file, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
        logger.debug(f"Acquired lock: {lock_file}")
        yield
    finally:
        if lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
            logger.debug(f"Released lock: {lock_file}")


# ============ 数据类 ============

@dataclass
class BindingCode:
    """绑定码数据类"""
    code: str
    channel_platform: str
    channel_id: str
    user_name: str
    created_at: str
    expires_at: str
    status: str  # pending, confirmed, expired, revoked
    ip_address: Optional[str] = None  # 可选：记录 IP
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        try:
            expires_at = datetime.fromisoformat(self.expires_at)
            return datetime.now() > expires_at
        except Exception:
            return True
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BindingCode':
        """从字典创建"""
        return cls(**data)


@dataclass
class Channel:
    """渠道数据类"""
    platform: str
    channel_id: str
    bound_at: str
    is_primary: bool = False
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Channel':
        """从字典创建"""
        return cls(**data)


@dataclass
class User:
    """用户数据类"""
    user_id: str
    name: str
    channels: List[Channel]
    created_at: str
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['channels'] = [c.to_dict() if isinstance(c, Channel) else c for c in self.channels]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """从字典创建"""
        channels = [Channel.from_dict(c) if isinstance(c, dict) else c for c in data.get('channels', [])]
        return cls(
            user_id=data['user_id'],
            name=data['name'],
            channels=channels,
            created_at=data['created_at'],
            updated_at=data.get('updated_at')
        )


# ============ 核心功能 ============

class IdentityManager:
    """身份管理器"""
    
    def __init__(self, cfg: Config = None):
        """
        初始化身份管理器
        
        Args:
            cfg: 配置对象，使用全局配置如果未提供
        """
        self.cfg = cfg or config
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        self.cfg.identity_dir.mkdir(parents=True, exist_ok=True)
        self.cfg.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def generate_binding_code(self, user_name: str = "USER") -> str:
        """
        生成安全的绑定码
        
        格式：{PREFIX}-{NAME_SHORT}-{RANDOM}
        例如：PANGTOU-DAD-A7B9C2
        
        Args:
            user_name: 用户名称
            
        Returns:
            str: 绑定码
        """
        # 生成随机部分（6 位字母数字）
        chars = string.ascii_uppercase + string.digits
        random_suffix = ''.join(random.SystemRandom().choices(chars, k=config.binding_code_length))
        
        # 缩短用户名（最多 8 字符）
        name_short = user_name.upper().replace(' ', '_')[:8]
        
        # 组合绑定码
        code = f"{config.binding_code_prefix}-{name_short}-{random_suffix}"
        
        logger.info(f"Generated binding code for {user_name}: {code}")
        return code
    
    def create_binding_request(
        self,
        channel_platform: str,
        channel_id: str,
        user_name: str = "用户"
    ) -> Dict[str, Any]:
        """
        创建绑定请求
        
        Args:
            channel_platform: 渠道平台 (feishu, wecom, telegram, etc.)
            channel_id: 渠道用户 ID
            user_name: 用户名称
            
        Returns:
            dict: 绑定请求信息
            
        Raises:
            ValueError: 参数无效
            RuntimeError: 系统错误
        """
        try:
            # 验证参数
            if not channel_platform or not channel_id:
                raise ValueError("渠道平台和渠道 ID 不能为空")
            
            # 生成绑定码
            binding_code = self.generate_binding_code(user_name)
            expires_at = (datetime.now() + timedelta(minutes=config.binding_code_expiry_minutes)).isoformat()
            
            # 创建绑定码对象
            code_obj = BindingCode(
                code=binding_code,
                channel_platform=channel_platform,
                channel_id=channel_id,
                user_name=user_name,
                created_at=datetime.now().isoformat(),
                expires_at=expires_at,
                status="pending"
            )
            
            # 使用文件锁写入
            with file_lock(self.cfg.binding_codes_file):
                codes_data = self._load_binding_codes()
                
                # 清理过期的绑定码
                codes_data = self._cleanup_expired_codes(codes_data)
                
                # 检查是否超过最大数量
                pending_count = sum(1 for c in codes_data.get('codes', {}).values() 
                                   if c.get('status') == 'pending')
                if pending_count >= config.max_binding_codes:
                    raise RuntimeError(f"待确认绑定码数量已达上限 ({config.max_binding_codes})")
                
                # 保存绑定码
                codes_data['codes'][binding_code] = code_obj.to_dict()
                self._save_binding_codes(codes_data)
            
            logger.info(f"Created binding request: {binding_code}")
            
            return {
                "success": True,
                "binding_code": binding_code,
                "expires_at": expires_at,
                "expires_in_minutes": config.binding_code_expiry_minutes,
                "message": self._format_bind_request_message(binding_code, expires_at, channel_platform)
            }
            
        except Exception as e:
            logger.error(f"Failed to create binding request: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 创建绑定请求失败：{e}"
            }
    
    def confirm_binding(self, binding_code: str, confirmer_channel_id: str) -> Dict[str, Any]:
        """
        确认绑定
        
        Args:
            binding_code: 绑定码
            confirmer_channel_id: 确认者的渠道 ID
            
        Returns:
            dict: 绑定结果
        """
        try:
            with file_lock(self.cfg.binding_codes_file):
                codes_data = self._load_binding_codes()
                
                # 检查绑定码是否存在
                if binding_code not in codes_data.get('codes', {}):
                    return {
                        "success": False,
                        "message": "❌ 绑定码不存在"
                    }
                
                code_info = codes_data['codes'][binding_code]
                
                # 检查是否过期
                if code_info['status'] == 'expired' or self._is_code_expired(code_info):
                    code_info['status'] = 'expired'
                    self._save_binding_codes(codes_data)
                    return {
                        "success": False,
                        "message": "❌ 绑定码已过期，请重新生成"
                    }
                
                # 检查状态
                if code_info['status'] != 'pending':
                    return {
                        "success": False,
                        "message": f"❌ 绑定码状态：{code_info['status']}（不可用）"
                    }
                
                # 获取或创建用户记录
                with file_lock(self.cfg.linked_channels_file):
                    linked_data = self._load_linked_channels()
                    
                    # 查找确认者是否是现有用户
                    existing_user = self._find_user_by_channel(linked_data, confirmer_channel_id)
                    
                    if not existing_user:
                        # 创建新用户
                        existing_user = User(
                            user_id=f"user_{len(linked_data['users']) + 1:03d}",
                            name=code_info['user_name'],
                            channels=[],
                            created_at=datetime.now().isoformat()
                        )
                        linked_data['users'].append(existing_user)
                        logger.info(f"Created new user: {existing_user.user_id}")
                    
                    # 添加新渠道
                    new_channel = Channel(
                        platform=code_info['channel_platform'],
                        channel_id=code_info['channel_id'],
                        bound_at=datetime.now().isoformat(),
                        is_primary=(len(existing_user.channels) == 0)
                    )
                    
                    # 如果已有渠道，确保第一个渠道保持为主渠道
                    if len(existing_user.channels) > 0:
                        new_channel.is_primary = False
                    else:
                        # 标记确认者的渠道为主渠道
                        for ch in existing_user.channels:
                            ch.is_primary = True
                    
                    existing_user.channels.append(new_channel)
                    existing_user.updated_at = datetime.now().isoformat()
                    
                    # 更新绑定码状态
                    code_info['status'] = 'confirmed'
                    self._save_binding_codes(codes_data)
                    
                    # 保存用户数据
                    self._save_linked_channels(linked_data)
                
                logger.info(f"Binding confirmed: {binding_code} -> {existing_user.user_id}")
                
                return {
                    "success": True,
                    "message": self._format_bind_success_message(
                        code_info['channel_platform'],
                        existing_user.name,
                        len(existing_user.channels)
                    ),
                    "user_id": existing_user.user_id,
                    "user_name": existing_user.name,
                    "channels_count": len(existing_user.channels)
                }
                
        except Exception as e:
            logger.error(f"Failed to confirm binding: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 确认绑定失败：{e}"
            }
    
    def verify_identity(self, channel_platform: str, channel_id: str) -> Dict[str, Any]:
        """
        验证身份
        
        Args:
            channel_platform: 渠道平台
            channel_id: 渠道 ID
            
        Returns:
            dict: 验证结果
        """
        try:
            linked_data = self._load_linked_channels()
            
            for user in linked_data['users']:
                user_obj = User.from_dict(user) if isinstance(user, dict) else user
                for channel in user_obj.channels:
                    if (channel.channel_id == channel_id and 
                        channel.platform == channel_platform):
                        return {
                            "verified": True,
                            "user_id": user_obj.user_id,
                            "user_name": user_obj.name,
                            "is_primary": channel.is_primary,
                            "channels_count": len(user_obj.channels),
                            "message": f"✅ 已验证：{user_obj.name}"
                        }
            
            return {
                "verified": False,
                "message": "未绑定身份",
                "suggestion": "发送'绑定身份'开始绑定流程"
            }
            
        except Exception as e:
            logger.error(f"Failed to verify identity: {e}")
            return {
                "verified": False,
                "error": str(e),
                "message": f"❌ 验证失败：{e}"
            }
    
    def get_user_channels(self, channel_id: str) -> Dict[str, Any]:
        """
        查询用户已绑定的所有渠道
        
        Args:
            channel_id: 渠道 ID
            
        Returns:
            dict: 渠道列表
        """
        try:
            linked_data = self._load_linked_channels()
            
            for user in linked_data['users']:
                user_obj = User.from_dict(user) if isinstance(user, dict) else user
                for channel in user_obj.channels:
                    if channel.channel_id == channel_id:
                        return {
                            "success": True,
                            "user_id": user_obj.user_id,
                            "user_name": user_obj.name,
                            "channels": [c.to_dict() for c in user_obj.channels],
                            "channels_count": len(user_obj.channels)
                        }
            
            return {
                "success": False,
                "message": "未找到绑定的渠道"
            }
            
        except Exception as e:
            logger.error(f"Failed to get user channels: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 查询失败：{e}"
            }
    
    def revoke_binding(self, channel_id: str, platform: str) -> Dict[str, Any]:
        """
        解除绑定
        
        Args:
            channel_id: 渠道 ID
            platform: 渠道平台
            
        Returns:
            dict: 解除结果
        """
        try:
            with file_lock(self.cfg.linked_channels_file):
                linked_data = self._load_linked_channels()
                
                for user in linked_data['users']:
                    user_obj = User.from_dict(user) if isinstance(user, dict) else user
                    original_count = len(user_obj.channels)
                    
                    # 移除指定渠道
                    user_obj.channels = [
                        c for c in user_obj.channels 
                        if not (c.channel_id == channel_id and c.platform == platform)
                    ]
                    
                    if len(user_obj.channels) < original_count:
                        user_obj.updated_at = datetime.now().isoformat()
                        self._save_linked_channels(linked_data)
                        
                        logger.info(f"Revoked binding: {platform}:{channel_id}")
                        
                        return {
                            "success": True,
                            "message": f"✅ 已解除绑定：{platform}",
                            "remaining_channels": len(user_obj.channels)
                        }
                
                return {
                    "success": False,
                    "message": "未找到该渠道的绑定"
                }
                
        except Exception as e:
            logger.error(f"Failed to revoke binding: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ 解除绑定失败：{e}"
            }
    
    # ============ 辅助方法 ============
    
    def _load_binding_codes(self) -> Dict:
        """加载绑定码"""
        if not self.cfg.binding_codes_file.exists():
            return {"codes": {}, "version": "2.0"}
        
        try:
            with open(self.cfg.binding_codes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load binding codes: {e}")
            return {"codes": {}, "version": "2.0"}
    
    def _save_binding_codes(self, data: Dict):
        """保存绑定码"""
        with open(self.cfg.binding_codes_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_linked_channels(self) -> Dict:
        """加载已绑定的渠道"""
        if not self.cfg.linked_channels_file.exists():
            return {"users": [], "version": "2.0"}
        
        try:
            with open(self.cfg.linked_channels_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load linked channels: {e}")
            return {"users": [], "version": "2.0"}
    
    def _save_linked_channels(self, data: Dict):
        """保存已绑定的渠道"""
        with open(self.cfg.linked_channels_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _cleanup_expired_codes(self, codes_data: Dict) -> Dict:
        """清理过期的绑定码"""
        now = datetime.now()
        expired_count = 0
        
        for code, info in list(codes_data.get('codes', {}).items()):
            try:
                expires_at = datetime.fromisoformat(info['expires_at'])
                if now > expires_at or info.get('status') == 'expired':
                    del codes_data['codes'][code]
                    expired_count += 1
            except Exception:
                # 无效的绑定码，删除
                del codes_data['codes'][code]
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired binding codes")
        
        return codes_data
    
    def _is_code_expired(self, code_info: Dict) -> bool:
        """检查绑定码是否过期"""
        try:
            expires_at = datetime.fromisoformat(code_info['expires_at'])
            return datetime.now() > expires_at
        except Exception:
            return True
    
    def _find_user_by_channel(
        self,
        linked_data: Dict,
        channel_id: str
    ) -> Optional[User]:
        """根据渠道 ID 查找用户"""
        for user in linked_data['users']:
            user_obj = User.from_dict(user) if isinstance(user, dict) else user
            for channel in user_obj.channels:
                if channel.channel_id == channel_id:
                    return user_obj
        return None
    
    def _format_bind_request_message(
        self,
        binding_code: str,
        expires_at: str,
        channel_platform: str
    ) -> str:
        """格式化绑定请求消息"""
        return f"""🔑 生成绑定码：**{binding_code}**

请在你的主渠道输入"确认绑定 {binding_code}"完成关联。

⏰ 有效期：{config.binding_code_expiry_minutes} 分钟
📱 新渠道：{channel_platform}

💡 提示：绑定码只能使用一次，过期作废。"""
    
    def _format_bind_success_message(
        self,
        platform: str,
        user_name: str,
        channels_count: int
    ) -> str:
        """格式化绑定成功消息"""
        return f"""✅ 绑定成功！

{platform} 已关联到 {user_name}。
现在你可以在多个渠道无缝切换，我会记住你～

📋 已绑定渠道：{channels_count} 个"""


# ============ 命令行接口 ============

def create_cli():
    """创建命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="跨渠道身份关联工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s generate feishu ou_xxx 爸爸          # 生成绑定码
  %(prog)s confirm PANGTOU-DAD-A7B9C2 ou_xxx    # 确认绑定
  %(prog)s verify feishu ou_xxx                 # 验证身份
  %(prog)s list ou_xxx                          # 列出渠道
  %(prog)s revoke feishu ou_xxx                 # 解除绑定
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # generate 命令
    gen_parser = subparsers.add_parser('generate', help='生成绑定码')
    gen_parser.add_argument('platform', help='渠道平台 (feishu, wecom, telegram, etc.)')
    gen_parser.add_argument('channel_id', help='渠道用户 ID')
    gen_parser.add_argument('--name', default='用户', help='用户名称')
    
    # confirm 命令
    conf_parser = subparsers.add_parser('confirm', help='确认绑定')
    conf_parser.add_argument('binding_code', help='绑定码')
    conf_parser.add_argument('channel_id', help='确认者的渠道 ID')
    
    # verify 命令
    ver_parser = subparsers.add_parser('verify', help='验证身份')
    ver_parser.add_argument('platform', help='渠道平台')
    ver_parser.add_argument('channel_id', help='渠道 ID')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出渠道')
    list_parser.add_argument('channel_id', help='渠道 ID')
    
    # revoke 命令
    rev_parser = subparsers.add_parser('revoke', help='解除绑定')
    rev_parser.add_argument('platform', help='渠道平台')
    rev_parser.add_argument('channel_id', help='渠道 ID')
    
    return parser


def main():
    """主函数"""
    parser = create_cli()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = IdentityManager()
    
    try:
        if args.command == 'generate':
            result = manager.create_binding_request(
                args.platform,
                args.channel_id,
                args.name
            )
            print(result['message'])
            
        elif args.command == 'confirm':
            result = manager.confirm_binding(
                args.binding_code,
                args.channel_id
            )
            print(result['message'])
            
        elif args.command == 'verify':
            result = manager.verify_identity(
                args.platform,
                args.channel_id
            )
            if result['verified']:
                print(f"✅ {result['message']}")
                print(f"   用户 ID: {result['user_id']}")
                print(f"   主渠道：{'是' if result['is_primary'] else '否'}")
                print(f"   绑定渠道数：{result['channels_count']}")
            else:
                print(f"❌ {result['message']}")
                
        elif args.command == 'list':
            result = manager.get_user_channels(args.channel_id)
            if result['success']:
                print(f"📋 {result['user_name']} 的已绑定渠道：")
                for ch in result['channels']:
                    primary = "🟢" if ch['is_primary'] else "🔵"
                    print(f"   {primary} {ch['platform']}: {ch['channel_id']}")
                print(f"\n共 {result['channels_count']} 个渠道")
            else:
                print(f"❌ {result['message']}")
                
        elif args.command == 'revoke':
            result = manager.revoke_binding(args.channel_id, args.platform)
            print(result['message'])
            
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"❌ 发生错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
