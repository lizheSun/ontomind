"""认知层 API - 本体图谱构建 & 语义理解."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db, SessionLocal
from app.services.ontology_service import OntologyService
from app.core.exceptions import BusinessException

router = APIRouter()


# ========== 本体版本管理 ==========

@router.post("/ontology/build")
async def build_ontology(payload: dict, db: Session = Depends(get_db)):
    """构建本体（非流式）.

    请求体:
    {
      "datasource_id": 1,
      "method": "rules" | "llm" | "agent",
      "llm_config_id": null,   # method=llm 时
      "agent_id": null,        # method=agent 时
      "table_ids": [],         # 可选，限定表
      "use_judge": false
    }
    """
    svc = OntologyService(db)
    datasource_id = payload.get("datasource_id")
    if not datasource_id:
        raise BusinessException("缺少 datasource_id", code="BAD_REQUEST")
    table_ids = payload.get("table_ids") or None
    result = await svc.build_ontology(
        datasource_id=datasource_id,
        method=payload.get("method", "rules"),
        llm_config_id=payload.get("llm_config_id"),
        agent_id=payload.get("agent_id"),
        table_ids=table_ids,
        use_judge=bool(payload.get("use_judge", False)),
    )
    return {"code": "SUCCESS", "message": "构建完成", "data": result}


@router.get("/ontology/versions")
async def list_ontology_versions(datasource_id: int = Query(...), db: Session = Depends(get_db)):
    """列出数据源的本体版本."""
    svc = OntologyService(db)
    data = svc.list_versions(datasource_id)
    return {"code": "SUCCESS", "data": data, "total": len(data)}


@router.get("/ontology/versions/{version_id}")
async def get_ontology_version(version_id: int, db: Session = Depends(get_db)):
    """获取本体版本详情."""
    svc = OntologyService(db)
    return {"code": "SUCCESS", "data": svc.get_version(version_id)}


@router.delete("/ontology/versions/{version_id}")
async def delete_ontology_version(version_id: int, db: Session = Depends(get_db)):
    """删除本体版本."""
    svc = OntologyService(db)
    return {"code": "SUCCESS", "message": "已删除", "data": svc.delete_version(version_id)}


# ========== 本体内容查询 ==========

@router.get("/ontology/{version_id}/graph")
async def get_ontology_graph(version_id: int, db: Session = Depends(get_db)):
    """获取本体图谱数据 (用于 G6 可视化)."""
    svc = OntologyService(db)
    return {"code": "SUCCESS", "data": svc.get_graph(version_id)}


@router.get("/ontology/{version_id}/entities")
async def list_ontology_entities(version_id: int, db: Session = Depends(get_db)):
    """获取本体实体（类）及属性列表."""
    svc = OntologyService(db)
    data = svc.get_entities(version_id)
    return {"code": "SUCCESS", "data": data, "total": len(data)}


@router.get("/ontology/{version_id}/relationships")
async def list_ontology_relationships(version_id: int, db: Session = Depends(get_db)):
    """获取本体关系列表."""
    svc = OntologyService(db)
    data = svc.get_relationships(version_id)
    return {"code": "SUCCESS", "data": data, "total": len(data)}


@router.get("/ontology/{version_id}/constraints")
async def list_ontology_constraints(version_id: int, db: Session = Depends(get_db)):
    """获取本体约束列表."""
    svc = OntologyService(db)
    data = svc.get_constraints(version_id)
    return {"code": "SUCCESS", "data": data, "total": len(data)}


@router.put("/ontology/entities/{entity_id}")
async def update_ontology_entity(entity_id: int, payload: dict, db: Session = Depends(get_db)):
    """更新实体（类）元数据（人工编辑）."""
    svc = OntologyService(db)
    data = svc.update_entity(entity_id, payload)
    return {"code": "SUCCESS", "message": "更新成功", "data": data}


# ========== 导出 ==========

@router.get("/ontology/{version_id}/export")
async def export_ontology(
    version_id: int,
    fmt: str = Query("turtle", description="turtle | xml | json"),
    db: Session = Depends(get_db),
):
    """导出本体为 OWL/RDF (Turtle/XML) 或 JSON."""
    if fmt not in ("turtle", "xml", "json"):
        raise BusinessException("不支持的格式，仅支持 turtle/xml/json", code="BAD_FORMAT")
    svc = OntologyService(db)
    content = svc.export_owl(version_id, fmt)
    return {
        "code": "SUCCESS",
        "data": {
            "format": fmt,
            "content": content,
            "filename": f"ontology_{version_id}.{'ttl' if fmt == 'turtle' else fmt if fmt == 'xml' else 'json'}",
        },
    }


# ========== 流式构建 (WebSocket) ==========

@router.websocket("/ontology/build/stream")
async def stream_build_ontology(websocket: WebSocket):
    """WebSocket 流式构建本体.

    前端发送: {"datasource_id":1,"method":"llm","llm_config_id":null,"agent_id":null,"table_ids":[],"use_judge":false}
    后端实时推送:
      {"type":"status","content":"..."}
      {"type":"text","content":"LLM 返回..."}
      {"type":"error","content":"..."}
      {"type":"done","content":"..."}
      {"type":"result","content":{version 对象}}
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            datasource_id = payload.get("datasource_id")
            if not datasource_id:
                await websocket.send_text(json.dumps({"type": "error", "content": "缺少 datasource_id"}))
                break

            db = SessionLocal()
            svc = OntologyService(db)

            async def on_event(etype: str, content: str):
                await websocket.send_text(json.dumps({"type": etype, "content": content}))

            try:
                result = await svc.build_ontology(
                    datasource_id=datasource_id,
                    method=payload.get("method", "rules"),
                    llm_config_id=payload.get("llm_config_id"),
                    agent_id=payload.get("agent_id"),
                    table_ids=payload.get("table_ids") or None,
                    use_judge=bool(payload.get("use_judge", False)),
                    on_event=on_event,
                )
                await websocket.send_text(json.dumps({"type": "result", "content": result}))
            finally:
                db.close()
            break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": f"服务器异常: {e}"}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ========== 语义搜索（占位，预留接口） ==========

@router.get("/search/semantic")
async def semantic_search(q: str = ""):
    """语义搜索（后续版本接入向量检索）."""
    return {"query": q, "results": []}
