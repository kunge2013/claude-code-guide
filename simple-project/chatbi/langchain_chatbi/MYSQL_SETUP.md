# MySQL 数据库配置说明

## 概述

`execution_node` 现在支持查询 MySQL 数据库。通过配置环境变量，可以将 ChatBI 连接到真实的 MySQL 数据库执行 SQL 查询。

## 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# MySQL 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=chatbi
```

### 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MYSQL_HOST` | MySQL 服务器地址 | localhost |
| `MYSQL_PORT` | MySQL 端口 | 3306 |
| `MYSQL_USER` | 数据库用户名 | root |
| `MYSQL_PASSWORD` | 数据库密码 | (无) |
| `MYSQL_DATABASE` | 数据库名称 | chatbi |

## 使用方式

### 1. 在工作流中使用

```python
import asyncio
from langchain_chatbi.db.mysql_db import create_mysql_connection
from langchain_chatbi.graph.state import ChatBIState
from langchain_chatbi.graph.nodes import execution_node


async def main():
    # 创建 MySQL 连接
    mysql_conn = create_mysql_connection()

    # 准备状态
    state: ChatBIState = {
        "question": "显示销售额前10的产品",
        "db": mysql_conn,  # 传入数据库连接
        "generated_sql": "SELECT * FROM products ORDER BY sales DESC LIMIT 10",
        # ... 其他状态字段
    }

    # 执行查询
    result = await execution_node(state)
    print(result["query_result"])

    # 关闭连接
    mysql_conn.disconnect()


asyncio.run(main())
```

### 2. 直接使用 MySQLConnection

```python
from langchain_chatbi.db.mysql_db import create_mysql_connection

# 创建连接
conn = create_mysql_connection()

# 执行查询
result = conn.run("SELECT * FROM users WHERE id = %s", (1,))
print(result)

# 获取表结构
tables = conn.get_all_tables()
schema = conn.get_table_schema("users")

# 关闭连接
conn.disconnect()
```

### 3. 运行 Demo

```bash
python demos/mysql_execution_demo.py
```

## 功能特性

### 核心功能

- **连接管理**: 自动连接池和连接复用
- **查询执行**: 支持 SELECT、INSERT、UPDATE、DELETE
- **参数化查询**: 防止 SQL 注入
- **结果转换**: 自动转换为字典列表
- **错误处理**: 捕获 MySQL 错误用于 SQL 修正

### 高级功能

```python
# 获取所有表
tables = conn.get_all_tables()

# 获取表结构
schema = conn.get_table_schema("table_name")
# 返回: {"name": "table_name", "columns": [...]}

# 获取所有表结构
all_schemas = conn.get_all_schemas()

# 批量执行
conn.run_many("INSERT INTO users (name) VALUES (%s)", [("Alice",), ("Bob",)])

# 测试连接
is_connected = conn.test_connection()
```

## 测试

运行 MySQL 连接测试：

```bash
# 运行所有集成测试
pytest tests/test_mysql_connection.py -v

# 只运行连接测试
pytest tests/test_mysql_connection.py::TestMySQLConnection::test_connect_to_database -v
```

**注意**: 测试需要真实的 MySQL 数据库连接。

## 错误处理

当 SQL 执行失败时，`execution_node` 会：

1. 捕获 MySQL 错误
2. 将错误信息存储在 `state["sql_error"]` 中
3. 工作流会返回 `sql_node` 进行错误修正
4. 最多重试 3 次

```python
# 错误示例
{
    "sql_error": "MySQL Error: Table 'chatbi.products' doesn't exist",
    "query_result": None
}
```

## 安装依赖

```bash
# 安装 pymysql
pip install pymysql

# 或使用项目依赖
pip install -e .
```

## 安全建议

1. **不要在代码中硬编码密码** - 始终使用环境变量
2. **使用只读用户** - 对于查询场景，建议使用只读权限的数据库用户
3. **限制连接** - 在生产环境中使用连接池限制最大连接数
4. **SSL 连接** - 生产环境建议启用 SSL

```sql
-- 创建只读用户示例
CREATE USER 'chatbi_readonly'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON chatbi.* TO 'chatbi_readonly'@'localhost';
FLUSH PRIVILEGES;
```

## 故障排查

### 连接失败

```python
# 检查连接
conn = create_mysql_connection()
try:
    conn.test_connection()
except Exception as e:
    print(f"Connection failed: {e}")
    # 检查:
    # 1. MySQL 服务是否运行
    # 2. 主机和端口是否正确
    # 3. 用户名和密码是否正确
    # 4. 数据库是否存在
```

### SQL 执行错误

```python
# 查看详细错误
result = await execution_node(state)
if result.get("sql_error"):
    print(f"SQL Error: {result['sql_error']}")
    # 检查:
    # 1. 表名是否存在
    # 2. 列名是否正确
    # 3. SQL 语法是否正确
```

### 中文乱码

确保使用 `utf8mb4` 字符集：

```python
# MySQLConnection 默认使用 utf8mb4
conn = create_mysql_connection()
# 或在连接时指定
conn = MySQLConnection(
    host="localhost",
    charset="utf8mb4"
)
```

## 示例数据库

创建测试数据库：

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS chatbi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE chatbi;

-- 创建示例表
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2),
    sales DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    customer_id INT,
    total_amount DECIMAL(10, 2),
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 插入示例数据
INSERT INTO products (name, category, price, sales) VALUES
    ('Laptop', 'Electronics', 999.99, 15000.00),
    ('Mouse', 'Electronics', 29.99, 4500.00),
    ('Keyboard', 'Electronics', 79.99, 3200.00),
    ('Monitor', 'Electronics', 299.99, 8900.00),
    ('Headphones', 'Electronics', 149.99, 2100.00);
```

## 完整示例

```python
import asyncio
from dotenv import load_dotenv
from langchain_chatbi.db.mysql_db import create_mysql_connection

load_dotenv()


async def query_example():
    conn = create_mysql_connection()

    try:
        # 查询销售额最高的产品
        result = conn.run("""
            SELECT name, category, sales
            FROM products
            ORDER BY sales DESC
            LIMIT 5
        """)

        print("Top 5 Products by Sales:")
        for row in result:
            print(f"  {row['name']}: ${row['sales']}")

    finally:
        conn.disconnect()


asyncio.run(query_example())
```
