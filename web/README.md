# CloverHub Web 管理后台

基于 Vue 3 + Element Plus 的 Web 管理后台，用于管理活动、用户数据和备份。

---

## 功能特性

- **活动管理**：查看、搜索、删除活动
- **用户数据**：查看活动的报名列表、表单数据、反馈数据
- **用户管理**：查看所有用户及其报名记录
- **数据备份**：导出/导入 JSON 数据

---

## 快速开始

### 1. 配置环境 ID

编辑 `src/cloud.js`，将环境 ID 替换为您的：

```javascript
const CLOUDBASE_ENV_ID = '您的环境ID'
```

### 2. 安装依赖

```bash
cd web-admin
npm install
```

### 3. 本地开发

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 构建生产版本

```bash
npm run build
```

构建后的文件在 `dist` 目录

---

## 部署到 CloudBase（自动化部署）

### 方式一：CloudBase 静态托管（简单）

1. 进入 [CloudBase 控制台](https://console.cloudbase.net/)
2. 开通静态网站托管
3. 上传 `dist` 目录中的所有文件
4. 获取访问域名

### 方式二：CloudBase Web Framework（推荐，可自动部署）

#### 前提条件
- GitHub 账号
- CloudBase 账号

#### 步骤

**第一步：创建 GitHub 仓库**

1. 打开 https://github.com
2. 点击右上角 **+** → **New repository**
3. 仓库名填写 `clover-web-admin`
4. 选择 **Private**（私有）
5. 点击 **Create repository**

**第二步：上传代码到 GitHub**

在终端执行（需要先安装 Git）：

```bash
cd web-admin

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit"

# 添加远程仓库（替换 YOUR_USERNAME 为您的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/clover-web-admin.git

# 推送
git branch -M main
git push -u origin main
```

**第三步：在 CloudBase 配置自动化部署**

1. 进入 [CloudBase 控制台](https://console.cloudbase.net/)
2. 点击左侧 **静态网站托管**
3. 点击 **导入 Git 仓库**
4. 选择 **GitHub**
5. 授权 GitHub 账号
6. 选择仓库 `clover-web-admin`
7. 配置构建：
   - 构建命令：`npm install && npm run build`
   - 输出目录：`dist`
8. 点击 **部署**

**完成！** 每次您向 GitHub 推送代码，CloudBase 会自动构建并部署。

---

## 数据库权限配置

在 CloudBase 控制台 → 云数据库 → 权限设置中，将以下集合设置为 **"所有用户可读"**：

- `activities`
- `registrations`
- `form_submissions`
- `profiles`

---

## 项目结构

```
web-admin/
├── index.html
├── package.json
├── vite.config.js
├── cloudbase-config.json    # CloudBase Framework 配置
├── .gitignore
└── src/
    ├── main.js
    ├── App.vue
    ├── cloud.js            # CloudBase 配置（需填写环境ID）
    ├── router/index.js
    ├── views/
    │   ├── ActivityList.vue
    │   ├── UserData.vue
    │   ├── UserList.vue
    │   ├── UserDetail.vue
    │   └── Backup.vue
    └── styles/common.css
```

---

## 技术栈

- Vue 3 + Composition API
- Vue Router 4
- Element Plus
- Vite 5
- CloudBase JS SDK