# 记忆系统工作流程

## 自动记忆提取流程 (EXTRACT_MEMORIES)

### 触发条件

```
对话结束时
  └─> 检查 feature('EXTRACT_MEMORIES') 是否启用
      └─> 检查 isExtractModeActive()
          └─> 启动后台代理提取记忆
```

### 提取过程

```
1. 分析对话历史
   └─> 识别用户角色信息
   └─> 检测反馈（纠正/确认）
   └─> 发现项目上下文
   └─> 记录外部系统引用

2. 去重检查
   └─> 对比现有记忆
   └─> 跳过已记录的信息

3. 生成记忆文件
   └─> 选择合适的记忆类型
   └─> 撰写 frontmatter
   └─> 写入 .md 文件

4. 更新索引
   └─> 在 MEMORY.md 添加条目
```

### 代码入口

```typescript
// src/services/extractMemories/extractMemories.ts
export async function extractMemories(
  sessionId: string,
  messages: Message[],
): Promise<void> {
  // 分析消息提取记忆
  // 写入记忆目录
}
```

## 记忆加载流程

### 系统提示构建

```
会话启动
  └─> loadMemoryPrompt()
      ├─> 检查 isAutoMemoryEnabled()
      │   └─> 环境变量检查
      │   └─> 设置检查
      │   └─> 远程配置检查
      │
      ├─> 确定记忆模式
      │   ├─> KAIROS 模式 → 每日日志
      │   ├─> TEAMMEM 模式 → 组合提示
      │   └─> 标准模式 → 自动记忆
      │
      ├─> buildMemoryLines()
      │   └─> 生成行为指南
      │   └─> 包含四种记忆类型说明
      │   └─> 包含保存/使用指南
      │
      ├─> 读取 MEMORY.md
      │   └─> truncateEntrypointContent()
      │       └─> 限制 200 行 / 25KB
      │
      └─> 合并到系统提示
```

### 代码入口

```typescript
// src/memdir/memdir.ts
export async function loadMemoryPrompt(): Promise<string | null> {
  // 检查启用状态
  // 构建记忆提示
  // 返回系统提示内容
}
```

## 团队记忆同步流程 (TEAMMEM)

### 文件监控

```
文件系统事件
  └─> watcher.ts
      ├─> 检测文件变更
      ├─> secretScanner.ts 扫描敏感信息
      └─> 触发同步
```

### 同步过程

```
本地变更
  └─> 验证变更
      ├─> 检查文件格式
      ├─> 扫描敏感信息
      └─> 发送到团队存储

远程变更
  └─> 接收更新
      ├─> 合并到本地
      └─> 更新 MEMORY.md
```

## 记忆压缩流程 (COMPACT)

### 触发条件

```
上下文接近容量上限
  └─> 自动检测
      └─> 启动压缩
```

### 压缩类型

1. **Micro Compact**
   - 轻量级摘要
   - 保留关键决策和结果

2. **Session Compact**
   - 完整会话摘要
   - 在对话结束时执行

3. **Auto Compact**
   - 自动触发
   - 基于令牌使用量

### 代码入口

```typescript
// src/services/compact/compact.ts
export async function compactSession(
  sessionId: string,
): Promise<CompactResult> {
  // 压缩会话历史
  // 生成摘要
}
```

## /remember 技能流程

### 用户触发

```
用户输入 /remember
  └─> registerRememberSkill
      └─> 执行记忆审查流程
```

### 审查步骤

```
1. 收集所有记忆层
   ├─> 读取 CLAUDE.md
   ├─> 读取 CLAUDE.local.md
   ├─> 读取 auto-memory
   └─> 检查 team memory

2. 分类自动记忆
   ├─> CLAUDE.md 候选（项目约定）
   ├─> CLAUDE.local.md 候选（个人偏好）
   ├─> Team memory 候选（组织知识）
   └─> 保留在 auto-memory（临时内容）

3. 识别问题
   ├─> 重复条目
   ├─> 过时信息
   └─> 冲突内容

4. 生成报告
   ├─> Promotions（晋升建议）
   ├─> Cleanup（清理建议）
   ├─> Ambiguous（需用户确认）
   └─> No action（无需改动）
```

## 记忆搜索流程

### 本地搜索

```
用户查询
  └─> findRelevantMemories()
      ├─> 扫描记忆目录
      ├─> 匹配关键词
      └─> 返回相关记忆
```

### 代码入口

```typescript
// src/memdir/findRelevantMemories.ts
export async function findRelevantMemories(
  query: string,
  memoryDir: string,
): Promise<Memory[]> {
  // 搜索相关记忆
}
```

## 日常日志流程 (KAIROS)

### 助手模式

```
长期运行会话
  └─> 每日日志模式
      ├─> 追加到日期命名文件
      │   └─> logs/YYYY/MM/YYYY-MM-DD.md
      ├─> 格式：时间戳项目符号
      └─> /dream 技能夜间整理
          └─> 提炼为 topic 文件
          └─> 更新 MEMORY.md
```

### 与普通模式的区别

| 方面 | 普通模式 | KAIROS 模式 |
|------|----------|-------------|
| 写入目标 | MEMORY.md + topic 文件 | 每日日志文件 |
| 组织方式 | 主题分类 | 时间顺序 |
| 整理时机 | 实时 | 夜间批量 |
| 适用场景 | 常规开发 | 长期助手会话 |

## 错误处理

### 常见问题

1. **目录不存在**
   - `ensureMemoryDirExists()` 自动创建

2. **文件读取失败**
   - 静默处理，返回空内容

3. **敏感信息检测**
   - `secretScanner.ts` 拦截
   - 阻止包含密钥的文件保存

4. **路径遍历攻击**
   - `validateMemoryPath()` 验证
   - 拒绝相对路径和危险路径

### 监控与日志

```typescript
// 记忆目录加载事件
logEvent('tengu_memdir_loaded', {
  content_length: byteCount,
  line_count: lineCount,
  was_truncated: boolean,
  memory_type: 'auto' | 'team' | 'agent'
})

// 记忆禁用事件
logEvent('tengu_memdir_disabled', {
  disabled_by_env_var: boolean,
  disabled_by_setting: boolean
})
```
