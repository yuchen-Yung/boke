# # hand_tracker.py
# import cv2
# import mediapipe as mp
# import numpy as np

# class HandTracker:
#     def __init__(self, max_num_hands=2, min_detection_confidence=0.7):
#         """初始化HandTracker"""
#         self.mp_hands = mp.solutions.hands
#         self.hands = self.mp_hands.Hands(
#             static_image_mode=False,
#             max_num_hands=max_num_hands,
#             min_detection_confidence=min_detection_confidence
#         )
#         self.mp_drawing = mp.solutions.drawing_utils

#     def process(self, color_image, depth_frame=None):
#         """
#         处理彩色图像，绘制手部关键点。

#         Args:
#             color_image: BGR格式图像
#             depth_frame: (可选) RealSense获取的深度帧对象，用于真实z信息
#         Returns:
#             output_image: BGR图，带手部关键点绘制
#         """
#         # 转成RGB供Mediapipe使用
#         image_rgb = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
#         image_rgb.flags.writeable = False
#         results = self.hands.process(image_rgb)
#         image_rgb.flags.writeable = True
#         output_image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)  # 再转回BGR用于OpenCV绘制

#         if results.multi_hand_landmarks:
#             for hand_landmarks in results.multi_hand_landmarks:
#                 self.mp_drawing.draw_landmarks(
#                     output_image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
#                 )

#         return output_image
# hand_tracker.py

# hand_tracker.py
# hand_tracker.py

import mediapipe as mp
import cv2

class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils

    def process(self, image_bgr):
        """输入 BGR 图像，返回绘制好关键点的图像"""
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    image_bgr,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
        return image_bgr
