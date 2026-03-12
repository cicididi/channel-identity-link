# 🚀 发布到 GitHub 指南

## ⚠️ 首次推送需要手动完成

由于 GitHub 需要身份验证，请按以下步骤操作：

---

## 方法一：HTTPS + Personal Access Token（推荐）

### 1. 创建 GitHub Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选权限：`repo`（完整控制私有仓库）
4. 生成后复制 token（只会显示一次！）

### 2. 推送代码

```bash
cd ~/.openclaw/workspace/skills/channel-identity-link

# 使用 token 推送（替换 YOUR_TOKEN）
git remote set-url origin https://YOUR_TOKEN@github.com/cicigodd/channel-identity-link.git
git push -u origin master
```

---

## 方法二：SSH（一劳永逸）

### 1. 生成 SSH 密钥（如果还没有）

```bash
ssh-keygen -t ed25519 -C "cicigodd@163.com"
# 一路回车
```

### 2. 添加 SSH 公钥到 GitHub

```bash
cat ~/.ssh/id_ed25519.pub
# 复制输出内容
```

访问：https://github.com/settings/keys  
点击 "New SSH key"，粘贴公钥内容

### 3. 修改为 SSH 地址并推送

```bash
cd ~/.openclaw/workspace/skills/channel-identity-link
git remote set-url origin git@github.com:cicigodd/channel-identity-link.git
git push -u origin master
```

---

## ✅ 推送成功后

1. 访问：https://github.com/cicigodd/channel-identity-link
2. 确认文件都已上传
3. 可以添加 README 徽章、License 等

---

## 📦 发布到 ClawHub（可选）

如果想让其他人也能安装：

```bash
cd ~/.openclaw/workspace/skills/channel-identity-link
clawhub publish .
```

---

## 🔗 GitHub 仓库地址

**HTTPS**: https://github.com/cicigodd/channel-identity-link.git  
**SSH**: git@github.com:cicigodd/channel-identity-link.git

---

**创建者**：胖头 🐱  
**日期**：2026-03-12
