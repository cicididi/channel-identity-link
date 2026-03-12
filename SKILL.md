---
name: channel-identity-link
description: 跨渠道身份关联技能。支持用户在不同聊天渠道（飞书/企业微信/Telegram/WhatsApp 等）之间绑定身份，实现"换渠道不换人"。
author: cicigodd
version: 1.0.0
tags:
  - identity
  - cross-channel
  - user-binding
  - feishu
  - wechat
  - telegram
---

# 跨渠道身份关联

让用户在不同聊天渠道之间绑定身份，实现无缝切换。

---

## 🎯 使用场景

1. **换渠道**：从飞书换到企业微信，保持身份和记忆
2. **多渠道**：同时在多个渠道使用，知道是同一个用户
3. **家庭共享**：家人共用一个 AI，但区分不同成员

---

## 🚀 快速开始

### 首次绑定（新渠道）

在新渠道发送：
```
绑定身份
```

AI 会生成一个**绑定码**，例如：
```
🔑 你的绑定码：PANGTOU-DAD-2026

请在其他渠道输入这个绑定码完成关联。
```

### 确认绑定（原渠道）

在原渠道收到通知后，回复：
```
确认绑定 PANGTOU-DAD-2026
```

### 完成

绑定成功后，新渠道会自动：
- 继承 USER.md 中的用户信息
- 共享 MEMORY.md 中的记忆
- 使用相同的 SOUL.md 人格

---

## 📋 命令

| 命令 | 说明 |
|------|------|
| `绑定身份` | 生成绑定码，发起绑定流程 |
| `确认绑定 <绑定码>` | 确认绑定请求 |
| `我的渠道` | 查看已绑定的所有渠道 |
| `解除绑定 <渠道>` | 解除某个渠道的绑定 |
| `我是谁` | 查看当前身份信息 |

---

## 🔧 技术实现

### 身份存储

身份关联信息存储在 `~/.openclaw/workspace/identity/linked-channels.json`：

```json
{
  "users": [
    {
      "userId": "user_001",
      "name": "爸爸",
      "channels": [
        {
          "platform": "feishu",
          "channelId": "ou_e6f25dcb2a18ba4382ef635ae90140f7",
          "boundAt": "2026-03-12T16:00:00+08:00",
          "isPrimary": true
        },
        {
          "platform": "wecom",
          "channelId": "xxx",
          "boundAt": "2026-03-12T16:45:00+08:00",
          "isPrimary": false
        }
      ]
    }
  ]
}
```

### 绑定流程

```
1. 新渠道用户发送"绑定身份"
   ↓
2. 生成唯一绑定码（如 PANGTOU-DAD-2026）
   ↓
3. 等待原渠道确认（30 分钟有效期）
   ↓
4. 原渠道回复"确认绑定 <绑定码>"
   ↓
5. 更新 linked-channels.json
   ↓
6. 通知双方绑定成功
```

### 身份验证

每次收到消息时：
1. 提取渠道 ID（从 OpenClaw inbound metadata）
2. 查询 linked-channels.json
3. 如果匹配 → 加载对应用户的 USER.md
4. 如果不匹配 → 提示绑定身份

---

## 📁 文件结构

```
channel-identity-link/
├── SKILL.md                    # 本文档
├── scripts/
│   ├── link-identity.py        # 身份绑定主脚本
│   ├── verify-identity.py      # 身份验证
│   └── generate-code.py        # 生成绑定码
├── hooks/
│   └── openclaw/
│       └── HOOK.md             # OpenClaw hook 配置
└── templates/
    ├── bind-request.md         # 绑定请求模板
    └── bind-confirm.md         # 绑定确认模板
```

---

## 🔐 安全考虑

1. **绑定码有效期**：30 分钟，过期作废
2. **确认机制**：需要原渠道确认，防止恶意绑定
3. **唯一性**：一个渠道只能绑定一个用户
4. **隐私**：linked-channels.json 不应提交到 Git（加入 .gitignore）

---

## 🛠️ 安装

```bash
# 从 ClawHub 安装
clawhub install channel-identity-link

# 或手动克隆
git clone https://github.com/your-username/channel-identity-link.git
~/.openclaw/workspace/skills/channel-identity-link
```

---

## 📝 示例对话

### 场景 1：换渠道

**用户（企业微信）**：
```
绑定身份
```

**AI**：
```
🔑 生成绑定码：PANGTOU-DAD-2026

请在飞书（你的主渠道）输入"确认绑定 PANGTOU-DAD-2026"完成关联。

⏰ 有效期：30 分钟
```

**用户（飞书）**：
```
确认绑定 PANGTOU-DAD-2026
```

**AI**：
```
✅ 绑定成功！

企业微信已关联到你的身份（爸爸）。
现在你可以在两个渠道无缝切换，我会记住你～
```

---

### 场景 2：查看绑定

**用户**：
```
我的渠道
```

**AI**：
```
📋 已绑定的渠道：

1. 🟢 飞书 (主渠道)
   ID: ou_e6f25dcb2a18ba4382ef635ae90140f7
   绑定时间：2026-03-12 16:00

2. 🟢 企业微信
   ID: xxx
   绑定时间：2026-03-12 16:45

共 2 个渠道
```

---

## 🎨 自定义

### 修改绑定码格式

编辑 `scripts/generate-code.py`：
```python
def generate_code(user_name):
    # 默认格式：PANGTOU-{NAME}-{DATE}
    return f"PANGTOU-{user_name.upper()}-{datetime.now().strftime('%Y')}"
```

### 修改有效期

编辑 `SKILL.md` 配置：
```yaml
binding_code_expiry_minutes: 30  # 改为 60 即 1 小时
```

---

## 🐛 故障排除

### 问题：收不到绑定通知

**解决**：检查 cron 是否正常运行
```bash
openclaw cron list
```

### 问题：绑定后还是不认识我

**解决**：重启 Gateway
```bash
openclaw gateway restart
```

---

## 📄 License

MIT License - 胖头工作室

---

**作者**：胖头 🐱  
**创建日期**：2026-03-12  
**版本**：1.0.0
