# 使用 uv 创建虚拟环境、反推依赖并安装

本文档记录在 Windows 下，使用 `uv` 完成以下流程：

1. 创建 Python 虚拟环境
2. 从项目源码反推依赖（基于 import）
3. 下载并安装反推得到的依赖

## 1. 前置条件

- 已安装 Python（建议 3.10+）
- 已安装 `uv`

检查命令：

```powershell
uv --version
```

如果提示找不到 `uv`，可先安装：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. 创建虚拟环境

在项目根目录执行：

```powershell
uv venv .venv
```

激活环境（可选）：

```powershell
.\.venv\Scripts\Activate.ps1
```

说明：后续命令即使不激活，也可以通过 `--python .venv\Scripts\python.exe` 显式指定虚拟环境解释器。

## 3. 安装依赖反推工具

这里使用 `pipreqs` 从源码 import 反推出依赖列表：

```powershell
uv pip install --python .venv\Scripts\python.exe pipreqs
```

## 4. 反推依赖

在项目根目录执行（输出到独立文件，避免覆盖现有 `requirements.txt`）：

```powershell
uv run --python .venv\Scripts\python.exe pipreqs . --force --savepath requirements.txt --ignore .venv,web
```

参数说明：

- `--savepath requirements.inferred.txt`：将反推结果输出到新文件
- `--ignore .venv,web`：忽略虚拟环境目录和前端目录，减少误识别
- `--force`：允许覆盖已有输出文件

## 5. 安装反推得到的依赖

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## 6. 一条命令跑完整流程（可选）

```powershell
uv venv .venv; `
uv pip install --python .venv\Scripts\python.exe pipreqs; `
uv run --python .venv\Scripts\python.exe pipreqs . --force --savepath requirements.txt --ignore .venv,web; `
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

## 7. 本仓库一次实际执行结果

本次执行后，`requirements.txt` 内容如下：

```txt
anthropic==0.84.0
langchain_core==1.2.17
langchain_openai==1.1.10
pyodbc==5.3.0
python-dotenv==1.2.2
```

注意：`pipreqs` 通过源码 import 反推依赖，可能出现“版本偏高”或“可选依赖也被纳入”的情况。建议将 `requirements.inferred.txt` 与项目已有 `requirements.txt` 对比后，再决定最终依赖清单。

