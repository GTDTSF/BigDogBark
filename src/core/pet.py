import math
import random
import os
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QCursor, QAction, QMovie, QTransform, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication

from src.core.config import PetState, TICK_RATE, AI_MIN_INTERVAL, AI_MAX_INTERVAL, BASE_SPEED_MIN, BASE_SPEED_MAX, QUIT_IMG, PET_WIDTH, PET_HEIGHT

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
        
        # 摇摆动画相关
        self.wobble_angle = 0.0
        self.wobble_time = 0.0

        # 红温系统相关
        self.anger_level = 0
        self.anger_timer = QTimer(self)
        self.anger_timer.timeout.connect(self.reset_anger)
        self.anger_timer.setSingleShot(True)

        # --- 图形 / 动画 ---
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.current_movie = None
        
        # 应用固定尺寸
        w, h = PET_WIDTH, PET_HEIGHT
        self.setFixedSize(w, h)
        self.label.setFixedSize(w, h)
        
        self.load_image()
        
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

    def load_image(self):
        """加载静态图片并缓存镜像。"""
        if os.path.exists(QUIT_IMG):
            pixmap = QPixmap(QUIT_IMG)
            # 缩放至固定尺寸，保持纵横比
            self.pixmap_right = pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            # 预先生成向左（镜像）的图片
            transform = QTransform().scale(-1, 1)
            self.pixmap_left = self.pixmap_right.transformed(transform)
        else:
            print(f"警告: 未在 {QUIT_IMG} 找到素材")
            self.pixmap_right = self._create_fallback_pixmap(Qt.GlobalColor.green)
            self.pixmap_left = self._create_fallback_pixmap(Qt.GlobalColor.blue)
            
        self._update_tinted_pixmaps()
        self.set_state(PetState.IDLE)

    def _create_fallback_pixmap(self, color):
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color))
        painter.drawEllipse(10, 10, self.width()-20, self.height()-20)
        painter.end()
        return pixmap

    def _update_tinted_pixmaps(self):
        """根据当前红温值生成染色后的贴图。"""
        if self.anger_level == 0:
            self.tinted_right = self.pixmap_right
            self.tinted_left = self.pixmap_left
        else:
            self.tinted_right = self._apply_red_tint(self.pixmap_right)
            self.tinted_left = self._apply_red_tint(self.pixmap_left)
        self.update_image()

    def _apply_red_tint(self, pixmap):
        new_pixmap = QPixmap(pixmap.size())
        new_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(new_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        # 根据红温值 (0-100) 计算透明度，最高 180 (保留一定原图细节)
        alpha = int((self.anger_level / 100.0) * 180)
        painter.fillRect(new_pixmap.rect(), QColor(255, 0, 0, alpha))
        painter.end()
        return new_pixmap

    def reset_anger(self):
        """重置红温值。"""
        self.anger_level = 0
        self._update_tinted_pixmaps()

    def increase_anger(self):
        """每次点击增加红温值，并重置10秒冷却。"""
        self.anger_level = min(100, self.anger_level + 10) # 每次增加10，最大100
        self.anger_timer.start(10000) # 10秒后重置
        self._update_tinted_pixmaps()

    def update_image(self):
        """根据当前方向和摇摆角度更新图片。"""
        # 注意: 如果还在 load_image 初始化过程中，tinted_left 可能还不存在
        if not hasattr(self, 'tinted_left'):
            return
            
        base_pixmap = self.tinted_left if self.is_mirrored else self.tinted_right
        
        if self.wobble_angle != 0.0:
            # 应用旋转来模拟摇摆
            transform = QTransform().rotate(self.wobble_angle)
            rotated_pixmap = base_pixmap.transformed(
                transform, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.label.setPixmap(rotated_pixmap)
        else:
            self.label.setPixmap(base_pixmap)

    def set_state(self, new_state):
        self.state = new_state
        if self.state == PetState.IDLE:
            self.wobble_angle = 0.0
            self.update_image()

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
            old_mirrored = self.is_mirrored
            self.is_mirrored = self.vx < 0
            if old_mirrored != self.is_mirrored:
                self.update_image()
            
        # 安排下一次思考
        next_interval = random.randint(AI_MIN_INTERVAL, AI_MAX_INTERVAL)
        self.ai_timer.start(next_interval)

    def update_physics(self):
        """更新位置并处理碰撞。"""
        if self.is_dragging or self.state == PetState.IDLE:
            return
            
        self.pos_x += self.vx
        self.pos_y += self.vy
        
        # 计算摇摆角度 (正弦波)
        self.wobble_time += 0.15 # 调整这个值来改变摇摆速度
        max_wobble = 15.0 # 最大摇摆角度
        self.wobble_angle = math.sin(self.wobble_time) * max_wobble
        
        # 每次物理更新时刷新图像以应用旋转
        self.update_image()
        
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
            old_mirrored = self.is_mirrored
            self.is_mirrored = self.vx < 0
            if old_mirrored != self.is_mirrored:
                self.update_image()
            
        # 应用新位置
        self.move(int(self.pos_x), int(self.pos_y))

    # --- 鼠标事件 (交互) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.increase_anger() # 累加红温
            
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
