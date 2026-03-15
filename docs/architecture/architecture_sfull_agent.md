# SFullAgent 架构图

## 1. 类继承层次图

```mermaid
classDiagram
    direction TB

    class BaseAgentLoop {
        +provider: Provider
        +model: str
        +system: str
        +tools: list
        +tool_handlers: dict
        +max_tokens: int
        +max_rounds: int
        +arun(messages)
        +set_hook_delegate(delegate)
        +on_hook(hook, **payload)
    }

    class SFullAgent {
        +subagent_runner: SubagentRunner
        +task_manager: TaskManager
        +background_manager: BackgroundManager
        +message_bus: MessageBus
        +teammate_manager: TeammateManager
        +plan_gate: PlanGate
        +_hook_delegate: Any
        +set_hook_delegate(delegate)
        +on_hook(hook, **payload)
    }

    class SubagentRunner {
        +provider: Provider
        +model: str
        +run(prompt, agent_type)
    }

    class TaskManager {
        +tasks_dir: Path
        +create(title, description, assignee)
        +get(task_id)
        +update(task_id, **updates)
        +list(status)
    }

    class BackgroundManager {
        +executor: ThreadPoolExecutor
        +tasks: dict
        +run(command, timeout)
        +check(task_id)
    }

    class MessageBus {
        +inbox_dir: Path
        +send(to, content, from_)
        +broadcast(content, from_)
        +read(agent_name, clear)
    }

    class TeammateManager {
        +team_dir: Path
        +teammates: dict
        +spawn(name, role)
        +list()
        +idle(name)
        +claim(name)
    }

    class PlanGate {
        +pending_plans: dict
        +submit(plan)
        +review(plan_id, approve, feedback)
    }

    BaseAgentLoop <|-- SFullAgent
    SFullAgent *-- SubagentRunner
    SFullAgent *-- TaskManager
    SFullAgent *-- BackgroundManager
    SFullAgent *-- MessageBus
    SFullAgent *-- TeammateManager
    SFullAgent *-- PlanGate
```

## 2. 工具分类架构图

```mermaid
mindmap
  root((SFullAgent<br/>25个工具))
    基础工具
      bash
      read_file
      write_file
      edit_file
    Skill加载
      load_skill
      load_skill_reference
      load_skill_script
    Todo管理
      todo
      context_compact
    子代理
      subagent
    任务系统[s07]
      task_create
      task_get
      task_update
      task_list
    后台执行[s08]
      bg_run
      bg_check
    消息传递[s09]
      send_msg
      broadcast
      read_inbox
    队友管理[s09/s11]
      spawn_teammate
      list_teammates
      teammate_idle
      claim_work
    计划审批[s10]
      submit_plan
      review_plan
```

## 3. 组件交互流程图

```mermaid
flowchart TB
    subgraph User["用户交互层"]
        U[用户输入]
    end

    subgraph Agent["SFullAgent 核心"]
        S[SFullAgent]
        BL[BaseAgentLoop]
        P[Provider<br/>LLM调用]
    end

    subgraph Tools["工具层 (25个工具)"]
        direction TB
        T1[基础工具<br/>bash/read/write/edit]
        T2[Skill工具<br/>load_skill系列]
        T3[Todo工具<br/>todo/context_compact]
        T4[Subagent<br/>任务分解]
        T5[Task系统<br/>CRUD操作]
        T6[后台执行<br/>bg_run/bg_check]
        T7[消息传递<br/>send/broadcast/read]
        T8[队友管理<br/>spawn/claim/idle]
        T9[计划审批<br/>submit/review]
    end

    subgraph Storage["存储层"]
        D1[(.tasks<br/>任务数据)]
        D2[(.team<br/>队友数据)]
        D3[(.team/inbox<br/>消息数据)]
        D4[(skills<br/>技能文件)]
    end

    subgraph External["外部服务"]
        E1[LLM API<br/>DeepSeek/Claude]
        E2[文件系统]
    end

    U --> S
    S --> BL
    BL --> P
    P --> E1

    S --> T1
    S --> T2
    S --> T3
    S --> T4
    S --> T5
    S --> T6
    S --> T7
    S --> T8
    S --> T9

    T5 --> D1
    T7 --> D3
    T8 --> D2
    T2 --> D4
    T1 --> E2
    T6 --> E2
```

## 4. Agent 生命周期时序图

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as API服务器
    participant SA as SFullAgent
    participant P as Provider
    participant T as 工具层
    participant S as 存储层

    U->>API: 发送消息
    API->>SA: async_agent_loop(messages)
    SA->>SA: 构建工具列表(25个)
    SA->>SA: 设置 system prompt

    loop 对话循环 (max 25轮)
        SA->>P: chat_stream(messages, tools)
        P-->>SA: 返回 content/tool_calls

        alt 需要工具调用
            SA->>T: 调用工具
            T->>S: 读写数据
            S-->>T: 返回结果
            T-->>SA: 工具执行结果
            SA->>SA: 添加结果到 messages
        else 直接回复
            SA-->>API: 返回最终结果
        end
    end

    API-->>U: 返回响应
```

## 5. 功能演进路线图 (s01-s11)

```mermaid
timeline
    title SFullAgent 功能演进

    section s01-s02
        基础Agent : BaseAgentLoop
                  : WorkspaceOps
                  : 基础工具 (bash/read/write/edit)

    section s03
        Todo管理 : TodoManager
                 : todo 工具
                 : context_compact 工具

    section s04
        子代理 : SubagentRunner
               : subagent 工具
               : 任务分解

    section s05
        Skill系统 : SkillLoader
                  : load_skill 工具
                  : 渐进式加载

    section s06
        上下文压缩 : 自动token检测
                   : 历史消息摘要

    section s07
        任务系统 : TaskManager
                 : task_create/get/update/list
                 : 持久化存储

    section s08
        后台执行 : BackgroundManager
                 : bg_run/bg_check
                 : 线程池管理

    section s09
        消息系统 : MessageBus
                 : send_msg/broadcast/read_inbox
                 : TeammateManager

    section s10
        审批流程 : PlanGate
                 : submit_plan/review_plan
                 : ShutdownProtocol

    section s11
        团队协作 : spawn_teammate
                 : claim_work/teammate_idle
                 : 多Agent协作
```

## 6. 目录结构图

```mermaid
flowchart LR
    subgraph Root["项目根目录"]
        A[agents/]
        S[skills/]
        D1[.tasks/]
        D2[.team/]
        D3[.team/inbox/]
    end

    subgraph Agents["agents/"]
        B[base/]
        P[providers/]
        SA[s_full.py]
        direction TB
    end

    subgraph Base["agents/base/"]
        BL[abstract.py<br/>BaseAgentLoop]
        TO[toolkit.py<br/>@tool]
        WO[workspace.py<br/>WorkspaceOps]
    end

    subgraph Skills["skills/"]
        SK1[skill-a/]
        SK2[skill-b/]
        SK3[...]
    end

    A --> Agents
    A --> Skills
    Agents --> Base
    Root -.-> D1
    Root -.-> D2
    D2 -.-> D3
```

## 7. 工具调用决策树

```mermaid
flowchart TD
    A[用户请求] --> B{任务类型?}

    B -->|文件操作| C[bash/read/write/edit]
    B -->|使用技能| D[load_skill系列]
    B -->|多步骤任务| E[todo工具]
    B -->|复杂分解| F[subagent]
    B -->|长期任务| G[task_create/update]
    B -->|耗时命令| H[bg_run/check]
    B -->|团队协作| I[send_msg/broadcast]
    B -->|队友管理| J[spawn/claim/idle]
    B -->|计划审批| K[submit/review_plan]
    B -->|上下文管理| L[context_compact]

    C --> M[执行操作]
    D --> N[加载技能文档]
    E --> O[跟踪进度]
    F --> P[子代理执行]
    G --> Q[持久化存储]
    H --> R[后台线程]
    I --> S[消息队列]
    J --> T[队友状态]
    K --> U[审批流程]
    L --> V[压缩历史]

    M --> W[返回结果]
    N --> W
    O --> W
    P --> W
    Q --> W
    R --> W
    S --> W
    T --> W
    U --> W
    V --> W
```
