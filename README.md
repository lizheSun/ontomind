# OntoMind — AI 驱动本体自动构建平台

构建一个以 **AI 驱动** 为核心的 **本体自动构建平台**，通过五层产品架构实现从数据感知到智能决策、再到业务执行与应用的完整闭环。

## 五层架构

| 层级 | 定位 | 核心能力 |
|------|------|---------|
| **感知层** | 信息入口 | 数据源连接器、文档解析、数据仓库、代码库接入 |
| **认知层** | 知识提炼 | 本体图谱构建、语义理解、知识推理 |
| **决策层** | 策略生成 | 特征挖掘、ML模型训练、规则策略引擎 |
| **执行层** | 策略下发 | 策略分发引擎、风控/营销系统适配器 |
| **应用层** | 用户产品 | AIbi 智能分析、数据可视化、策略工作台 |

## 快速开始

```bash
# 克隆项目
git clone git@github.com:lizheSun/ontomind.git
cd ontomind

# 查看项目计划
cat docs/project-plan.md
```

## 技术栈

- **前端**：React + TypeScript + Ant Design
- **后端**：Python (FastAPI) + Java (Spring Boot)
- **AI**：LangChain + LLM
- **知识图谱**：Neo4j
- **向量数据库**：Milvus

## 项目结构

详见 [docs/project-plan.md](docs/project-plan.md)

## 开发路线图

- Phase 1：感知层（1-3月）
- Phase 2：认知层（3-6月）
- Phase 3：决策层（6-9月）
- Phase 4：执行层（9-11月）
- Phase 5：应用层（11-14月）

## License

MIT
