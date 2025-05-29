"""
**************************************************************************
工具1：RadarFusionPlayer - 多传感器数据同步回放工具（基于 PyQt6 + PyQtGraph）
**************************************************************************

功能简介：
----------------
本程序用于加载和同步回放多种传感器数据（毫米波雷达点云、RealSense彩色图、深度图），
支持姿态识别、手势识别、截图、关键点保存等功能，并提供图形化操作界面。

支持数据类型：
------------------
1. `.mp4`      —  彩色视频（使用 ColorCodec 编解码器）
2. `.zst`      —  深度图像（使用 DepthZstdCodec 编解码器）
3. `.feather`  —  雷达点云数据，必须包含 `frame_num`, `range`, `azim_deg`, `elev_deg`, `velocity` 字段

主要功能模块：
------------------
- 3D 点云视图（OpenGL 可旋转缩放）
- 彩色图像视图（可启用 Mediapipe 姿态识别和手部关键点识别）
- 深度图像视图（支持雷达投影）
- 支持逐帧播放、自动播放、截图、保存 3D 姿态关键点坐标为 CSV
- 播放速度可调（0.25x 到 4x）

使用说明：
------------------
1. 启动后点击 “加载数据”，选择一个包含 `.mp4`、`.zst` 和 `.feather` 文件的文件夹。
2. 使用播放控制按钮查看每一帧数据；
3. 可选开启姿态识别或手势识别；
4. 若勾选 “保存关键点坐标”，程序将在每帧处理时将 3D 姿态信息写入 CSV。

依赖库要求：
------------------
- numpy
- pandas
- opencv-python
- pyqt6
- pyqtgraph
- pyarrow
- color_codec（用户自定义模块）
- depth_codec（用户自定义模块）
- pose_tracker（封装了 Mediapipe 姿态识别）
- hand_tracker（封装了 Mediapipe 手部识别）

示例文件结构：
------------------
recordings/
└── record_20250427_120000/
    ├── color_output_20250427_120000.mp4
    ├── depth_output_20250427_120000.zst
    └── pointcloud_20250427_120000.feather

提示：
------------------
- 若你尚未实现 `ColorCodec`, `DepthZstdCodec`, `PoseTracker`, `HandTracker`，请先实现或导入这些模块；
- 所有传感器数据应基于统一时间戳命名，确保每一帧可以同步加载；
- 如需将本程序嵌入你的项目中，可将本类封装为模块引入使用。

启动方式：
------------------
python radar_fusion_player.py
"""


import os
import sys
import numpy as np
import pandas as pd
import cv2
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QFileDialog, QComboBox
)
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from depth_codec import DepthZstdCodec
from color_codec import ColorCodec
from pose_tracker import PoseTracker
from hand_tracker import HandTracker 

class RadarFusionPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多传感器同步回放器")
        self.resize(1600, 900)

        self.color_frames = []
        self.depth_frames = []
        self.pointcloud_frames = []

        self.current_index = 0
        self.total_frames = 0
        self.playing = False
        self.recordings_dir = ''
        self.base_filename = 'poses_3d'
        self.save_pose_enabled = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_next_frame)

        self.hand_tracker = HandTracker()
        self.pose_tracker = None  # 延迟初始化

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()

        self.play_btn = QPushButton("播放")
        self.play_btn.clicked.connect(self.toggle_play)

        self.next_btn = QPushButton("下一帧")
        self.next_btn.clicked.connect(self.next_frame)

        self.capture_btn = QPushButton("截图")
        self.capture_btn.clicked.connect(self.capture_screenshot)

        self.pose_btn = QPushButton("启用姿态识别")
        self.pose_btn.setCheckable(True)
        self.pose_btn.setChecked(False)

        self.hand_btn = QPushButton("启用手势识别")
        self.hand_btn.setCheckable(True)
        self.hand_btn.setChecked(False)

        self.save_pose_btn = QPushButton("保存关键点坐标")
        self.save_pose_btn.setCheckable(True)
        self.save_pose_btn.setChecked(False)

        def toggle_pose():
            if self.pose_btn.isChecked():
                self.hand_btn.setChecked(False)
        def toggle_hand():
            if self.hand_btn.isChecked():
                self.pose_btn.setChecked(False)

        self.pose_btn.clicked.connect(toggle_pose)
        self.hand_btn.clicked.connect(toggle_hand)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.valueChanged.connect(self.seek_frame)

        self.speed_selector = QComboBox()
        self.speed_selector.addItems(["0.25x", "0.5x", "1x", "2x", "4x"])
        self.speed_selector.setCurrentText("1x")
        self.speed_selector.currentIndexChanged.connect(self.change_speed)

        self.frame_label = QLabel("帧: 0/0")

        load_btn = QPushButton("加载数据")
        load_btn.clicked.connect(self.load_from_folder)

        control_layout.addWidget(load_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addWidget(self.capture_btn)
        control_layout.addWidget(self.pose_btn)
        control_layout.addWidget(self.hand_btn)
        control_layout.addWidget(self.save_pose_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.frame_label)
        control_layout.addWidget(self.slider)
        control_layout.addWidget(QLabel("播放速度:"))
        control_layout.addWidget(self.speed_selector)

        main_layout.addLayout(control_layout)

        content_layout = QHBoxLayout()
        self.init_3d_view(content_layout)
        self.init_image_views(content_layout)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    def load_from_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择回放文件夹", "recordings")
        if dir_path:
            self.recordings_dir = dir_path
            self.base_filename = os.path.basename(dir_path)
            self.pose_tracker = PoseTracker(output_csv_path=f"{dir_path}/{self.base_filename}_poses_3d.csv")
            self.load_all_data()

    def init_3d_view(self, layout):
        self.view3d = gl.GLViewWidget()
        self.view3d.setBackgroundColor('k')
        grid = gl.GLGridItem()
        grid.setSize(10, 10)
        grid.setSpacing(1, 1)
        self.view3d.addItem(grid)

        axes = {
            'x': ([0, 0, 0], [1, 0, 0], (1, 0, 0, 1)),
            'y': ([0, 0, 0], [0, 1, 0], (0, 1, 0, 1)),
            'z': ([0, 0, 0], [0, 0, 1], (0, 0, 1, 1)),
        }
        for _, (start, end, color) in axes.items():
            line = gl.GLLinePlotItem(pos=np.array([start, end]), color=color, width=2)
            self.view3d.addItem(line)

        self.scatter = gl.GLScatterPlotItem()
        self.view3d.addItem(self.scatter)
        layout.addWidget(self.view3d, 3)

    def init_image_views(self, layout):
        image_layout = QVBoxLayout()
        pg.setConfigOptions(imageAxisOrder='row-major')

        self.color_view = pg.ImageView()
        self.color_view.setMinimumHeight(400)
        self._clean_imageview_ui(self.color_view)

        self.depth_view = pg.ImageView()
        self.depth_view.setMinimumHeight(400)
        self._clean_imageview_ui(self.depth_view)

        image_layout.addWidget(self.color_view)
        image_layout.addWidget(self.depth_view)
        layout.addLayout(image_layout, 2)

    def _clean_imageview_ui(self, view):
        view.ui.histogram.hide()
        view.ui.roiBtn.hide()
        view.ui.menuBtn.hide()

    def load_all_data(self):
        try:
            print("开始加载数据...")
            self.color_frames = self._try_load(lambda: ColorCodec().decode_video(self._get_file('.mp4')), "彩色视频")
            self.depth_frames = self._try_load(lambda: DepthZstdCodec().get_all_frames(self._get_file('.zst')), "深度图")
            df = self._try_load(lambda: pd.read_feather(self._get_file('.feather')), "点云数据")
            if df is not None:
                self.pointcloud_frames = [frame for _, frame in df.groupby('frame_num')]

            self.total_frames = min(len(self.color_frames), len(self.depth_frames), len(self.pointcloud_frames))
            if self.total_frames == 0:
                print("未加载任何帧，请检查文件")
            else:
                self.slider.setMaximum(self.total_frames - 1)
                print(f"所有数据加载完成，总帧数: {self.total_frames}")
        except Exception as e:
            print(f"数据加载失败: {e}")

    def _try_load(self, func, name):
        try:
            result = func()
            print(f"{name} 加载成功，共 {len(result)} 帧")
            return result
        except Exception as e:
            print(f"加载 {name} 失败: {e}")
            return []

    def _get_file(self, ext):
        files = [f for f in os.listdir(self.recordings_dir) if f.endswith(ext)]
        if not files:
            raise FileNotFoundError(f"未找到后缀为 {ext} 的文件")
        return os.path.join(self.recordings_dir, files[0])

    def toggle_play(self):
        if self.playing:
            self.timer.stop()
            self.play_btn.setText("播放")
        else:
            self.timer.start(33)
            self.play_btn.setText("暂停")
        self.playing = not self.playing

    def next_frame(self):
        if self.current_index >= self.total_frames - 1:
            self.timer.stop()
            self.play_btn.setText("播放")
            return
        self.current_index += 1
        self.slider.setValue(self.current_index)
        self.update_frame()

    def seek_frame(self, index):
        self.current_index = index
        self.update_frame()

    def update_frame(self):
        if self.total_frames == 0:
            return
        self.update_pointcloud_view()
        self.update_color_view()
        self.update_depth_view()

        if self.pose_btn.isChecked() and self.pose_tracker:
            color_frame = self.color_frames[self.current_index]['color']
            depth_frame = self.depth_frames[self.current_index]['depth']
            save_flag = self.save_pose_btn.isChecked()
            self.pose_tracker.process(color_frame, depth_frame=depth_frame, frame_id=self.current_index if save_flag else None)

        self.frame_label.setText(f"帧: {self.current_index + 1}/{self.total_frames}")

    def update_pointcloud_view(self):
        try:
            points = self.pointcloud_frames[self.current_index]
            r = points['range']
            az = np.radians(points['azim_deg'])
            el = np.radians(points['elev_deg'])

            x = r * np.cos(el) * np.cos(az)
            y = -r * np.cos(el) * np.sin(az)
            z = r * np.sin(el)

            speeds = np.clip(np.abs(points['velocity']) / 5.0, 0, 1)
            colors = np.zeros((len(points), 4))
            colors[:, 0] = 1.0 - speeds
            colors[:, 1] = speeds
            colors[:, 3] = 1.0
            self.scatter.setData(pos=np.vstack([x, y, z]).T, color=colors, size=5)
        except Exception as e:
            print(f"点云更新失败: {e}")

    def update_color_view(self):
        frame = self.color_frames[self.current_index]['color']
        if self.hand_btn.isChecked():
            frame = self.hand_tracker.process(frame)
        if self.pose_btn.isChecked() and self.pose_tracker:
            frame = self.pose_tracker.process(frame)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.color_view.setImage(rgb)

    def update_depth_view(self):
        frame = self.depth_frames[self.current_index]['depth']
        depth_norm = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        colormap = cv2.applyColorMap(depth_norm, cv2.COLORMAP_JET)
        self.depth_view.setImage(cv2.cvtColor(colormap, cv2.COLOR_BGR2RGB))

    def capture_screenshot(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "保存截图", "", "PNG Files (*.png)")
        if save_path:
            image = self.view3d.renderToArray((1920, 1080))
            exporter = pg.exporters.ImageExporter(image)
            exporter.export(save_path)
            print(f"截图已保存: {save_path}")

    def play_next_frame(self):
        if self.current_index >= self.total_frames - 1:
            self.timer.stop()
            self.play_btn.setText("播放")
            return
        self.current_index += 1
        self.slider.setValue(self.current_index)
        self.update_frame()

    def change_speed(self):
        speed_str = self.speed_selector.currentText()
        speed = float(speed_str.replace("x", ""))
        interval = int(33 / speed)
        self.timer.setInterval(interval)
        print(f"播放速度切换为 {speed_str}，定时器间隔 {interval} ms")
        if self.playing:
            self.timer.stop()
            self.timer.start(interval)

if __name__ == "__main__":
    print("启动 RadarFusionPlayer...")
    app = QApplication(sys.argv)
    player = RadarFusionPlayer()
    player.show()
    print("RadarFusionPlayer 已显示")
    sys.exit(app.exec())
