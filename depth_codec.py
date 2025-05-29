import numpy as np
import zstandard as zstd
import struct
import os
import time
import matplotlib.pyplot as plt
import cv2
from tqdm import tqdm
import pyrealsense2 as rs
import open3d as o3d
from datetime import datetime

class DepthZstdCodec:
    def __init__(self, filename=None, fps=30, width=1280, height=720, compression_level=3):
        """初始化编码器并打开文件进行流式写入
        
        Args:
            filename: 输出文件名。如果为 None，则自动生成带时间戳的文件名。
            fps: 帧率 (当前未使用)
            width: 默认宽度 (当前未使用)
            height: 默认高度 (当前未使用)
            compression_level: Zstandard 压缩级别
        """
        if filename is None:
            # 使用时间戳生成默认文件名
            now = datetime.now()
            timestamp_str = now.strftime("%Y%m%d_%H%M%S")
            self.filename = f"depth_frames_{timestamp_str}.zst"
        else:
            self.filename = filename
            
        self.fps = fps
        self.width = width # 注意：如果encode_frame从图像中获取宽度和高度，初始化的宽度和高度不会被使用
        self.height = height
        self.frame_count = 0
        self.compression_level = compression_level
        
        # 初始化编码器和文件写入
        self._setup_encoder_and_writer()
        
    def _setup_encoder_and_writer(self):
        """设置Zstandard压缩编码器和文件写入器"""
        self.zstd_compressor = zstd.ZstdCompressor(
            level=self.compression_level, 
            threads=-1, 
            write_checksum=True
        )
        try:
            self.output_file = open(self.filename, 'wb')
            # 先写入一个 8 字节的占位符，用于存储总帧数
            self.output_file.write(struct.pack('Q', 0)) 
        except IOError as e:
            print(f"无法打开文件 {self.filename} 进行写入: {e}")
            raise
    
    def encode_frame(self, depth_image):
        """编码一帧深度图像并直接写入文件
        
        Args:
            depth_image: 深度图像数据 (numpy array, uint16)，单位通常为毫米
        """
        if not hasattr(self, 'output_file') or self.output_file.closed:
            raise RuntimeError("文件未打开或已关闭，无法编码帧。")

        height, width = depth_image.shape
        
        # 压缩深度数据
        try:
            compressed_depth = self.zstd_compressor.compress(depth_image.tobytes())
        except Exception as e:
            print(f"压缩第 {self.frame_count + 1} 帧时出错: {e}")
            # 可以选择是继续还是抛出异常
            raise 

        timestamp = self.frame_count # 使用帧索引作为时间戳
        
        # 写入帧元数据和压缩数据
        try:
            # 写入宽度、高度
            self.output_file.write(struct.pack('II', width, height))
            # 写入压缩数据大小和时间戳
            self.output_file.write(struct.pack('Q', len(compressed_depth)))
            self.output_file.write(struct.pack('Q', timestamp))
            # 写入压缩数据
            self.output_file.write(compressed_depth)
        except IOError as e:
            print(f"写入第 {self.frame_count + 1} 帧到文件时出错: {e}")
            # 可以选择是继续还是抛出异常
            raise

        self.frame_count += 1

    def close(self):
        """完成文件写入，更新总帧数并关闭文件"""
        if hasattr(self, 'output_file') and not self.output_file.closed:
            # 保存当前文件指针位置
            current_pos = self.output_file.tell()
            # 移动到文件开头
            self.output_file.seek(0)
            # 写入实际的总帧数
            self.output_file.write(struct.pack('Q', self.frame_count))
            # 关闭文件
            self.output_file.close()
            print(f"编码完成，共 {self.frame_count} 帧已保存到 {self.filename}")
        else:
            print("文件写入流未初始化或已关闭。")
            
    def decode_file(self, filename='depth_frames.zst'):
        """从文件解码深度数据（一次性解码所有帧）
        
        Args:
            filename: 输入文件名
            
        Returns:
            解码后的深度帧列表，每帧为numpy数组
        """
        return self.get_all_frames(filename)
    
    # def get_all_frames(self, filename='depth_frames.zst'):
    #     """从文件中一次性获取所有的深度帧
        
    #     Args:
    #         filename: 输入文件名
            
    #     Returns:
    #         解码后的深度帧列表，每帧为numpy数组
    #     """
    #     if not os.path.exists(filename):
    #         raise FileNotFoundError(f"找不到文件: {filename}")
            
    #     decompressor = zstd.ZstdDecompressor()
    #     decoded_frames = []
        
    #     with open(filename, 'rb') as f:
    #         # 读取总帧数
    #         frame_count = struct.unpack('Q', f.read(8))[0]
            
    #         for _ in tqdm(range(frame_count)):
    #             # 读取宽度、高度
    #             width, height = struct.unpack('II', f.read(8))
                
    #             # 读取压缩数据大小和时间戳
    #             compressed_size = struct.unpack('Q', f.read(8))[0]
    #             timestamp = struct.unpack('Q', f.read(8))[0]
                
    #             # 读取压缩数据
    #             compressed_data = f.read(compressed_size)
                
    #             # 解压缩数据
    #             decompressed_data = decompressor.decompress(compressed_data)
                
    #             # 转换为numpy数组
    #             depth_frame = np.frombuffer(decompressed_data, dtype=np.uint16).reshape(height, width)
                
    #             # 添加到帧列表
    #             decoded_frames.append({
    #                 'depth': depth_frame,
    #                 'timestamp': timestamp
    #             })
        
    #     print(f"已解码 {len(decoded_frames)} 帧深度数据")
    #     return decoded_frames

    def get_all_frames(self, filename='depth_frames.zst'):
        """从文件中一次性获取所有的深度帧"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"找不到文件: {filename}")
            
        decompressor = zstd.ZstdDecompressor()
        decoded_frames = []

        with open(filename, 'rb') as f:
            frame_count = struct.unpack('Q', f.read(8))[0]
            print(f"开始解码深度帧，总数: {frame_count}")

            for i in range(frame_count):
                try:
                    width, height = struct.unpack('II', f.read(8))
                    compressed_size = struct.unpack('Q', f.read(8))[0]
                    timestamp = struct.unpack('Q', f.read(8))[0]
                    compressed_data = f.read(compressed_size)
                    decompressed_data = decompressor.decompress(compressed_data)
                    depth_frame = np.frombuffer(decompressed_data, dtype=np.uint16).reshape(height, width)

                    decoded_frames.append({
                        'depth': depth_frame,
                        'timestamp': timestamp
                    })

                except Exception as e:
                    print(f"第 {i} 帧解码失败: {e}")
                    break

        print(f"已成功解码 {len(decoded_frames)} 帧深度数据")
        return decoded_frames

    
    def open_file_for_streaming(self, filename='depth_frames.zst'):
        """打开文件准备流式解码
        
        Args:
            filename: 输入文件名
        """
        if not os.path.exists(filename):
            raise FileNotFoundError(f"找不到文件: {filename}")
            
        self.stream_file = open(filename, 'rb')
        self.stream_decompressor = zstd.ZstdDecompressor()
        
        # 读取总帧数
        self.stream_frame_count = struct.unpack('Q', self.stream_file.read(8))[0]
        self.stream_current_frame = 0
        
        print(f"文件已打开，共有 {self.stream_frame_count} 帧")

        return self.stream_frame_count
    
    def get_next_frame(self):
        """获取下一帧深度数据
        
        Returns:
            解码后的下一帧深度数据，如果已到文件末尾则返回None
        """
        if not hasattr(self, 'stream_file') or self.stream_file.closed:
            raise RuntimeError("请先调用open_file_for_streaming打开文件")
            
        if self.stream_current_frame >= self.stream_frame_count:
            print("已到达文件末尾")
            return None
            
        # 读取宽度、高度
        width, height = struct.unpack('II', self.stream_file.read(8))
        
        # 读取压缩数据大小和时间戳
        compressed_size = struct.unpack('Q', self.stream_file.read(8))[0]
        timestamp = struct.unpack('Q', self.stream_file.read(8))[0]
        
        # 读取压缩数据
        compressed_data = self.stream_file.read(compressed_size)
        
        # 解压缩数据
        decompressed_data = self.stream_decompressor.decompress(compressed_data)
        
        # 转换为numpy数组
        depth_frame = np.frombuffer(decompressed_data, dtype=np.uint16).reshape(height, width)
        
        self.stream_current_frame += 1
        
        return {
            'depth': depth_frame,
            'timestamp': timestamp,
            'frame_index': self.stream_current_frame - 1,
            'progress': f"{self.stream_current_frame}/{self.stream_frame_count}"
        }
    
    def close_stream(self):
        """关闭流式解码的文件"""
        if hasattr(self, 'stream_file') and not self.stream_file.closed:
            self.stream_file.close()
            print("文件流已关闭")
        
    def clear(self):
        """重置帧计数器 (注意：这不会清空已写入文件的内容)"""
        self.frame_count = 0
        # 注意：如果需要重新开始编码到同一个文件，需要先删除或重命名旧文件 