"""MCP 业务服务."""
from sqlalchemy.orm import Session
from app.db.repositories.mcp_repo import MCPRepository
from app.db.repositories.llm_config_repo import LLMConfigRepository
from app.schemas.mcp_schema import MCPCreate, MCPUpdate
from app.services.llm_config_service import LLMConfigService
from app.core.exceptions import ConflictException, NotFoundException


class MCPService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MCPRepository(db)

    def create(self, data: MCPCreate) -> dict:
        if self.repo.name_exists(data.name):
            raise ConflictException("MCP 名称已存在", code="MCP_NAME_EXISTS")
        mcp = self.repo.create(data.model_dump())
        self.db.commit()
        return mcp.to_response_dict()

    def get(self, mcp_id: int) -> dict:
        mcp = self.repo.get_by_id(mcp_id)
        if not mcp:
            raise NotFoundException(f"MCP 不存在: {mcp_id}")
        return mcp.to_response_dict()

    def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        items = self.repo.get_all(skip, limit)
        return [m.to_response_dict() for m in items]

    def update(self, mcp_id: int, data: MCPUpdate) -> dict:
        mcp = self.repo.get_by_id(mcp_id)
        if not mcp:
            raise NotFoundException(f"MCP 不存在: {mcp_id}")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != mcp.name:
            if self.repo.name_exists(update_data["name"], exclude_id=mcp_id):
                raise ConflictException("MCP 名称已存在", code="MCP_NAME_EXISTS")
        updated = self.repo.update(mcp_id, update_data)
        self.db.commit()
        return updated.to_response_dict()

    def delete(self, mcp_id: int) -> bool:
        if not self.repo.delete(mcp_id):
            raise NotFoundException(f"MCP 不存在: {mcp_id}")
        self.db.commit()
        return True

    async def auto_discover(self, api_url: str, method: str = "GET",
                            headers: dict = None, request_body_example: str = None,
                            response_body_example: str = None,
                            description_text: str = None) -> dict:
        """从任意 API + LLM 自动发现并生成 MCP 配置"""
        import json

        # 收集所有可用信息
        api_info = {
            "url": api_url,
            "method": method.upper(),
        }
        if headers:
            api_info["headers"] = headers
        if request_body_example:
            api_info["request_body_example"] = request_body_example
        if response_body_example:
            api_info["response_body_example"] = response_body_example

        prompt = f"""你是一个 MCP (Model Context Protocol) 工具配置专家。请根据以下 API 信息，生成一个 MCP 工具的完整配置。

API 信息:
{json.dumps(api_info, ensure_ascii=False, indent=2)}

{f"额外描述: {description_text}" if description_text else ""}

请返回 JSON 格式（不要 markdown 包裹）:
{{
    "name": "工具名称（英文，snake_case）",
    "description": "工具的功能描述",
    "mcp_type": "http",
    "tools_manifest": {{
        "tools": [
            {{
                "name": "工具方法名",
                "description": "方法描述",
                "inputSchema": {{
                    "type": "object",
                    "properties": {{}},
                    "required": []
                }}
            }}
        ]
    }},
    "url": "API 完整 URL",
    "headers": {{}},
    "method": "HTTP 方法"
}}"""

        # 使用 LLM 推断
        llm_repo = LLMConfigRepository(self.db)
        active_config = llm_repo.get_active()
        if not active_config:
            raise RuntimeError("没有活跃的 LLM 配置，无法自动发现")

        llm_service = LLMConfigService(self.db)
        result = llm_service._call_openai(
            model=active_config.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
            base_url=active_config.base_url,
            api_key=active_config.api_key,
        )

        content = result.get("content", "")
        # 提取 JSON
        import re
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}', content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)

        parsed = json.loads(content)
        parsed.setdefault("name", "auto_discovered_mcp")
        parsed.setdefault("description", "")
        parsed.setdefault("url", api_url)
        parsed.setdefault("auto_discovery_enabled", True)
        parsed.setdefault("auto_discovery_url", api_url)
        parsed.setdefault("is_active", True)

        return {"code": "SUCCESS", "message": "自动发现完成", "data": parsed}
