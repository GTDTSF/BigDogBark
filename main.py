import sys
import os

# 确保根路径在 sys.path 中，以便我们可以导入 src 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from src.core.pet import DesktopPet

def main():
    app = QApplication(sys.argv)
    
    # 创建并显示桌宠
    pet = DesktopPet()
    pet.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
