from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import mediapipe as mp
import numpy as np
import math
import json
import asyncio
import base64
from typing import List, Dict
import time
from dataclasses import dataclass, asdict
from collections import deque, Counter

app = FastAPI(title="Gesture Control System", version="v2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MediaPipe Hands Setup
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

@dataclass
class GestureData:
    gesture: str
    confidence: float
    hand_type: str
    fingers_open: int
    thumb_state: str
    landmarks: List[Dict]
    timestamp: float
    fps: float

class GestureDetector:
    def __init__(self):
        self.gesture_history = deque(maxlen=10)
        self.prev_time = time.time()
        self.fps = 0
        
    def calculate_distance(self, p1, p2):
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2 + (p2.z - p1.z)**2)
    
    def calculate_angle(self, p1, p2, p3):
        a = np.array([p1.x, p1.y, p1.z])
        b = np.array([p2.x, p2.y, p2.z])
        c = np.array([p3.x, p3.y, p3.z])
        ba = a - b
        bc = c - b
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)
    
    def is_finger_open(self, tip_idx, pip_idx, mcp_idx, wrist, landmarks):
        tip = landmarks[tip_idx]
        pip = landmarks[pip_idx]
        mcp = landmarks[mcp_idx]
        wrist_tip = self.calculate_distance(wrist, tip)
        wrist_pip = self.calculate_distance(wrist, pip)
        return wrist_tip > wrist_pip * 1.2
    
    def is_thumb_open(self, landmarks, hand_type):
        thumb_cmc = landmarks[1]
        thumb_mcp = landmarks[2]
        thumb_ip = landmarks[3]
        angle = self.calculate_angle(thumb_cmc, thumb_mcp, thumb_ip)
        return angle > 30
    
    def detect_gesture(self, landmarks, hand_type="Right"):
        wrist = landmarks[0]
        
        fingers = {
            'thumb': self.is_thumb_open(landmarks, hand_type),
            'index': self.is_finger_open(8, 6, 5, wrist, landmarks),
            'middle': self.is_finger_open(12, 10, 9, wrist, landmarks),
            'ring': self.is_finger_open(16, 14, 13, wrist, landmarks),
            'pinky': self.is_finger_open(20, 18, 17, wrist, landmarks)
        }
        
        open_count = sum(fingers.values())
        gesture = "UNKNOWN"
        confidence = 0.0
        
        if open_count == 0:
            gesture = "FIST"
            confidence = 0.95
        elif open_count == 5:
            gesture = "PALM"
            confidence = 0.95
        elif fingers['index'] and fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
            if not fingers['thumb']:
                gesture = "PEACE"
                confidence = 0.92
            else:
                gesture = "SPIDERMAN"
                confidence = 0.85
        elif fingers['index'] and not fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
            if not fingers['thumb']:
                gesture = "POINT"
                confidence = 0.90
            else:
                gesture = "THUMB_POINT"
                confidence = 0.85
        elif fingers['thumb'] and not fingers['index'] and not fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
            gesture = "THUMBS UP"
            confidence = 0.93
        elif fingers['thumb'] and fingers['index']:
            thumb_tip = landmarks[4]
            index_tip = landmarks[8]
            distance = self.calculate_distance(thumb_tip, index_tip)
            if distance < 0.05 and fingers['middle'] and fingers['ring'] and fingers['pinky']:
                gesture = "OK"
                confidence = 0.88
        elif fingers['index'] and not fingers['middle'] and not fingers['ring'] and fingers['pinky']:
            gesture = "ROCK"
            confidence = 0.87
        elif fingers['index'] and fingers['middle'] and fingers['ring'] and not fingers['pinky']:
            gesture = "THREE"
            confidence = 0.88
        elif fingers['thumb'] and fingers['index'] and not fingers['middle'] and not fingers['ring'] and not fingers['pinky']:
            gesture = "GUN"
            confidence = 0.85
        else:
            gesture = "GESTURE"
            confidence = 0.5 + (open_count * 0.1)
        
        self.gesture_history.append(gesture)
        if len(self.gesture_history) >= 5:
            most_common = Counter(self.gesture_history).most_common(1)[0]
            if most_common[1] >= 4:
                gesture = most_common[0]
                confidence = min(0.99, confidence + 0.1)
        
        return gesture, confidence, fingers, open_count
    
    def get_fps(self):
        current_time = time.time()
        self.fps = 1 / (current_time - self.prev_time) if (current_time - self.prev_time) > 0 else 0
        self.prev_time = current_time
        return round(self.fps, 1)

detector = GestureDetector()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Gesture Control System API", "version": "v2.0", "status": "active"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    cap = None
    
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            await websocket.send_json({
                "error": "Camera not available",
                "status": "error"
            })
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        await websocket.send_json({
            "status": "connected",
            "message": "Camera initialized",
            "resolution": {"width": 640, "height": 480}
        })
        
        while True:
            try:
                try:
                    msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                    data = json.loads(msg)
                    if data.get("action") == "stop":
                        break
                except asyncio.TimeoutError:
                    pass
                
                success, frame = cap.read()
                if not success:
                    continue
                
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)
                
                fps = detector.get_fps()
                
                gesture_data = {
                    "gesture": "NO HAND",
                    "confidence": 0.0,
                    "hand_type": "None",
                    "fingers_open": 0,
                    "thumb_state": "closed",
                    "landmarks": [],
                    "timestamp": time.time(),
                    "fps": fps,
                    "frame": None
                }
                
                if results.multi_hand_landmarks:
                    for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                        hand_type = "Right"
                        if results.multi_handedness:
                            hand_type = results.multi_handedness[idx].classification[0].label
                        
                        landmarks = hand_landmarks.landmark
                        gesture, confidence, fingers, open_count = detector.detect_gesture(landmarks, hand_type)
                        
                        mp_draw.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )
                        
                        cv2.putText(frame, f"{gesture} ({confidence:.0%})", 
                                   (20, 50 + idx * 40), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                        
                        landmark_list = []
                        for lm in landmarks:
                            landmark_list.append({
                                "x": lm.x,
                                "y": lm.y,
                                "z": lm.z
                            })
                        
                        gesture_data = {
                            "gesture": gesture,
                            "confidence": round(confidence, 2),
                            "hand_type": hand_type,
                            "fingers_open": open_count,
                            "thumb_state": "open" if fingers['thumb'] else "closed",
                            "fingers": {
                                "thumb": fingers['thumb'],
                                "index": fingers['index'],
                                "middle": fingers['middle'],
                                "ring": fingers['ring'],
                                "pinky": fingers['pinky']
                            },
                            "landmarks": landmark_list,
                            "timestamp": time.time(),
                            "fps": fps
                        }
                
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                gesture_data["frame"] = f"data:image/jpeg;base64,{frame_base64}"
                
                await websocket.send_json(gesture_data)
                await asyncio.sleep(0.033)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error in stream: {e}")
                await asyncio.sleep(0.1)
    
    finally:
        if cap:
            cap.release()
        manager.disconnect(websocket)
        print("Client disconnected, camera released")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)