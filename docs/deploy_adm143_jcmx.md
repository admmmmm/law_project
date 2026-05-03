# adm143.xyz/jcmx 部署说明

目标访问地址：

```text
https://adm143.xyz/jcmx/
```

当前正式链路是：

```text
浏览器
  -> Caddy 监听 80/443
  -> /jcmx/ 静态文件：frontend/dist
  -> /jcmx/api/* 反代到 127.0.0.1:8000
  -> FastAPI 后端
```

不要再使用 `serve.py:8080`。那个只是临时代理，容易和 Caddy、Vite dev server 串。

## 1. 启动后端

```powershell
cd C:\Users\adm14\Desktop\law_project\backend
C:\Users\adm14\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

检查：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health -UseBasicParsing
```

## 2. 构建前端到 /jcmx/ 子路径

必须带 `VITE_BASE_PATH=/jcmx/`，否则资源会生成成 `/assets/...`，挂到域名子路径时会白屏或串项目。

```powershell
cd C:\Users\adm14\Desktop\law_project\frontend
$env:VITE_BASE_PATH='/jcmx/'
npm run build
```

构建后检查 `frontend/dist/index.html`，里面应该是：

```html
src="/jcmx/assets/..."
href="/jcmx/assets/..."
```

## 3. 启动或重载 Caddy

Caddy 配置文件：

```text
C:\Users\adm14\Desktop\law_project\Caddyfile.jcmx
```

启动：

```powershell
cd C:\Users\adm14\Desktop\law_project
caddy run --config Caddyfile.jcmx
```

如果 Caddy 已经在跑，重载：

```powershell
cd C:\Users\adm14\Desktop\law_project
caddy reload --config Caddyfile.jcmx
```

## 4. 检查端口

正常状态应至少看到：

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 80,443,8000 } |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

期望：

- `80/443`：Caddy
- `8000`：FastAPI 后端

不需要：

- `8080`：旧 `serve.py` 临时代理
- `5173`：Vite 开发服务器，公网部署不需要

## 5. 外网检查

```powershell
Invoke-WebRequest https://adm143.xyz/jcmx/ -UseBasicParsing
Invoke-WebRequest https://adm143.xyz/jcmx/api/v1/health -UseBasicParsing
```

第二条应返回类似：

```json
{"status":"ok","env":"dev"}
```

## 当前故障原因

这次混乱主要有两点：

1. 前端之前按根路径 `/` 构建，`index.html` 里资源是 `/assets/...`，但实际部署在 `/jcmx/` 子路径。
2. 同时存在 Caddy、Vite dev server、`serve.py:8080` 三条入口，容易打开错入口或串到别的项目。

现在保留 Caddy 作为唯一公网入口。
