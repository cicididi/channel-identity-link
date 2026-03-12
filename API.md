# API 文档

## 跨渠道身份关联 API

### 基础信息

- **版本**: 2.0.0
- **作者**: cicigodd
- **许可证**: MIT

---

## 函数 API

### IdentityManager 类

#### `__init__(cfg: Config = None)`

初始化身份管理器

**参数**:
- `cfg`: 配置对象（可选，使用全局配置如果未提供）

**示例**:
```python
manager = IdentityManager()
```

---

#### `generate_binding_code(user_name: str = "USER") -> str`

生成安全的绑定码

**参数**:
- `user_name`: 用户名称

**返回**:
- `str`: 绑定码（格式：PANGTOU-{NAME}-{RANDOM}）

**示例**:
```python
code = manager.generate_binding_code("爸爸")
# 输出：PANGTOU-DAD-A7B9C2
```

---

#### `create_binding_request(channel_platform, channel_id, user_name) -> Dict`

创建绑定请求

**参数**:
- `channel_platform`: 渠道平台 (feishu, wecom, telegram, etc.)
- `channel_id`: 渠道用户 ID
- `user_name`: 用户名称

**返回**:
```json
{
  "success": true,
  "binding_code": "PANGTOU-DAD-A7B9C2",
  "expires_at": "2026-03-12T20:00:00",
  "expires_in_minutes": 30,
  "message": "🔑 生成绑定码：PANGTOU-DAD-A7B9C2..."
}
```

**示例**:
```python
result = manager.create_binding_request(
    "feishu",
    "ou_xxx",
    "爸爸"
)
```

---

#### `confirm_binding(binding_code, confirmer_channel_id) -> Dict`

确认绑定

**参数**:
- `binding_code`: 绑定码
- `confirmer_channel_id`: 确认者的渠道 ID

**返回**:
```json
{
  "success": true,
  "message": "✅ 绑定成功！",
  "user_id": "user_001",
  "user_name": "爸爸",
  "channels_count": 2
}
```

**示例**:
```python
result = manager.confirm_binding(
    "PANGTOU-DAD-A7B9C2",
    "ou_xxx"
)
```

---

#### `verify_identity(channel_platform, channel_id) -> Dict`

验证身份

**参数**:
- `channel_platform`: 渠道平台
- `channel_id`: 渠道 ID

**返回**:
```json
{
  "verified": true,
  "user_id": "user_001",
  "user_name": "爸爸",
  "is_primary": true,
  "channels_count": 2,
  "message": "✅ 已验证：爸爸"
}
```

**示例**:
```python
result = manager.verify_identity("feishu", "ou_xxx")
```

---

#### `get_user_channels(channel_id) -> Dict`

查询用户已绑定的所有渠道

**参数**:
- `channel_id`: 渠道 ID

**返回**:
```json
{
  "success": true,
  "user_id": "user_001",
  "user_name": "爸爸",
  "channels": [
    {"platform": "feishu", "channel_id": "ou_xxx", "is_primary": true},
    {"platform": "wecom", "channel_id": "yyy", "is_primary": false}
  ],
  "channels_count": 2
}
```

---

#### `revoke_binding(channel_id, platform) -> Dict`

解除绑定

**参数**:
- `channel_id`: 渠道 ID
- `platform`: 渠道平台

**返回**:
```json
{
  "success": true,
  "message": "✅ 已解除绑定：wecom",
  "remaining_channels": 1
}
```

---

## 命令行 API

### 生成绑定码

```bash
python link-identity.py generate <platform> <channel_id> [--name <name>]
```

**示例**:
```bash
python link-identity.py generate feishu ou_xxx --name 爸爸
```

---

### 确认绑定

```bash
python link-identity.py confirm <binding_code> <channel_id>
```

**示例**:
```bash
python link-identity.py confirm PANGTOU-DAD-A7B9C2 ou_xxx
```

---

### 验证身份

```bash
python link-identity.py verify <platform> <channel_id>
```

**示例**:
```bash
python link-identity.py verify feishu ou_xxx
```

---

### 列出渠道

```bash
python link-identity.py list <channel_id>
```

**示例**:
```bash
python link-identity.py list ou_xxx
```

---

### 解除绑定

```bash
python link-identity.py revoke <platform> <channel_id>
```

**示例**:
```bash
python link-identity.py revoke wecom yyy
```

---

## 错误处理

所有 API 调用都会返回统一的错误格式：

```json
{
  "success": false,
  "error": "错误描述",
  "message": "❌ 用户友好的错误消息"
}
```

### 常见错误

| 错误码 | 说明 | 解决方法 |
|--------|------|----------|
| `BINDING_CODE_NOT_FOUND` | 绑定码不存在 | 重新生成绑定码 |
| `BINDING_CODE_EXPIRED` | 绑定码已过期 | 重新生成绑定码 |
| `BINDING_CODE_ALREADY_USED` | 绑定码已使用 | 使用新的绑定码 |
| `CHANNEL_NOT_FOUND` | 渠道未找到 | 检查渠道 ID 是否正确 |
| `MAX_BINDING_CODES_REACHED` | 绑定码数量达上限 | 等待清理或手动清理 |

---

## 最佳实践

### 1. 错误处理

```python
result = manager.create_binding_request("feishu", "ou_xxx")
if not result['success']:
    print(f"失败：{result['error']}")
    # 记录日志或重试
```

### 2. 并发安全

使用文件锁确保并发安全：

```python
from link-identity import file_lock

with file_lock(config.binding_codes_file):
    # 安全的文件操作
    codes_data = manager._load_binding_codes()
    # ...
```

### 3. 日志记录

```python
import logging
logger = logging.getLogger("ChannelIdentity")

logger.info("绑定请求创建成功")
logger.warning("绑定码即将过期")
logger.error("绑定确认失败")
```

---

## 测试

运行单元测试：

```bash
cd tests
python -m unittest test_identity.py
```

运行所有测试：

```bash
python -m pytest tests/
```

---

## 版本历史

### v2.0.0 (2026-03-12)

- ✅ 重写为专业级代码
- ✅ 添加错误处理和日志记录
- ✅ 添加并发安全的文件锁
- ✅ 改进绑定码生成算法
- ✅ 添加完整的单元测试
- ✅ 改进 API 文档

### v1.0.0 (2026-03-12)

- 初始版本

---

**最后更新**: 2026-03-12  
**维护者**: cicigodd
