# 项目瘦身报告

> 日期: 2026-03-31
> 项目: learn-claude-code-my

---

## 📊 当前状况

| 指标 | 数值 |
|------|------|
| **总体积** | 2.2 GB |
| **Python 文件** | 65+ 个 |
| **TypeScript 文件** | 168 个 |
| **大文件 (>1MB)** | 127 个 |

---

## 🎯 瘦身方案

### 第一阶段: 清理缓存 (预计节省 ~1GB)

#### 1. Next.js 构建缓存
- **路径**: `web/.next/`
- **大小**: ~950 MB
- **说明**: Next.js 开发和生产构建缓存
- **操作**: ✅ 可安全删除，重新构建时自动生成

#### 2. Python 字节码缓存
- **路径**: `**/__pycache__/`
- **大小**: ~50 MB
- **说明**: Python 编译后的字节码
- **操作**: ✅ 可安全删除

#### 3. 测试和类型检查缓存
- **路径**: `.pytest_cache/`, `.mypy_cache/`
- **大小**: ~10 MB
- **操作**: ✅ 可安全删除

**执行命令**:
```powershell
# Windows PowerShell
Remove-Item -Recurse -Force web/.next
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force .pytest_cache
Remove-Item -Recurse -Force .mypy_cache
```

---

### 第二阶段: 合并重复文件 (预计节省 ~100KB)

#### 重复的 Session 数据
```
web/src/data/
├── annotations/      # 包含完整数据
│   ├── s01.json    (6.5KB)
│   ├── s02.json    (6.8KB)
│   └── ...
└── scenarios/        # 包含简化数据 (可删除)
    ├── s01.json    (1.6KB)
    ├── s02.json    (1.5KB)
    └── ...
```

**建议**: 删除 `scenarios/` 目录，统一使用 `annotations/`

---

### 第三阶段: 清理未使用代码 (预计节省 ~500KB)

#### 1. 旧的运行时备份
- **文件**: `backup_runtime.py`
- **大小**: ~12KB
- **状态**: 已过时，新架构在 `core/agent/runtimes/`

#### 2. 临时文件
- **模式**: `.tmp_*.py`
- **说明**: 运行时生成的临时检查文件

#### 3. 重复的类型定义
```
web/src/
├── stores/dialog.ts      # Store 实现
└── types/dialog.ts       # 类型定义 (可合并)
```

**建议**: 合并重复的类型定义

---

## 🚀 快速清理

### 方式一: 使用脚本 (推荐)

```powershell
# 预览模式 (查看可清理内容)
PowerShell -ExecutionPolicy Bypass -File cleanup-project.ps1 -DryRun

# 执行清理
PowerShell -ExecutionPolicy Bypass -File cleanup-project.ps1

# 强制清理 (不提示确认)
PowerShell -ExecutionPolicy Bypass -File cleanup-project.ps1 -Force
```

### 方式二: 手动清理

```bash
# 1. 删除 Next.js 缓存
cd web
rm -rf .next

# 2. 删除 Python 缓存
find .. -type d -name "__pycache__" -exec rm -rf {} +

# 3. 删除测试缓存
rm -rf ../.pytest_cache
rm -rf ../.mypy_cache

# 4. 删除重复数据
rm -rf src/data/scenarios

# 5. 删除临时文件
find .. -name ".tmp_*" -delete
```

---

## 📈 预期效果

| 清理阶段 | 预计节省 | 清理后大小 |
|----------|----------|------------|
| 缓存清理 | ~1.0 GB | ~1.2 GB |
| 重复文件 | ~100 KB | ~1.2 GB |
| 未使用代码 | ~500 KB | ~1.2 GB |
| **总计** | **~1.0 GB** | **~1.2 GB** |

**瘦身比例**: 约 45%

---

## ⚠️ 注意事项

1. **.next 目录**: 删除后需要重新运行 `npm run dev` 或 `npm run build`
2. **Python 缓存**: 删除后首次导入模块会稍慢（重新编译）
3. **不要删除**:
   - `node_modules/` (需要 `npm install` 重装)
   - `.git/` (版本历史)
   - 源代码文件

---

## ✅ 清理后验证

```bash
# 1. 检查项目大小
du -sh .

# 2. 验证前端构建
cd web && npm run dev

# 3. 验证后端启动
cd .. && python main.py

# 4. 运行测试
python -m pytest tests/ -v
```

---

## 🔄 持续维护建议

1. **.gitignore 更新**:
   ```gitignore
   # 构建产物
   .next/
   __pycache__/
   .pytest_cache/
   .mypy_cache/
   *.tmp_*
   backup_*.py
   ```

2. **定期清理**: 每月执行一次清理脚本

3. **CI/CD 优化**: 在构建流程中自动清理缓存

---

**报告生成时间**: 2026-03-31
**预计清理时间**: 2-3 分钟
