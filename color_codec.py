import numpy as np
import cv2
import av
import os
import time
import struct
from datetime import datetime

class ColorCodec:
    def __init__(self, fps=30, width=1280, height=720, bitrate=5000000, filename=None):
        """初始化彩色视频编码器
        
        Args:
            fps: 帧率
            width: 视频宽度
            height: 视频高度
            bitrate: 视频码率
            filename: 输出文件名，如果为None则使用带时间戳的默认文件名
        """
        self.fps = fps
        self.width = width
        self.height = height
        self.frame_count = 0
        self.bitrate = bitrate
        
        # 设置文件名
        if filename is None:
            now = datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            self.filename = f"color_output_{timestamp_str}.mp4"
        else:
            self.filename = filename
        
        # 创建编码器
        self._setup_encoder()
    
    def _setup_encoder(self):
        """设置视频编码器"""
        try:
            # 创建一个容器用于视频
            self.color_container = av.open(self.filename, mode='w')
            
            # 尝试使用硬件编码，如果失败则回退到软件编码
            try:
                # 首先尝试使用硬件加速编码器（平台相关）
                hw_encoders = ['h264_nvenc', 'h264_qsv', 'h264_videotoolbox', 'h264_amf']
                
                encoder = None
                # for hw in hw_encoders:
                #     try:
                #         self.color_stream = self.color_container.add_stream(hw, rate=self.fps)
                #         encoder = hw
                #         break
                #     except (ValueError, av.error.DefinedError):
                #         continue
                
                # 如果所有硬件编码器都失败，回退到软件编码
                if encoder is None:
                    self.color_stream = self.color_container.add_stream('libx264', rate=self.fps)
                    encoder = 'libx264'
                
                print(f"使用编码器: {encoder}")
            except Exception as e:
                # 所有尝试都失败，使用标准H.264编码器
                print(f"无法初始化硬件编码器，回退到软件编码: {e}")
                self.color_stream = self.color_container.add_stream('libx264', rate=self.fps)
            
            # 设置视频流参数
            self.color_stream.width = self.width
            self.color_stream.height = self.height
            self.color_stream.pix_fmt = 'yuv420p'
            # 设置比特率
            self.color_stream.bit_rate = self.bitrate
            # 对软件编码设置优化参数
            if self.color_stream.name == 'libx264':
                self.color_stream.options = {
                    'crf': '18',  # 常量质量因子，值越低质量越高
                    'preset': 'fast'  # 编码速度优先
                }
        except Exception as e:
            print(f"设置视频编码器失败: {e}")
            raise
    
    def encode_frame(self, color_image):
        """编码一帧彩色图像
        
        Args:
            color_image: BGR格式彩色图像
            
        Returns:
            原始彩色图像
        """
        if color_image is None:
            return None
        
        try:
            # 帧计数增加
            self.frame_count += 1
            
            # BGR转RGB
            color_image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
            
            # 创建PyAV视频帧
            color_frame = av.VideoFrame.from_ndarray(color_image_rgb, format='rgb24')
            color_frame.pts = self.frame_count - 1
            
            # 编码
            for packet in self.color_stream.encode(color_frame):
                self.color_container.mux(packet)
            
            return color_image
        except Exception as e:
            print(f"编码第 {self.frame_count} 帧时出错: {e}")
            return color_image
    
    def close(self):
        """关闭编码器并保存数据"""
        if hasattr(self, 'color_container') and self.color_container:
            try:
                # 刷新编码缓冲区
                for packet in self.color_stream.encode():
                    self.color_container.mux(packet)
                    
                # 关闭容器
                self.color_container.close()
                print(f"彩色视频已保存到 {self.filename}，共 {self.frame_count} 帧")
            except Exception as e:
                print(f"关闭视频编码器时出错: {e}")
    
    def decode_video(self, filename=None):
        """解码彩色视频文件
        
        Args:
            filename: 输入视频文件名，默认使用编码时的文件名
            
        Returns:
            解码后的彩色帧列表，每帧为BGR格式numpy数组
        """
        if filename is None:
            filename = self.filename
            
        if not os.path.exists(filename):
            raise FileNotFoundError(f"找不到文件: {filename}")
            
        container = av.open(filename)
        decoded_frames = []
        
        try:
            for frame in container.decode(video=0):
                # 转换为BGR格式numpy数组
                color_frame = frame.to_ndarray(format='rgb24')
                color_frame = cv2.cvtColor(color_frame, cv2.COLOR_RGB2BGR)
                
                decoded_frames.append({
                    'color': color_frame,
                    'timestamp': frame.pts
                })
            
            print(f"已解码 {len(decoded_frames)} 帧彩色视频")
            return decoded_frames
        except Exception as e:
            print(f"解码视频时出错: {e}")
            return decoded_frames
        finally:
            container.close() 