"""
3D人体骨架逐帧可视化工具（Pose 3D Skeleton Player）
======================================================

【功能概述】：
本脚本用于加载由 Mediapipe 等系统输出的人体关键点 3D 坐标 CSV 文件，并对每一帧的骨架姿态进行三维可视化展示。
支持逐帧播放，清晰展示下肢骨架结构，包括左右大腿与小腿之间的连接。

【输入说明】：
- 输入文件为 `.csv` 格式，包含人体姿态关键点的三维坐标数据。
- CSV 文件需包含以下列字段：
    - `frame`：帧编号（整数）
    - `landmark_id`：关键点编号（整数，符合 Mediapipe 定义，如 23-28 表示下肢）
    - `x_3d`, `y_3d`, `z_3d`：关键点的三维相机坐标（单位：米）

【可视化说明】：
- 可视化采用 `matplotlib` 3D 图形展示：
    - 蓝色点表示关键点位置
    - 红色线表示下肢连接（包括左右大腿、小腿之间的骨架线段）
    - 每帧暂停 0.1 秒以模拟自动播放效果
    - 默认视角为仰视（elev=10, azim=180），坐标轴范围固定为：
        - X: [-1, 1]
        - Y: [-1, 1]
        - Z: [0, 2]

【输出说明】：
- 本脚本为可视化工具，无文件写入或导出，仅在屏幕上逐帧播放 3D 骨架结构。

【使用方法】：
1. 确保安装依赖库（matplotlib、numpy 等）
2. 修改脚本中 `auto_play()` 函数的 `csv_path` 参数，指定要可视化的 CSV 文件路径
3. 运行脚本，即可逐帧播放可视化效果

【适用场景】：
适用于步态分析、人体姿态检测调试、康复训练评估、可视化展示等任务。

日期：2025年5月
"""

import csv
import os
import matplotlib.pyplot as plt
import numpy as np
import imageio

POSE_CONNECTIONS = [
    (23, 25), (25, 27),      # 左腿
    (24, 26), (26, 28),      # 右腿
    (23, 24),                # 骨盆
    (23, 11), (24, 12),      # 骨盆到肩膀
    (11, 12)                 # 肩膀
]

def load_pose_data(csv_path):
    pose_dict = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            frame_id = int(row['frame'])
            landmark_id = int(row['landmark_id'])
            x = float(row['x_3d'])
            y = float(row['y_3d'])
            z = float(row['z_3d'])
            if frame_id not in pose_dict:
                pose_dict[frame_id] = {}
            pose_dict[frame_id][landmark_id] = (x, y, z)
    return pose_dict

def draw_pose_frame(ax, landmarks):
    xs, ys, zs = [], [], []
    for id, (x, y, z) in landmarks.items():
        xs.append(x)
        ys.append(y)
        zs.append(z)
        ax.text(x, y, z, str(id), fontsize=6, color='black')
    ax.scatter(xs, ys, zs, c='blue')

    for start, end in POSE_CONNECTIONS:
        if start in landmarks and end in landmarks:
            x1, y1, z1 = landmarks[start]
            x2, y2, z2 = landmarks[end]
            ax.plot([x1, x2], [y1, y2], [z1, z2], c='red', linewidth=2)

    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_zlim(0, 2)
    ax.view_init(elev=90, azim=180)  # Y轴向上，Z轴向前
    ax.axis('off')

def generate_gif(pose_dict, output_gif='pose_output.gif'):
    frame_ids = sorted(pose_dict.keys())
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, projection='3d')
    temp_dir = 'temp_pose_frames'
    os.makedirs(temp_dir, exist_ok=True)
    images = []

    for i, frame_id in enumerate(frame_ids):
        ax.clear()
        draw_pose_frame(ax, pose_dict[frame_id])
        temp_path = os.path.join(temp_dir, f'frame_{i:04d}.png')
        plt.savefig(temp_path, bbox_inches='tight')
        images.append(imageio.imread(temp_path))

    imageio.mimsave(output_gif, images, duration=0.1)
    plt.close()

    for f in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, f))
    os.rmdir(temp_dir)
    print(f"GIF已保存：{output_gif}")

if __name__ == '__main__':
    csv_path = 'E:/pythonlibary/work/python/Depth_camera/D455_camera_code/project/project/recordings/poses_3d.csv'
    if not os.path.exists(csv_path):
        print(f"文件不存在: {csv_path}")
    else:
        data = load_pose_data(csv_path)
        generate_gif(data)
