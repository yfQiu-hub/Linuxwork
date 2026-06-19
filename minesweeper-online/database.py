import psycopg2
import psycopg2.extras
import os
import json

class Database:
    def __init__(self):
        self.host = os.environ.get('DB_HOST', 'postgres')
        self.dbname = os.environ.get('DB_NAME', 'minesweeper')
        self.user = os.environ.get('DB_USER', 'gameuser')
        self.password = os.environ.get('DB_PASSWORD', 'gamepass')
    
    def get_connection(self):
        """获取数据库连接 - 返回连接对象"""
        return psycopg2.connect(
            host=self.host,
            database=self.dbname,
            user=self.user,
            password=self.password
        )
    
    def execute_query(self, query, params=None, fetch=False):
        """执行查询"""
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
            else:
                conn.commit()
                result = None
            cur.close()
            return result
        finally:
            conn.close()
    
    def save_game(self, game_id, player_name, game_state, difficulty):
        """保存游戏状态"""
        query = '''
            INSERT INTO games (game_id, player_name, game_state, difficulty, created_at, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (game_id) DO UPDATE
            SET player_name = EXCLUDED.player_name,
                game_state = EXCLUDED.game_state,
                difficulty = EXCLUDED.difficulty,
                updated_at = CURRENT_TIMESTAMP
        '''
        self.execute_query(query, (game_id, player_name, json.dumps(game_state), difficulty))
    
    def load_game(self, game_id):
        """加载游戏状态"""
        query = 'SELECT * FROM games WHERE game_id = %s'
        result = self.execute_query(query, (game_id,), fetch=True)
        if result:
            return dict(result[0])
        return None
    
    def get_leaderboard(self, limit=10):
        """获取排行榜"""
        query = '''
            SELECT player_name, 
                   difficulty,
                   (game_state->>'rows')::int * (game_state->>'cols')::int - (game_state->>'mines')::int as total_cells,
                   (game_state->>'revealed_count')::int as revealed,
                   EXTRACT(EPOCH FROM (updated_at - created_at)) as duration
            FROM games
            WHERE game_state->>'game_over' = 'true' 
              AND game_state->>'win' = 'true'
            ORDER BY (game_state->>'revealed_count')::int DESC,
                     EXTRACT(EPOCH FROM (updated_at - created_at)) ASC
            LIMIT %s
        '''
        result = self.execute_query(query, (limit,), fetch=True)
        return [dict(row) for row in result] if result else []

db = Database()