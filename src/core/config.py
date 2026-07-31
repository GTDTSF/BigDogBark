import os
from enum import Enum, auto


class PetState(Enum):
    IDLE = auto()
    WALKING = auto()


# 路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FRAMES_DIR = os.path.join(ASSETS_DIR, "bark_frames")

# 物理与时间配置
FPS = 60
TICK_RATE = 1000 // FPS  # 物理刷新率 (毫秒)
AI_MIN_INTERVAL = 2000  # 状态切换的最小间隔时间 (毫秒)
AI_MAX_INTERVAL = 5000  # 状态切换的最大间隔时间 (毫秒)
BASE_SPEED_MIN = 1.0  # 最小移动速度
BASE_SPEED_MAX = 3.0  # 最大移动速度

# 尺寸配置
PET_WIDTH = 50  # 桌宠固定宽度
PET_HEIGHT = 50  # 桌宠固定高度
