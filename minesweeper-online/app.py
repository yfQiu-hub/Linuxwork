from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from game_logic import MinesweeperGame
from database import db
import redis
import os
import json
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Redis连接
redis_client = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    decode_responses=True
)

# 存储活跃游戏
active_games = {}

# 初始化数据库表
def init_db():
    conn = db.get_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id VARCHAR(36) PRIMARY KEY,
            player_name VARCHAR(50) NOT NULL,
            game_state JSONB NOT NULL,
            difficulty VARCHAR(20) DEFAULT 'easy',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_games_player ON games(player_name)
    ''')
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_games_created ON games(created_at DESC)
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new_game', methods=['POST'])
def new_game():
    """创建新游戏"""
    data = request.json
    player_name = data.get('player_name', 'Anonymous')
    difficulty = data.get('difficulty', 'easy')
    
    # 难度设置
    configs = {
        'easy': {'rows': 9, 'cols': 9, 'mines': 10},
        'medium': {'rows': 16, 'cols': 16, 'mines': 40},
        'hard': {'rows': 16, 'cols': 30, 'mines': 99}
    }
    
    config = configs.get(difficulty, configs['easy'])
    game_id = str(uuid.uuid4())
    
    # 创建游戏实例
    game = MinesweeperGame(config['rows'], config['cols'], config['mines'])
    active_games[game_id] = game
    
    # 保存到Redis缓存
    redis_client.hset(f'game:{game_id}', mapping={
        'player_name': player_name,
        'difficulty': difficulty,
        'created_at': datetime.now().isoformat()
    })
    
    return jsonify({
        'game_id': game_id,
        'player_name': player_name,
        'difficulty': difficulty,
        'state': game.get_game_state()
    })

@app.route('/api/game/<game_id>/reveal', methods=['POST'])
def reveal_cell(game_id):
    """翻开格子"""
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    data = request.json
    row = data.get('row')
    col = data.get('col')
    game = active_games[game_id]
    
    if row is None or col is None:
        return jsonify({'error': 'Invalid coordinates'}), 400
    
    result = game.reveal(row, col)
    
    # 检查是否获胜
    win = game.check_win() if not game.first_click else False
    
    state = game.get_game_state()
    state['win'] = win
    
    # 如果游戏结束，保存到数据库
    if game.game_over:
        game_data = {
            'rows': game.rows,
            'cols': game.cols,
            'mines': game.mines,
            'game_over': game.game_over,
            'win': win,
            'revealed_count': sum(sum(row) for row in game.revealed)
        }
        player_name = redis_client.hget(f'game:{game_id}', 'player_name') or 'Anonymous'
        difficulty = redis_client.hget(f'game:{game_id}', 'difficulty') or 'easy'
        db.save_game(game_id, player_name, game_data, difficulty)
    
    # 通过WebSocket广播更新
    socketio.emit('game_update', {
        'game_id': game_id,
        'state': state
    })
    
    return jsonify(state)

@app.route('/api/game/<game_id>/flag', methods=['POST'])
def toggle_flag(game_id):
    """切换旗帜"""
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    data = request.json
    row = data.get('row')
    col = data.get('col')
    game = active_games[game_id]
    
    if row is None or col is None:
        return jsonify({'error': 'Invalid coordinates'}), 400
    
    result = game.toggle_flag(row, col)
    state = game.get_game_state()
    
    # 通过WebSocket广播更新
    socketio.emit('game_update', {
        'game_id': game_id,
        'state': state
    })
    
    return jsonify(state)

@app.route('/api/game/<game_id>/state')
def get_game_state(game_id):
    """获取游戏状态"""
    if game_id in active_games:
        game = active_games[game_id]
        return jsonify(game.get_game_state())
    
    # 尝试从数据库加载
    game_data = db.load_game(game_id)
    if game_data:
        return jsonify({
            'loaded': True,
            'game_over': True,
            'data': game_data['game_state']
        })
    
    return jsonify({'error': 'Game not found'}), 404

@app.route('/api/game/<game_id>/restart', methods=['POST'])
def restart_game(game_id):
    """重新开始游戏"""
    if game_id not in active_games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = active_games[game_id]
    game.init_board()
    state = game.get_game_state()
    
    socketio.emit('game_update', {
        'game_id': game_id,
        'state': state
    })
    
    return jsonify(state)

@app.route('/api/leaderboard')
def get_leaderboard():
    """获取排行榜"""
    limit = request.args.get('limit', 10, type=int)
    leaders = db.get_leaderboard(limit)
    return jsonify(leaders)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)