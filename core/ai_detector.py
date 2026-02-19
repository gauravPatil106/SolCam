"""
AI Detector Module
YOLOv8n-based object detection for surveillance
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import random
import config
from utils.logger import get_logger


class AIDetector:
    """YOLOv8n object detector for surveillance"""
    
    def __init__(self, model_path: Optional[str] = None, 
                 confidence_threshold: float = None):
        """
        Initialize AI detector
        
        Args:
            model_path: Path to YOLOv8 model (default: from config)
            confidence_threshold: Minimum confidence for detections
        """
        self.model_path = model_path or str(config.YOLO_MODEL_PATH)
        self.confidence_threshold = confidence_threshold or config.AI_CONFIDENCE_THRESHOLD
        self.important_classes = config.IMPORTANT_CLASSES
        self.simulate = config.SIMULATE_DETECTION
        self.model = None
        self.model_loaded = False
        self.logger = get_logger()
        
        if not self.simulate:
            self._load_model()
    
    def _load_model(self):
        """Load YOLOv8n model"""
        try:
            from ultralytics import YOLO
            
            # Download model if it doesn't exist
            if not config.YOLO_MODEL_PATH.exists():
                print("Downloading YOLOv8n model (first time only)...")
                self.model = YOLO('yolov8n.pt')
                # Save to models directory
                config.YOLO_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            else:
                self.model = YOLO(str(config.YOLO_MODEL_PATH))
            
            self.model_loaded = True
            print("YOLOv8n model loaded successfully")
            
        except Exception as e:
            print(f"Error loading YOLOv8n model: {e}")
            print("Falling back to simulated detection mode")
            self.simulate = True
            self.model_loaded = False
    
    def detect(self, frame: np.ndarray) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
        """
        Detect objects in frame
        
        Args:
            frame: OpenCV image (BGR format)
            
        Returns:
            List of (class_name, confidence, bbox) tuples
            bbox format: (x1, y1, x2, y2)
        """
        if self.simulate:
            return self._simulate_detection(frame)
        
        if not self.model_loaded or self.model is None:
            return []
        
        try:
            # Run inference
            results = self.model(frame, verbose=False)
            
            detections = []
            
            for result in results:
                boxes = result.boxes
                
                for box in boxes:
                    # Get class name
                    class_id = int(box.cls[0])
                    class_name = result.names[class_id]
                    
                    # Filter by important classes
                    if class_name not in self.important_classes:
                        continue
                    
                    # Get confidence
                    confidence = float(box.conf[0])
                    
                    # Filter by confidence threshold
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Get bounding box
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    bbox = (int(x1), int(y1), int(x2), int(y2))
                    
                    detections.append((class_name, confidence, bbox))
            
            return detections
            
        except Exception as e:
            print(f"Detection error: {e}")
            return []
    
    def _simulate_detection(self, frame: np.ndarray) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
        """
        Simulate detections for testing (without actual AI)
        
        Args:
            frame: OpenCV image
            
        Returns:
            Simulated detections
        """
        # Randomly generate detections (10% chance per frame)
        if random.random() < 0.1:
            h, w = frame.shape[:2]
            
            # Random object
            obj = random.choice(self.important_classes)
            confidence = random.uniform(0.6, 0.95)
            
            # Random bounding box
            x1 = random.randint(0, w // 2)
            y1 = random.randint(0, h // 2)
            x2 = random.randint(x1 + 50, min(x1 + 200, w))
            y2 = random.randint(y1 + 50, min(y1 + 200, h))
            
            bbox = (x1, y1, x2, y2)
            
            return [(obj, confidence, bbox)]
        
        return []
    
    def set_confidence_threshold(self, threshold: float):
        """
        Update confidence threshold
        
        Args:
            threshold: New confidence threshold (0.0 - 1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))
    
    def draw_detections(self, frame: np.ndarray, 
                       detections: List[Tuple[str, float, Tuple[int, int, int, int]]]) -> np.ndarray:
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: OpenCV image
            detections: List of detections from detect()
            
        Returns:
            Frame with drawn detections
        """
        frame_copy = frame.copy()
        
        for class_name, confidence, (x1, y1, x2, y2) in detections:
            # Draw bounding box
            color = self._get_class_color(class_name)
            cv2.rectangle(frame_copy, (x1, y1), (x2, y2), color, 2)
            
            # Draw label background
            label = f"{class_name} {confidence:.2f}"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame_copy, (x1, y1 - label_h - 10), (x1 + label_w, y1), color, -1)
            
            # Draw label text
            cv2.putText(frame_copy, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return frame_copy
    
    def _get_class_color(self, class_name: str) -> Tuple[int, int, int]:
        """Get color for object class (BGR format)"""
        colors = {
            'person': (0, 255, 0),      # Green
            'car': (255, 0, 0),         # Blue
            'truck': (0, 165, 255),     # Orange
            'motorcycle': (255, 0, 255) # Magenta
        }
        return colors.get(class_name, (0, 255, 255))  # Yellow default
