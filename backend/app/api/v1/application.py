"""应用层 API - AIbi & 数据可视化."""

from fastapi import APIRouter

router = APIRouter()


# === AIbi - 智能分析 ===

@router.post("/aibi/query")
async def aibi_query():
    """AIbi 自然语言查询."""
    return {"query": "", "sql": "", "results": [], "explanation": ""}


@router.post("/aibi/analyze")
async def aibi_analyze():
    """AIbi 智能分析."""
    return {"analysis": "", "insights": [], "visualizations": []}


# === 数据可视化 ===

@router.get("/dashboard/datasets")
async def list_datasets():
    """获取可用数据集."""
    return {"datasets": [], "total": 0}


@router.get("/dashboard/charts")
async def list_charts():
    """获取仪表盘图表配置."""
    return {"charts": []}


@router.post("/dashboard/charts")
async def create_chart():
    """创建图表."""
    return {"message": "create chart - to be implemented"}
