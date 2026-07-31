import math
import random
import os
from PySide6.QtCore import Qt, QTimer, QPointF, QUrl
from PySide6.QtGui import QCursor, QAction, QMovie, QTransform, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.core.config import PetState, TICK_RATE, AI_MIN_INTERVAL, AI_MAX_INTERVAL, BASE_SPEED_MIN, BASE_SPEED_MAX, QUIT_IMG, BARK_IMG, DOG_MP4, PET_WIDTH, PET_HEIGHT

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
        self.anger_timer.timeout.connect(self.trigger_bark)
        self.anger_timer.setSingleShot(True)
        
        # Bark状态计时器
        self.bark_timer = QTimer(self)
        self.bark_timer.timeout.connect(self.end_bark)
        self.bark_timer.setSingleShot(True)
        self.bark_base_x = 0.0
        self.bark_base_y = 0.0
        self.bark_start_anger = 0
        self.bark_total_duration = 0
        
        # 媒体播放器列表 (防止被垃圾回收)，用于支持不覆盖的并发播放
        self.media_players = []

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
        # 加载正常状态图片
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

        # 加载Bark状态图片
        if os.path.exists(BARK_IMG):
            pixmap_bark = QPixmap(BARK_IMG)
            self.pixmap_bark_right = pixmap_bark.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            transform = QTransform().scale(-1, 1)
            self.pixmap_bark_left = self.pixmap_bark_right.transformed(transform)
        else:
            print(f"警告: 未在 {BARK_IMG} 找到素材")
            self.pixmap_bark_right = self._create_fallback_pixmap(Qt.GlobalColor.red)
            self.pixmap_bark_left = self._create_fallback_pixmap(Qt.GlobalColor.darkRed)
            
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
            self.tinted_bark_right = self.pixmap_bark_right
            self.tinted_bark_left = self.pixmap_bark_left
        else:
            self.tinted_right = self._apply_red_tint(self.pixmap_right)
            self.tinted_left = self._apply_red_tint(self.pixmap_left)
            self.tinted_bark_right = self._apply_red_tint(self.pixmap_bark_right)
            self.tinted_bark_left = self._apply_red_tint(self.pixmap_bark_left)
        self.update_image()

    def _apply_red_tint(self, pixmap):
        new_pixmap = QPixmap(pixmap.size())
        new_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(new_pixmap)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        
        # 根据红温值计算透明度，限制显示效果最高 180 (保留一定原图细节)
        # 即使红温值无限大，画面的红度也锁定在最大 180 的透明度
        display_anger = min(100, self.anger_level) 
        alpha = int((display_anger / 100.0) * 180)
        
        painter.fillRect(new_pixmap.rect(), QColor(255, 0, 0, alpha))
        painter.end()
        return new_pixmap

    def trigger_bark(self):
        """倒计时结束，进入 Bark 状态"""
        if self.anger_level == 0:
            self.end_bark()
            return
            
        self.state = PetState.BARK
        self.ai_timer.stop() # 暂停普通的思考
        self.vx, self.vy = 0, 0
        
        # 记录基准位置用于抖动计算
        self.bark_base_x = self.pos_x
        self.bark_base_y = self.pos_y
        
        # 记录初始红温值和总持续时间，用于衰减计算
        self.bark_start_anger = self.anger_level
        self.bark_total_duration = 1000 + int(self.anger_level * 20)
        
        self.bark_timer.start(self.bark_total_duration)
        self.update_image()

    def end_bark(self):
        """Bark 结束，重置状态"""
        self.anger_level = 0
        self._update_tinted_pixmaps()
        
        # 恢复物理位置
        if self.state == PetState.BARK:
            self.pos_x = self.bark_base_x
            self.pos_y = self.bark_base_y
            self.move(int(self.pos_x), int(self.pos_y))
            
        self.set_state(PetState.IDLE)
        self.think() # 重新启动普通 AI

    def increase_anger(self):
        """每次点击增加红温值，只有在红温为0时才启动10秒倒计时，不再刷新。"""
        if self.anger_level == 0:
            self.anger_timer.start(10000) # 仅第一次点击触发，固定10秒后重置
            
        self.anger_level += 10 # 每次增加10，无上限
        self._update_tinted_pixmaps()
        
        # 播放大狗叫声音频
        if os.path.exists(DOG_MP4):
            # 根据红温增加播放速度 (每次点击速度提升，最高加速到 3.0 倍)
            playback_rate = min(3.0, 1.0 + (self.anger_level / 100.0))
            
            player = QMediaPlayer()
            audio_output = QAudioOutput()
            player.setAudioOutput(audio_output)
            player.setSource(QUrl.fromLocalFile(os.path.abspath(DOG_MP4)))
            player.setPlaybackRate(playback_rate)
            
            # 播放结束后清理资源
            player.mediaStatusChanged.connect(lambda status, p=player: self._cleanup_player(p, status))
            
            self.media_players.append(player)
            player.play()

    def _cleanup_player(self, player, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if player in self.media_players:
                self.media_players.remove(player)

    def update_image(self):
        """根据当前方向和摇摆角度更新图片。"""
        # 注意: 如果还在 load_image 初始化过程中，tinted_left 可能还不存在
        if not hasattr(self, 'tinted_left') or not hasattr(self, 'tinted_bark_left'):
            return
            
        if self.state == PetState.BARK:
            base_pixmap = self.tinted_bark_left if self.is_mirrored else self.tinted_bark_right
        else:
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
            
        # 根据红温计算疯狂系数 (Anger Factor)
        # 0红温 = 1.0 (正常)
        # 100红温 = 2.0 (2倍速，2倍疯狂)
        # 200红温 = 3.0 等等...
        anger_factor = 1.0 + (self.anger_level / 100.0)
            
        # 随机选择发呆或行走
        # 红温越高，发呆的概率越低 (正常50%，100红温25%，200红温16.6%)
        idle_probability = 0.5 / anger_factor
        
        if random.random() < idle_probability:
            self.set_state(PetState.IDLE)
            self.vx, self.vy = 0, 0
        else:
            self.set_state(PetState.WALKING)
            # 选取一个随机角度 (0 到 360 度)
            angle = random.uniform(0, 2 * math.pi)
            
            # 速度随着红温增加
            speed = random.uniform(BASE_SPEED_MIN, BASE_SPEED_MAX) * anger_factor
            
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
            
            # 根据水平速度更新镜像状态
            old_mirrored = self.is_mirrored
            self.is_mirrored = self.vx < 0
            if old_mirrored != self.is_mirrored:
                self.update_image()
            
        # 安排下一次思考 (红温越高，思考间隔越短 -> 变向越频繁，越混沌)
        min_interval = int(AI_MIN_INTERVAL / anger_factor)
        max_interval = int(AI_MAX_INTERVAL / anger_factor)
        # 限制最小思考时间为 100ms，防止过快导致程序卡死
        next_interval = random.randint(max(100, min_interval), max(100, max_interval))
        self.ai_timer.start(next_interval)

    def update_physics(self):
        """更新位置并处理碰撞。"""
        if self.is_dragging:
            return
            
        if self.state == PetState.BARK:
            # 计算剩余时间比例 (0.0 到 1.0)
            remaining_time = self.bark_timer.remainingTime()
            if remaining_time < 0: remaining_time = 0
            progress_ratio = remaining_time / float(self.bark_total_duration) if self.bark_total_duration > 0 else 0
            
            # 随时间逐渐消退红温值
            self.anger_level = int(self.bark_start_anger * progress_ratio)
            self._update_tinted_pixmaps() # 动态更新图片颜色
            
            # 根据当前的剩余红温分值决定抖动烈度 (同样会随时间减弱)
            anger_factor = 1.0 + (self.anger_level / 100.0)
            shake_pos = 3.0 * anger_factor # 位置抖动半径
            shake_angle = 10.0 * anger_factor # 旋转抖动最大角度
            
            # 在基准位置上随机跳跃 (狂震)
            self.pos_x = self.bark_base_x + random.uniform(-shake_pos, shake_pos)
            self.pos_y = self.bark_base_y + random.uniform(-shake_pos, shake_pos)
            self.wobble_angle = random.uniform(-shake_angle, shake_angle)
            
            self.update_image()
            self.move(int(self.pos_x), int(self.pos_y))
            return
            
        if self.state == PetState.IDLE:
            return
            
        self.pos_x += self.vx
        self.pos_y += self.vy
        
        # 动态计算疯狂系数
        anger_factor = 1.0 + (self.anger_level / 100.0)
        
        # 计算摇摆角度 (正弦波)
        # 摇摆速度和最大摇摆角度都随着红温增加
        self.wobble_time += 0.15 * anger_factor
        max_wobble = 15.0 * min(3.0, anger_factor) # 限制最大摇摆角度不超过 45 度
        
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
            if self.state == PetState.BARK:
                return # 处于爆发状态时无视点击
                
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
