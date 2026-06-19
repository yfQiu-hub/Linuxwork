from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from database import db
import json

server = Server("minesweeper-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_game_state",
            description="获取指定游戏的当前状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string", "description": "游戏ID"}
                },
                "required": ["game_id"]
            }
        ),
        types.Tool(
            name="get_leaderboard",
            description="获取扫雷游戏排行榜",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "返回数量", "default": 10}
                }
            }
        ),
        types.Tool(
            name="get_player_games",
            description="获取玩家所有游戏记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "player_name": {"type": "string", "description": "玩家名称"}
                },
                "required": ["player_name"]
            }
        ),
        types.Tool(
            name="get_game_stats",
            description="获取游戏统计数据",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    
    if name == "get_game_state":
        game_id = arguments.get("game_id")
        game_data = db.load_game(game_id)
        if game_data:
            return [types.TextContent(type="text", text=json.dumps(game_data, indent=2, default=str))]
        return [types.TextContent(type="text", text="Game not found")]
    
    elif name == "get_leaderboard":
        limit = arguments.get("limit", 10)
        leaders = db.get_leaderboard(limit)
        return [types.TextContent(type="text", text=json.dumps(leaders, indent=2, default=str))]
    
    elif name == "get_player_games":
        player_name = arguments.get("player_name")
        query = '''
            SELECT game_id, difficulty, created_at, updated_at,
                   game_state->>'game_over' as game_over,
                   game_state->>'win' as win,
                   game_state->>'revealed_count' as revealed
            FROM games
            WHERE player_name = %s
            ORDER BY created_at DESC
        '''
        result = db.execute_query(query, (player_name,), fetch=True)
        return [types.TextContent(type="text", text=json.dumps([dict(r) for r in result], indent=2, default=str))]
    
    elif name == "get_game_stats":
        query = '''
            SELECT 
                COUNT(*) as total_games,
                COUNT(CASE WHEN game_state->>'win' = 'true' THEN 1 END) as wins,
                COUNT(CASE WHEN game_state->>'game_over' = 'true' AND game_state->>'win' = 'false' THEN 1 END) as losses,
                AVG((game_state->>'revealed_count')::int) as avg_revealed
            FROM games
            WHERE game_state->>'game_over' = 'true'
        '''
        result = db.execute_query(query, fetch=True)
        return [types.TextContent(type="text", text=json.dumps(dict(result[0]), indent=2))]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with server.run_stdio():
        await server.wait_for_shutdown()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())