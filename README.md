# 多传感器融合可视化系统

这是一个基于PyQt6的多传感器融合可视化系统，支持雷达点云和RealSense深度相机的数据采集、显示和录制。

## 功能特点

- **雷达点云可视化**：3D实时显示雷达点云数据
- **RealSense相机集成**：显示彩色图像和深度图像
- **多传感器融合**：在同一界面同时显示雷达和相机数据
- **数据录制**：支持雷达点云、彩色视频和深度图像的录制
- **高效编码**：
  - 点云使用Feather格式存储
  - 深度流使用Zstandard压缩
  - 彩色流使用H.264视频编码

## 系统要求

- Python 3.8+
- Intel RealSense相机（如D435i）
- 兼容的雷达传感器（通过串口连接）
- Windows/Linux/MacOS

## 安装指南

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/multi-sensor-fusion.git
cd multi-sensor-fusion
```

2. 安装依赖项：
```bash
pip install -r requirements.txt
```

3. 安装RealSense SDK（如果尚未安装）:
   - 按照[Intel RealSense官方指南](https://github.com/IntelRealSense/librealsense/blob/master/doc/installation.md)安装

## 使用方法

1. 启动应用程序：
```bash
python main.py
```

2. 连接传感器：
   - 点击"连接雷达"按钮连接雷达设备
   - 点击"连接相机"按钮连接RealSense相机

3. 数据采集：
   - 雷达：点击"开始"按钮开始采集雷达数据
   - 相机：连接后自动开始数据流

4. 数据录制：
   - 雷达：点击"录制"按钮录制点云数据
   - 相机：点击"录制相机"按钮同时录制彩色和深度流

5. 录制文件保存在`recordings`目录中，使用时间戳命名。

## 文件格式

- 雷达点云：Feather格式（.feather）
- 深度流：Zstandard压缩文件（.zst）
- 彩色流：MP4视频文件（.mp4）

## 注意事项

- 确保雷达设备已正确连接到系统，且COM端口可用
- 确保RealSense相机已正确连接并被系统识别
- 视频和深度数据可能会占用大量存储空间，请确保有足够的硬盘空间

## 架构说明

系统采用多进程架构，主要组件包括：

1. **RadarVisualizer**: 主GUI界面，负责数据可视化和用户交互
2. **RadarSensor**: 雷达传感器类，在独立进程中处理雷达数据
3. **RealSenseSensor**: RealSense相机类，在独立进程中处理相机数据流
4. **DepthZstdCodec**: 深度图像压缩编解码器
5. **ColorCodec**: 彩色视频压缩编解码器

多进程设计提供了以下优势：
- 数据采集和处理不阻塞GUI
- 更高效的CPU利用率
- 系统稳定性提升，单个传感器故障不会影响整个系统

## 开发指南

### 编译和安装的先决条件

- Python 3.8+
- PyQt6和相关依赖项
- Intel RealSense SDK
- Zstandard压缩库
- PyAV多媒体处理库

### 添加新传感器

要添加新的传感器类型：

1. 参照`RadarSensor`或`RealSenseSensor`创建新的传感器类
2. 实现多进程数据处理
3. 在`RadarVisualizer`中添加相应的UI和处理逻辑 