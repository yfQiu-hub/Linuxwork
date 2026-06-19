import random
import json

class MinesweeperGame:
    def __init__(self, rows=9, cols=9, mines=10):
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.board = []
        self.revealed = []
        self.flags = []
        self.game_over = False
        self.first_click = True
        self.init_board()
    
    def init_board(self):
        """初始化空白棋盘"""
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.flags = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.game_over = False
        self.first_click = True
    
    def place_mines(self, first_row, first_col):
        """放置地雷，避开第一次点击的位置"""
        self.mines_placed = 0
        while self.mines_placed < self.mines:
            row = random.randint(0, self.rows - 1)
            col = random.randint(0, self.cols - 1)
            # 避开第一次点击的位置及其周围
            if (abs(row - first_row) <= 1 and abs(col - first_col) <= 1):
                continue
            if self.board[row][col] == -1:
                continue
            self.board[row][col] = -1
            self.mines_placed += 1
        
        # 计算数字
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if self.board[nr][nc] == -1:
                                count += 1
                self.board[r][c] = count
        
        self.first_click = False
    
    def reveal(self, row, col):
        """翻开格子"""
        if self.game_over:
            return False
        
        if self.first_click:
            self.place_mines(row, col)
        
        if self.flags[row][col]:
            return False
        
        if self.revealed[row][col]:
            return False
        
        if self.board[row][col] == -1:
            self.game_over = True
            return False
        
        # 递归翻开空白格子
        self._reveal_recursive(row, col)
        return True
    
    def _reveal_recursive(self, row, col):
        """递归翻开空白格子"""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        if self.revealed[row][col]:
            return
        if self.flags[row][col]:
            return
        if self.board[row][col] == -1:
            return
        
        self.revealed[row][col] = True
        
        if self.board[row][col] == 0:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    self._reveal_recursive(row + dr, col + dc)
    
    def toggle_flag(self, row, col):
        """切换旗帜标记"""
        if self.game_over:
            return False
        if self.revealed[row][col]:
            return False
        
        self.flags[row][col] = not self.flags[row][col]
        return True
    
    def check_win(self):
        """检查是否获胜"""
        if self.first_click:
            return False
        
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] != -1 and not self.revealed[r][c]:
                    return False
        self.game_over = True
        return True
    
    def get_board_state(self):
        """获取当前棋盘状态（用于前端）"""
        state = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                if self.game_over and self.board[r][c] == -1:
                    row.append({'value': '💣', 'revealed': True})
                elif self.flags[r][c]:
                    row.append({'value': '🚩', 'revealed': False})
                elif not self.revealed[r][c]:
                    row.append({'value': '⬜', 'revealed': False})
                else:
                    val = self.board[r][c]
                    if val == 0:
                        row.append({'value': ' ', 'revealed': True})
                    else:
                        row.append({'value': str(val), 'revealed': True})
            state.append(row)
        return state
    
    def get_game_state(self):
        """获取完整游戏状态"""
        return {
            'board': self.get_board_state(),
            'game_over': self.game_over,
            'rows': self.rows,
            'cols': self.cols,
            'mines': self.mines,
            'flags_placed': sum(sum(row) for row in self.flags),
            'revealed_count': sum(sum(row) for row in self.revealed),
            'win': self.check_win() if not self.first_click else False
        }