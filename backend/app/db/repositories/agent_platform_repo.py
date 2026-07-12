"""节点连接与发现持久化封装。"""
from sqlalchemy.orm import Session

from app.db.models.compute_node_model import ComputeNode
from app.db.models.discovery_item_model import DiscoveryItem
from app.db.models.discovery_run_model import DiscoveryRun
from app.db.models.node_connection_model import NodeConnection


class AgentPlatformRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_nodes(self, skip: int = 0, limit: int = 100) -> list[ComputeNode]:
        return self.db.query(ComputeNode).order_by(ComputeNode.id).offset(skip).limit(limit).all()

    def get_node(self, node_id: int) -> ComputeNode | None:
        return self.db.query(ComputeNode).filter(ComputeNode.id == node_id).first()

    def get_connection(self, node_id: int) -> NodeConnection | None:
        return (
            self.db.query(NodeConnection)
            .filter(NodeConnection.node_id == node_id, NodeConnection.enabled.is_(True))
            .first()
        )

    def create_node(self, node_data: dict, connection_data: dict) -> ComputeNode:
        node = ComputeNode(**node_data)
        self.db.add(node)
        self.db.flush()
        self.db.add(NodeConnection(node_id=node.id, **connection_data))
        self.db.flush()
        return node

    def create_run(self, **data) -> DiscoveryRun:
        run = DiscoveryRun(**data)
        self.db.add(run)
        self.db.flush()
        return run

    def create_item(self, **data) -> DiscoveryItem:
        item = DiscoveryItem(**data)
        self.db.add(item)
        self.db.flush()
        return item

    def get_run(self, run_id: int) -> DiscoveryRun | None:
        return self.db.query(DiscoveryRun).filter(DiscoveryRun.id == run_id).first()

    def list_items(self, run_id: int) -> list[DiscoveryItem]:
        return (
            self.db.query(DiscoveryItem)
            .filter(DiscoveryItem.discovery_run_id == run_id)
            .order_by(DiscoveryItem.id)
            .all()
        )

    def get_item(self, run_id: int, item_id: int) -> DiscoveryItem | None:
        return (
            self.db.query(DiscoveryItem)
            .filter(
                DiscoveryItem.discovery_run_id == run_id,
                DiscoveryItem.id == item_id,
            )
            .first()
        )

    def get_latest_run(self, node_id: int) -> DiscoveryRun | None:
        return (
            self.db.query(DiscoveryRun)
            .filter(DiscoveryRun.node_id == node_id)
            .order_by(DiscoveryRun.id.desc())
            .first()
        )

    def find_local_node(self) -> ComputeNode | None:
        return (
            self.db.query(ComputeNode)
            .join(NodeConnection, NodeConnection.node_id == ComputeNode.id)
            .filter(NodeConnection.connector_type == "local", NodeConnection.enabled.is_(True))
            .order_by(ComputeNode.id)
            .first()
        )
