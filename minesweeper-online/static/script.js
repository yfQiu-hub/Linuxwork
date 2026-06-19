let socket = null;
let currentGameId = null;
let currentPlayer = '';
let currentDifficulty = 'easy';
let timerInterval = null;
let seconds = 0;

// 难度配置
const DIFFICULTY_CONFIG = {
    easy: { label: '简单', rows: 9, cols: 9, mines: 10 },
    medium: { label: '中等', rows: 16, cols: 16, mines: 40 },
    hard: { label: '困难', rows: 16, cols: 30, mines: 99 }
};

document.addEventListener('DOMContentLoaded', () => {
    // 初始化Socket
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to server');
    });
    
    socket.on('game_update', (data) => {
        if (data.game_id === currentGameId) {
            renderBoard(data.state);
            updateGameInfo(data.state);
            
            if (data.state.game_over) {
                stopTimer();
                const statusEl = document.getElementById('game-status');
                if (data.state.win) {
                    statusEl.textContent = '🎉 恭喜你赢了！';
                    statusEl.className = 'win';
                } else {
                    statusEl.textContent = '💥 游戏结束！踩到地雷了！';
                    statusEl.className = 'lose';
                }
            }
        }
    });
    
    // 事件绑定
    document.querySelectorAll('.diff-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentDifficulty = btn.dataset.diff;
        });
    });
    
    document.getElementById('start-game-btn').addEventListener('click', startNewGame);
    document.getElementById('restart-btn').addEventListener('click', restartGame);
    document.getElementById('new-game-btn').addEventListener('click', () => {
        document.getElementById('game-section').style.display = 'none';
        document.getElementById('setup-section').style.display = 'block';
    });
    
    // 加载排行榜
    loadLeaderboard();
    
    // 定时刷新排行榜
    setInterval(loadLeaderboard, 15000);
});

async function startNewGame() {
    const playerInput = document.getElementById('player-input');
    currentPlayer = playerInput.value.trim() || 'Anonymous';
    
    try {
        const response = await fetch('/api/new_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player_name: currentPlayer,
                difficulty: currentDifficulty
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentGameId = data.game_id;
            document.getElementById('player-name').textContent = `👤 ${currentPlayer}`;
            document.getElementById('setup-section').style.display = 'none';
            document.getElementById('game-section').style.display = 'block';
            document.getElementById('game-status').textContent = '';
            document.getElementById('game-status').className = '';
            
            renderBoard(data.state);
            updateGameInfo(data.state);
            startTimer();
        } else {
            alert(data.error || '创建游戏失败');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('连接服务器失败');
    }
}

async function restartGame() {
    if (!currentGameId) return;
    
    try {
        const response = await fetch(`/api/game/${currentGameId}/restart`, {
            method: 'POST'
        });
        
        const data = await response.json();
        if (response.ok) {
            renderBoard(data);
            updateGameInfo(data);
            document.getElementById('game-status').textContent = '';
            document.getElementById('game-status').className = '';
            resetTimer();
            startTimer();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

function renderBoard(state) {
    const container = document.getElementById('board-container');
    const board = state.board;
    
    if (!board || board.length === 0) {
        container.innerHTML = '<p>No board data</p>';
        return;
    }
    
    const rows = board.length;
    const cols = board[0].length;
    
    // 计算合适的格子大小
    let cellSize = 40;
    const maxWidth = container.clientWidth - 20;
    const maxHeight = window.innerHeight - 400;
    
    if (cols * 42 > maxWidth) {
        cellSize = Math.min(32, Math.floor((maxWidth - 10) / cols));
    }
    if (rows * (cellSize + 2) > maxHeight) {
        cellSize = Math.min(28, Math.floor((maxHeight - 10) / rows) - 2);
    }
    cellSize = Math.max(24, Math.min(40, cellSize));
    
    let html = `<div class="board" style="grid-template-columns: repeat(${cols}, ${cellSize}px);">`;
    
    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const cell = board[r][c];
            const isRevealed = cell.revealed;
            const value = cell.value;
            
            let displayValue = '';
            let classes = 'cell';
            let dataValue = '';
            
            if (isRevealed) {
                classes += ' revealed';
                if (value === '💣') {
                    displayValue = '💣';
                    if (state.game_over) {
                        classes += ' mine-exploded';
                    }
                } else if (value !== ' ') {
                    displayValue = value;
                    dataValue = ` data-value="${value}"`;
                }
            } else {
                if (value === '🚩') {
                    displayValue = '🚩';
                    classes += ' flag';
                }
            }
            
            html += `<div class="${classes}" data-row="${r}" data-col="${c}"${dataValue} onclick="handleCellClick(${r}, ${c})" oncontextmenu="handleRightClick(event, ${r}, ${c})">${displayValue}</div>`;
        }
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function updateGameInfo(state) {
    document.getElementById('mines-count').textContent = `💣 ${state.mines}`;
    document.getElementById('flags-count').textContent = `🚩 ${state.flags_placed || 0}`;
}

function startTimer() {
    resetTimer();
    timerInterval = setInterval(() => {
        seconds++;
        document.getElementById('timer').textContent = `⏱️ ${seconds}s`;
    }, 1000);
}

function resetTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    seconds = 0;
    document.getElementById('timer').textContent = `⏱️ 0s`;
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

async function handleCellClick(row, col) {
    if (!currentGameId) return;
    
    try {
        const response = await fetch(`/api/game/${currentGameId}/reveal`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row, col })
        });
        
        const data = await response.json();
        if (!response.ok) {
            console.error('Error:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function handleRightClick(event, row, col) {
    event.preventDefault();
    if (!currentGameId) return;
    
    try {
        const response = await fetch(`/api/game/${currentGameId}/flag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ row, col })
        });
        
        const data = await response.json();
        if (!response.ok) {
            console.error('Error:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard?limit=10');
        const data = await response.json();
        
        const list = document.getElementById('leaderboard-list');
        list.innerHTML = '';
        
        if (!data || data.length === 0) {
            list.innerHTML = '<div style="text-align:center;color:#888;padding:20px;">暂无游戏记录</div>';
            return;
        }
        
        data.forEach((player, index) => {
            const item = document.createElement('div');
            item.className = 'leader-item';
            const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`;
            const duration = player.duration ? `${Math.round(player.duration)}s` : '-';
            item.innerHTML = `
                <span>
                    <span class="rank">${medal}</span>
                    ${player.player_name}
                    <span class="details">(${player.difficulty}, ${player.revealed}/${player.total_cells})</span>
                </span>
                <span class="details">⏱️ ${duration}</span>
            `;
            list.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading leaderboard:', error);
    }
}

// 窗口大小变化时重新渲染棋盘
window.addEventListener('resize', () => {
    // 可以添加防抖
});