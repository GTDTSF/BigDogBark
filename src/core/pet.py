import math
import random
import os
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QCursor, QAction, QMovie, QTransform, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication

from src.core.config import PetState, TICK_RATE, AI_MIN_INTERVAL, AI_MAX_INTERVAL, BASE_SPEED_MIN, BASE_SPEED_MAX, IDLE_GIF, WALK_GIF, PET_WIDTH, PET_HEIGHT

class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- UI 配置 ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool  # 隐藏任务栏图标
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # --- 状态变量 ---
        self.state = PetState.IDLE
        self.vx = 0.0
        self.vy = 0.0
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.is_mirrored = False # False = 朝右, True = 朝左
        self.is_dragging = False
        self.drag_offset = QPointF()

        # --- 图形 / 动画 ---
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.current_movie = None
        self.load_movies()
        
        # 应用固定尺寸
        w, h = PET_WIDTH, PET_HEIGHT
        self.setFixedSize(w, h)
        self.label.setFixedSize(w, h)
        
        # 初始居中显示桌宠
        screen_rect = QApplication.primaryScreen().availableGeometry()
        self.pos_x = (screen_rect.width() - w) / 2
        self.pos_y = (screen_rect.height() - h) / 2
        self.move(int(self.pos_x), int(self.pos_y))
        
        # --- 定时器 ---
        # 物理更新定时器 (~60 fps)
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.start(TICK_RATE)
        
        # AI 状态机定时器
        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(self.think)
        self.ai_timer.setSingleShot(True)
        self.think() # 启动 AI 循环

    def load_movies(self):
        """将 GIF 加载到 QMovie 对象中并设置帧拦截。"""
        self.movies = {}
        
        for state, path in [(PetState.IDLE, IDLE_GIF), (PetState.WALKING, WALK_GIF)]:
            if os.path.exists(path):
                movie = QMovie(path)
                # 不是直接将 movie 设置给 label，而是拦截帧
                # 以便在向左移动时我们可以手动翻转它们。
                movie.frameChanged.connect(self.on_frame_changed)
                self.movies[state] = movie
            else:
                self.movies[state] = None
                print(f"警告: 未在 {path} 找到素材")
                
        self.set_state(PetState.IDLE)

    def on_frame_changed(self, frame_number):
        """每次活动 QMovie 更改其帧时调用。"""
        if not self.current_movie:
            return
            
        pixmap = self.current_movie.currentPixmap()
        
        # 将图像按比例平滑缩放至固定的窗口大小
        pixmap = pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 如果向左移动，则水平镜像图像
        if self.is_mirrored:
            transform = QTransform().scale(-1, 1)
            pixmap = pixmap.transformed(transform)
            
        self.label.setPixmap(pixmap)

    def set_state(self, new_state):
        self.state = new_state
        
        # 停止上一个动画
        if self.current_movie:
            self.current_movie.stop()
            
        self.current_movie = self.movies.get(self.state)
        
        # 启动新动画
        if self.current_movie:
            self.current_movie.start()
        else:
            # 如果没有 GIF 则使用后备方案画个圆
            pixmap = QPixmap(self.size())
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            color = Qt.GlobalColor.green if self.state == PetState.IDLE else Qt.GlobalColor.blue
            painter.setBrush(QColor(color))
            painter.drawEllipse(10, 10, self.width()-20, self.height()-20)
            painter.end()
            self.label.setPixmap(pixmap)

    def think(self):
        """AI 逻辑：决定下一个状态和移动向量。"""
        if self.is_dragging:
            return # 被拖拽时不思考
            
        # 随机选择发呆或行走
        if random.random() < 0.5:
            self.set_state(PetState.IDLE)
            self.vx, self.vy = 0, 0
        else:
            self.set_state(PetState.WALKING)
            # 选取一个随机角度 (0 到 360 度)
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(BASE_SPEED_MIN, BASE_SPEED_MAX)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            
            # 根据水平速度更新镜像状态
            self.is_mirrored = self.vx < 0
            
        # 安排下一次思考
        next_interval = random.randint(AI_MIN_INTERVAL, AI_MAX_INTERVAL)
        self.ai_timer.start(next_interval)

    def update_physics(self):
        """更新位置并处理碰撞。"""
        if self.is_dragging or self.state == PetState.IDLE:
            return
            
        self.pos_x += self.vx
        self.pos_y += self.vy
        
        # 获取屏幕边界 (考虑任务栏)
        screen_rect = QApplication.primaryScreen().availableGeometry()
        
        # 碰撞检测和反弹
        hit_edge = False
        
        if self.pos_x <= screen_rect.left():
            self.pos_x = screen_rect.left()
            self.vx = abs(self.vx)
            hit_edge = True
        elif self.pos_x + self.width() >= screen_rect.right():
            self.pos_x = screen_rect.right() - self.width()
            self.vx = -abs(self.vx)
            hit_edge = True
            
        if self.pos_y <= screen_rect.top():
            self.pos_y = screen_rect.top()
            self.vy = abs(self.vy)
        elif self.pos_y + self.height() >= screen_rect.bottom():
            self.pos_y = screen_rect.bottom() - self.height()
            self.vy = -abs(self.vy)
            
        # 如果我们碰到左右墙壁，更新镜像方向
        if hit_edge:
            self.is_mirrored = self.vx < 0
            
        # 应用新位置
        self.move(int(self.pos_x), int(self.pos_y))

    # --- 鼠标事件 (交互) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_offset = event.globalPosition() - self.pos()
            
            # 拖拽时暂停 AI
            self.set_state(PetState.IDLE)
            self.vx, self.vy = 0, 0
            self.ai_timer.stop()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition() - self.drag_offset
            self.pos_x = new_pos.x()
            self.pos_y = new_pos.y()
            self.move(int(self.pos_x), int(self.pos_y))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            # 恢复 AI
            self.think()

    def contextMenuEvent(self, event):
        """右键菜单。"""
        menu = QMenu(self)
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        menu.addAction(quit_action)
        menu.exec(QCursor.pos())
