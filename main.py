import sys
import logging
import multiprocessing as mp
from PyQt6.QtWidgets import QApplication
from radar_visualizer import RadarVisualizer

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    # 设置主程序日志
    logger = logging.getLogger('Main')
    logger.setLevel(logging.INFO)
    
    # 确保多进程在主模块启动
    mp.set_start_method('spawn', force=True)
    logger.info("启动多传感器融合可视化系统")
    
    # 创建QApplication实例
    app = QApplication(sys.argv)
    
    # 创建并显示可视化器
    visualizer = RadarVisualizer()
    visualizer.show()
    
    # 运行应用程序
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 