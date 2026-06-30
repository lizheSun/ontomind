"""数据源业务服务."""
from typing import Optional
import pymysql
from sqlalchemy.orm import Session
from app.db.repositories.data_source_repo import DataSourceRepository
from app.schemas.data_source_schema import DataSourceCreate, DataSourceUpdate
from app.core.exceptions import ConflictException, NotFoundException


class DataSourceService:
    """数据源管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = DataSourceRepository(db)

    def create(self, data: DataSourceCreate) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("数据源名称已存在", code="DS_NAME_EXISTS")
        ds = self.repo.create(data.model_dump())
        self.db.commit()
        return ds.to_response_dict()

    def get(self, ds_id: int) -> dict:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")
        return ds.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        sources = self.repo.get_all(skip, limit)
        return [s.to_response_dict() for s in sources]

    def update(self, ds_id: int, data: DataSourceUpdate) -> dict:
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != ds.name:
            if self.repo.name_exists(update_data["name"], exclude_id=ds_id):
                raise ConflictException("数据源名称已存在", code="DS_NAME_EXISTS")
        updated = self.repo.update(ds_id, update_data)
        self.db.commit()
        return updated.to_response_dict()

    def delete(self, ds_id: int) -> bool:
        if not self.repo.delete(ds_id):
            raise NotFoundException(f"数据源不存在: {ds_id}")
        self.db.commit()
        return True

    def test_connection(self, ds_id: int) -> dict:
        """测试数据源连接"""
        ds = self.repo.get_by_id(ds_id)
        if not ds:
            raise NotFoundException(f"数据源不存在: {ds_id}")

        source_type = ds.source_type.lower()
        host = ds.host
        port = ds.port
        username = ds.username
        password = ds.password
        database = ds.database
        charset = ds.charset or "utf8mb4"

        db_drivers = {"mysql", "doris", "clickhouse"}

        if source_type in db_drivers:
            return self._test_mysql(host, port, username, password, database, charset)
        elif source_type == "postgresql":
            return {"success": False, "message": "PostgreSQL 连接测试暂未实现，请安装 psycopg2 后重试"}
        elif source_type in ("kafka", "mongodb", "redis"):
            return {"success": False, "message": f"{source_type} 连接测试暂未实现"}
        elif source_type in ("api", "file", "unknown"):
            return {"success": True, "message": f"{source_type} 类型无需连接测试，配置已保存"}
        else:
            return {"success": False, "message": f"暂不支持 {source_type} 类型的数据源连接测试"}

    def _test_mysql(self, host, port, username, password, database, charset) -> dict:
        """测试 MySQL 协议连接（适用于 MySQL/Doris/ClickHouse）"""
        if not host:
            return {"success": False, "message": "主机地址不能为空"}
        try:
            conn = pymysql.connect(
                host=host,
                port=port or 3306,
                user=username or "",
                password=password or "",
                database=database or "",
                charset=charset,
                connect_timeout=10,
            )
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return {
                "success": True,
                "message": f"连接成功！服务器版本: {version}",
                "details": f"主机: {host}:{port}, 数据库: {database or '(未指定)'}, 字符集: {charset}",
            }
        except pymysql.err.OperationalError as e:
            error_code = e.args[0] if e.args else 0
            error_msg = e.args[1] if len(e.args) > 1 else str(e)
            return {
                "success": False,
                "message": f"连接失败: [{error_code}] {error_msg}",
                "details": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "details": str(e),
            }

    def update_status(self, ds_id: int, status: str):
        """更新数据源状态"""
        self.repo.update(ds_id, {"status": status})
        self.db.commit()
