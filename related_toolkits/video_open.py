"""
视频播放与逐帧控制工具（Video Playback Controller with Frame Info）
=====================================================================

功能简介：
----------
本脚本提供一个基于 OpenCV 的视频播放工具，支持多种视频格式（如 .mp4, .avi, .mov 等），
允许用户通过键盘交互进行暂停播放、逐帧前进与后退，并在播放窗口左上角实时显示当前帧号与总帧数。

适用场景：
----------
- 视频数据检查与标签审核
- 逐帧分析姿态、目标检测等视觉任务输出结果
- 调试和验证计算机视觉处理效果

输入说明：
----------
- 通过文件选择框选择一个本地视频文件，支持常见视频格式（.mp4, .avi, .mov, .mkv 等）

输出说明：
----------
- 图像窗口播放视频内容，并在左上角显示帧号信息（Frame: 当前帧 / 总帧数）
- 无文件输出（仅用于播放和交互式控制）

控制操作：
----------
- 空格键 `' '` ：暂停 / 恢复播放
- 数字键 `'1'`：暂停状态下后退一帧
- 数字键 `'3'`：暂停状态下前进一步
- 字母键 `'q'`：退出播放

使用方法：
----------
1. 运行脚本后会弹出文件选择框，选中视频文件后开始播放；
2. 在播放过程中可使用上述按键实现帧级控制和实时观察；
3. 支持暂停查看任意帧图像内容，适合用于逐帧评估。

日期：2025年5月
"""



import cv2
import os
from tkinter import Tk, filedialog

def select_video_file():
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    file_path = filedialog.askopenfilename(
        title="选择视频文件",
        filetypes=[("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
    )
    return file_path

def play_video(video_path):
    if not os.path.exists(video_path):
        print(f"视频文件不存在: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"视频信息：")
    print(f"路径：{video_path}")
    print(f"FPS：{fps}")
    print(f"分辨率：{width}x{height}")
    print(f"总帧数：{total_frames}\n")

    paused = False
    current_frame = 0

    while cap.isOpened():
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("播放完成或读取错误")
                break
            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        else:
            # 若暂停状态，手动定位到当前帧重读
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
            ret, frame = cap.read()
            if not ret:
                break

        # 在左上角绘制帧编号
        cv2.putText(frame, f"Frame: {current_frame}/{total_frames}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Video Playback - SPACE:暂停/播放, 1:后退, 3:前进, q:退出", frame)

        key = cv2.waitKey(0 if paused else int(1000 / fps)) & 0xFF

        if key == ord('q'):
            print("用户中断播放")
            break
        elif key == ord(' '):  # 空格键暂停/播放
            paused = not paused
        elif key == ord('1'):  # 后退一帧
            paused = True
            current_frame = max(0, current_frame - 2)  # 后退1帧，设置-2是为了抵消自动+1
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        elif key == ord('3'):  # 前进一帧
            paused = True
            current_frame = min(total_frames - 1, current_frame + 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    print("请选择你要播放的视频文件（支持 .mp4, .avi, .mov, .mkv 等）")
    video_path = select_video_file()

    if video_path:
        play_video(video_path)
    else:
        print("未选择视频文件，程序已退出。")
