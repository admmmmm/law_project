# 检察侦查画像模型 Demo

这是项目正式 demo 的前端工程起点。

## 技术选择

- 前端框架：React
- 构建工具：Vite
- 图标库：lucide-react
- 当前数据：前端 mock 数据
- 后续接口：可替换为后端 API

选择 React + Vite 的原因：

- 符合赛题“前端基于现代框架实现交互设计”的要求。
- 适合快速做出可演示的单页应用。
- 后续可以平滑接入后端接口、图谱服务和报告生成服务。

## 当前页面

- 总览
- 证据接入
- 图谱穿透
- 分析碰撞
- 信息画像
- 报告建议

## 运行方式

在网络和 npm 权限可用时：

```powershell
cd C:\Users\adm14\Desktop\law_project\demo
npm.cmd install
npm.cmd run dev
```

然后访问：

```text
http://127.0.0.1:5173
```

## 临时预览

如果暂时不能安装依赖，可以直接打开：

```text
C:\Users\adm14\Desktop\law_project\demo\static-preview.html
```

这个静态页不代表最终技术栈，只用于快速预览 demo 的信息架构和交互流程。

## 后续接入方向

- 将 `mockData.js` 替换为后端接口返回数据。
- 将图谱 SVG 替换为图谱可视化组件。
- 接入证据上传与解析接口。
- 接入专题报告和画像生成接口。
- 增加节点点击、筛选、报告导出等演示交互。
