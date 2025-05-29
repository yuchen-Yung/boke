"""
PoseTracker 姿态检测与3D关键点记录模块
======================================

功能简介：
----------
本模块封装了基于 Mediapipe 的人体姿态检测功能，支持对每帧彩色图像进行 2D 姿态识别，
并结合深度图重建每个关键点的三维相机坐标（x, y, z）。
检测结果绘制在图像上，并将每帧所有关键点的 3D 坐标输出到 CSV 文件中，
用于后续步态分析、康复评估或人体建模等应用。

输入说明：
----------
- color_image：每帧彩色图像（BGR 格式的 np.ndarray）
- depth_frame：对应深度图像（二维数组，单位为毫米，默认可为 None）
- frame_id：当前帧编号，用于写入 CSV 文件

输出说明：
----------
- 返回值：带姿态骨架绘制的 RGB 图像（np.ndarray）
- 文件输出：默认路径 recordings/poses_3d.csv（可自定义）
  CSV 文件格式如下：
    frame, landmark_id, x_3d, y_3d, z_3d

处理流程：
----------
1. 初始化 Mediapipe Pose 模型
2. 将彩色图转为 RGB 并输入模型检测
3. 绘制关键点与骨架连接（绿色点 + 红线）
4. 若提供深度图，则根据相机内参计算每个关键点的 3D 坐标
5. 将所有有效关键点的三维坐标写入 CSV 文件中

默认相机内参：
--------------
- fx = 600.0
- fy = 600.0
- cx = 640.0
- cy = 360.0
（可根据具体相机标定值修改）

使用示例：
----------
tracker = PoseTracker()
output = tracker.process(color_image, depth_frame, frame_id=42)
tracker.close()

日期：2025年5月
"""


import cv2
import mediapipe as mp
import numpy as np
import os
import csv

class PoseTracker:
    """封装 Mediapipe Pose 姿态检测功能 + 打印和保存关键点信息"""
    def __init__(self, detection_confidence=0.5, tracking_confidence=0.5, output_csv_path='recordings/poses_3d.csv'):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        self.mp_drawing = mp.solutions.drawing_utils

        self.output_csv_path = output_csv_path
        self.intrinsics = {
            'fx': 600.0,
            'fy': 600.0,
            'cx': 640.0,
            'cy': 360.0
        }

        # 如果文件不存在，写入表头
        if not os.path.exists(self.output_csv_path):
            with open(self.output_csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['frame', 'landmark_id', 'x_3d', 'y_3d', 'z_3d'])

    def process(self, color_image, depth_frame=None, frame_id=None):
        """
        处理输入的彩色图像，检测并绘制姿态关键点，同时打印和保存3D坐标
        """
        if color_image is None:
            return None

        h, w, c = color_image.shape  # 获取图像尺寸

        # 转为RGB
        image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False

        # 姿态检测
        results = self.pose.process(image_rgb)

        # 准备绘制
        image_rgb.flags.writeable = True
        output_image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                output_image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
            )

            coords_list = []
            for id, lm in enumerate(results.pose_landmarks.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)

                x3d, y3d, z3d = None, None, None
                if depth_frame is not None and 0 <= cx < w and 0 <= cy < h:
                    z = depth_frame[cy, cx] / 1000.0  # mm -> meters
                    if z > 0:
                        fx, fy, cx0, cy0 = self.intrinsics['fx'], self.intrinsics['fy'], self.intrinsics['cx'], self.intrinsics['cy']
                        x3d = (cx - cx0) * z / fx
                        y3d = (cy - cy0) * z / fy
                        z3d = z
                        print(f"[PoseTracker] ID: {id} | Pixel: ({cx}, {cy}) | 3D: ({x3d:.3f}, {y3d:.3f}, {z3d:.3f})")

                        if frame_id is not None:
                            coords_list.append([frame_id, id, x3d, y3d, z3d])

            # 写入CSV
            if coords_list:
                with open(self.output_csv_path, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(coords_list)

        return cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB)

    def close(self):
        """释放资源"""
        self.pose.close()
#ctrol z 一次