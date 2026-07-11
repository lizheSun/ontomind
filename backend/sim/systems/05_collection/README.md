# collection 系统

- **数据库**: `sim_collection`
- **schema**: `schema.sql`
- **种子数据**: `seed_data/`
- **产品文档**: `../../docs/05_collection/`

## 关键表

参见 `schema.sql` COMMENT 注释。

## 数据量（截至生成时）

```bash
mysql -u root -e "
SELECT table_name, table_rows
FROM information_schema.tables
WHERE table_schema='sim_collection'"
```

## 相关系统

见根 README.md 主线时序图。
