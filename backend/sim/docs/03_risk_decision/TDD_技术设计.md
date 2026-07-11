    # 风险决策 — TDD 技术设计文档

    - **技术负责人**：架构师
    - **版本**：v1.0
    - **数据库**：`sim_risk_decision`

    ## 一、总体架构

    ```mermaid
    graph LR
        subgraph 上游
            U[进件 loan_intake, 客户中心 CIF]
        end
        subgraph 风险决策 服务
            API[REST/gRPC API]
            SVC[Service Layer]
            DAL[Data Access Layer]
            MQ_P[MQ Producer]
        end
        subgraph 下游
            D[信贷核心 credit_core, 催收 collection]
        end
        U --> API
        API --> SVC
        SVC --> DAL
        SVC --> MQ_P
        DAL --> DB[(MySQL sim_risk_decision)]
        MQ_P --> D
    ```

    ## 二、技术选型

    | 层 | 技术 |
    |---|---|
    | 语言 | Java 17 / Spring Boot 3 |
    | 数据库 | MySQL 8.0（主从） |
    | 缓存 | Redis 7 |
    | MQ | RocketMQ 5 |
    | 网关 | Spring Cloud Gateway |
    | 监控 | Prometheus + Grafana + SkyWalking |
    | 部署 | Kubernetes |

    ## 三、数据模型

    表清单（DDL 见 `../../systems/03_risk_decision/schema.sql`）：

        rule_set : (详见 schema.sql)
    decision_log : (详见 schema.sql)
    model_score : (详见 schema.sql)
    blacklist : (详见 schema.sql)
    antifraud_event : (详见 schema.sql)
    risk_grade : (详见 schema.sql)
    policy_ref : (详见 schema.sql)

    ## 四、关键接口清单

    - `POST /risk-decision/...`
    - `GET  /risk-decision/...`
    - `PUT  /risk-decision/...`

    详细契约见 OpenAPI 附件。

    ## 五、关键算法/机制

    ### 5.1 唯一 ID 生成
    使用 Snowflake（或 UUID v7）保证全局唯一 & 时序单调。

    ### 5.2 状态机
    核心业务表状态流转：
    - 通过 `*_status_log` 表记录每次变更
    - 变更需经过状态机校验合法性

    ### 5.3 事件通知
    写事件到 RocketMQ Topic，下游消费。

    ## 六、部署 & 环境

    - dev / test / staging / prod
    - MySQL 主从
    - Pod 副本数：4

    ## 七、监控 & 告警

    | 监控项 | 阈值 |
    |---|---|
    | P95 读 | 150ms |
    | P95 写 | 500ms |
    | 错误率 | > 1% 告警 |
    | 连接池 | > 80% 告警 |

    ## 八、安全设计

    - TLS 1.3
    - 字段级加密（敏感数据）
    - RBAC
    - 全量审计

    ## 九、容量规划

    | 项 | 当前 | 3 年后 |
    |---|---|---|
    | QPS | 见基线 | 3–5x |
    | 存储 | 见基线 | 需分库分表 |

    ## 十、风险与降级

    - 依赖故障：熔断 + 降级
    - 数据库故障：主从切换
    - 缓存穿透：布隆过滤器

## 十一、系统架构关键决策

### 11.1 分层架构
- **接入层**：API Gateway，负责鉴权/限流/路由
- **业务层**：领域服务，纯业务逻辑
- **数据层**：Repository 模式封装 DAO
- **消息层**：MQ Producer/Consumer

### 11.2 数据一致性策略
- 同库跨表：本地事务
- 跨库跨系统：Saga 长事务 + 事件补偿
- 读写分离：读走从库（可能有 100ms 延迟）
- 强一致读：显式指定走主库

### 11.3 高可用
- 多可用区部署
- 自动故障切换
- 熔断限流（Sentinel）
- 全链路压测（每季度）

### 11.4 可观测性
- Metrics：Prometheus
- Tracing：SkyWalking
- Logs：ELK
- APM：全链路 trace

### 11.5 数据加密
- 传输：TLS 1.3
- 存储：字段级 + 表级 TDE
- KMS：托管密钥轮换

## 十二、生产环境规格

- 服务 Pod：4 replicas × 2 core / 4G RAM
- MySQL：主 8C32G，从 x 2
- Redis：3 主 3 从
- MQ：3 broker 集群
- 日均调用量：~ 100 万次
- 峰值 QPS：预留 3 倍容量

