---
name: airflow
description: Apache Airflow任务编排平台 — 45k⭐，DAG有向无环图，调度+监控+日志，Python原生，500+Providers扩展。触发：Airflow、DAG调度、定时任务编排、ETL流程、工作流监控。
version: 1.0.0
tags: [workflow, scheduler, DAG, ETL, python, apache]
triggers: ["Airflow", "airflow", "DAG调度", "定时任务编排", "ETL", "任务编排", "有向无环图"]
---

# Apache Airflow 架构设计参考

## 核心定位
Airflow = Apache开源的**任务编排平台**（45k⭐），核心用Python定义DAG（有向无环图），实现定时调度+执行监控+错误重试+日志追踪。适用于：**ETL流水线、定时数据同步、定时报告生成**。

## 核心概念

```
DAG（有向无环图）
    ├── tasks（任务）：具体的操作单元
    ├── dependencies（依赖）：任务间的执行顺序
    └── schedule_interval（调度周期）：何时触发

核心流程：schedule → trigger → execute → monitor → retry
```

## 三个关键组件

| 组件 | 职责 |
|------|------|
| **Scheduler** | 监控DAG + 触发Task执行 |
| **Executor** | 真正执行Task（Local/Sequential/Celery/Kubernetes） |
| **Web Server** | 可视化DAG、任务状态、日志 |
| **Metadata DB** | 存储所有元数据（PostgreSQL/MySQL） |
| **Triggerer** | 支持Async任务的异步触发（Airflow 2.x） |

## DAG编写（Python原生）

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# 1. 定义DAG
with DAG(
    dag_id="daily_etl_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule_interval="0 3 * * *",  # 每天凌晨3点
    catchup=False,
    tags=["etl", "daily"],
) as dag:

    # 2. 定义Task
    extract = BashOperator(
        task_id="extract_data",
        bash_command="python /scripts/extract.py",
    )

    def transform(**context):
        import json
        data = context["ti"].xcom_pull(task_ids="extract_data")
        # 清洗转换逻辑
        return {"cleaned": data, "rows": 1000}

    transform_task = PythonOperator(
        task_id="transform_data",
        python_callable=transform,
        provide_context=True,
    )

    load = BashOperator(
        task_id="load_data",
        bash_command="python /scripts/load.py {{ ti.xcom_pull(task_ids='transform_data') }}",
    )

    # 3. 定义执行顺序
    extract >> transform_task >> load
```

## 常用Operator

```python
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.http import HttpOperator
from airflow.operators.mysql import MySqlOperator
from airflow.sensors.http_sensor import HttpSensor
from airflow.sensors.time_sensor import TimeSensor

# Python任务
PythonOperator(task_id="process", python_callable=my_func)

# 条件分支
BranchPythonOperator(
    task_id="branch",
    python_callable=lambda: "task_a" if condition else "task_b",
)

# HTTP请求
HttpOperator(task_id="call_api", http_conn_id="my_api", ...)

# 传感器（等待条件触发）
HttpSensor(task_id="wait_for_data", http_conn_id="api", ...)
```

## XCom（跨Task数据传递）

```python
# Task A 推送数据
def push_data(**context):
    context["ti"].xcom_push(key="result", value={"total": 100})

# Task B 拉取数据
def pull_data(**context):
    result = context["ti"].xcom_pull(task_ids="push_task", key="result")
    print(f"Received: {result}")
```

## Trigger规则（任务触发条件）

```python
from airflow.utils.trigger_rule import TriggerRule

task = PythonOperator(
    task_id="report",
    python_callable=send_report,
    trigger_rule=TriggerRule.ALL_SUCCESS,  # 所有上游成功才执行
    # 可选：ALL_FAILED / ONE_FAILED / ONE_SUCCESS / NONE_FAILED / ALL_DONE
)
```

## Docker Compose部署

```yaml
# docker-compose.yaml
version: '3'
services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow

  redis:
    image: redis:7

  airflow-webserver:
    image: apache/airflow:2.9
    command: webserver
    ports: ["8080:8080"]
    environment:
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      POSTGRES_HOST: postgres
    depends_on: [postgres, redis]
```

```bash
docker-compose up -d
# 访问 http://localhost:8080
# 默认：airflow / airflow
```

## 与本项目的契合点

| Airflow特性 | 借鉴场景 |
|------------|---------|
| DAG调度 | 复杂任务的依赖图管理 |
| Python原生 | 用Python定义任务比YAML更灵活 |
| Trigger规则 | 任务依赖和失败策略 |
| XCom | 跨任务数据传递 |
| Catchup | 补跑历史未执行的任务 |
| Providers | 500+扩展（GitHub/Slack/微信等） |
| 调度周期 | Cron表达式 + Timetable自定义 |

## 坑/注意事项

1. **DAG必须是无环图**：有环会导致调度器死循环
2. **任务幂等性**：任务可能被重跑，设计时保证重复执行安全
3. **长任务处理**：>1小时的任务需要设置retries和timeout
4. **并发控制**：max_active_tasks限制并行度，避免资源耗尽
5. **PostgreSQL必须**：生产环境必须用PostgreSQL，不要用SQLite
