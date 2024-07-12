import cv2
import numpy as np
from mss import mss
import time
import argparse
from datetime import datetime
import pyautogui
import os
import re

CURSOR_PATH = "resource/cursor.png"
TARGET_FPS = 60

def load_cursor_image():
    if os.path.exists(CURSOR_PATH):
        cursor = cv2.imread(CURSOR_PATH, cv2.IMREAD_UNCHANGED)
        if cursor is not None:
            print(f"Loaded cursor image. Size: {cursor.shape[1]}x{cursor.shape[0]} pixels")
            if cursor.shape[2] == 3:
                cursor = cv2.cvtColor(cursor, cv2.COLOR_BGR2BGRA)
            elif cursor.shape[2] == 4:
                print("Cursor already has an alpha channel")
            else:
                print(f"Unexpected number of channels: {cursor.shape[2]}")
        return cursor
    else:
        print(f"Cursor image not found at {CURSOR_PATH}. Recording without cursor.")
        return None

def overlay_cursor(frame, cursor, x, y):
    if cursor is None:
        return frame
    
    h, w = cursor.shape[:2]
    frame_h, frame_w = frame.shape[:2]
    
    y_start = max(0, y)
    y_end = min(frame_h, y + h)
    x_start = max(0, x)
    x_end = min(frame_w, x + w)
    
    if y_end <= y_start or x_end <= x_start:
        return frame

    alpha = cursor[y_start-y:y_end-y, x_start-x:x_end-x, 3] / 255.0
    alpha = np.dstack([alpha] * 3)
    
    cursor_area = cursor[y_start-y:y_end-y, x_start-x:x_end-x, :3]
    
    try:
        overlay = (
            frame[y_start:y_end, x_start:x_end] * (1 - alpha) + 
            cursor_area * alpha
        ).astype(np.uint8)
        frame[y_start:y_end, x_start:x_end] = overlay
    except ValueError as e:
        print(f"Error overlaying cursor: {e}")
        print(f"Frame shape: {frame.shape}, Cursor shape: {cursor.shape}")
        print(f"Overlay area: y[{y_start}:{y_end}], x[{x_start}:{x_end}]")
        print(f"Alpha shape: {alpha.shape}, Cursor area shape: {cursor_area.shape}")
    
    return frame

def parse_duration(duration_str):
    if isinstance(duration_str, int):
        return duration_str
    
    total_seconds = 0
    parts = re.findall(r'(\d+)([sm]?)', duration_str.lower())
    
    for value, unit in parts:
        value = int(value)
        if unit == 'm':
            total_seconds += value * 60
        elif unit == 's' or unit == '':
            total_seconds += value
    
    return total_seconds

def cleanup_small_files(min_size_kb=2):
    removed_files = []
    for filename in os.listdir('.'):
        if filename.endswith('.mp4'):
            file_path = os.path.join('.', filename)
            file_size_kb = os.path.getsize(file_path) / 1024
            if file_size_kb < min_size_kb:
                os.remove(file_path)
                removed_files.append(filename)
    
    if removed_files:
        print(f"Removed {len(removed_files)} small file(s): {', '.join(removed_files)}")
    else:
        print("No small files to remove.")

def screen_record_2k_mouse_follow(duration, is_portrait=False):
    if is_portrait:
        width, height = 1440, 2560
        orientation = "portrait"
    else:
        width, height = 2560, 1440
        orientation = "landscape"
    
    sct = mss()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"output_{width}x{height}_{orientation}_{timestamp}.mp4"
    
    cursor = load_cursor_image()
    
    # Capture a few frames to determine actual FPS
    test_frames = 60
    start_time = time.perf_counter()
    for _ in range(test_frames):
        sct.grab({"left": 0, "top": 0, "width": width, "height": height})
    end_time = time.perf_counter()
    actual_fps = test_frames / (end_time - start_time)
    
    print(f"Detected capture rate: {actual_fps:.2f} FPS")
    
    # Use the lower of actual or target FPS
    fps = min(actual_fps, TARGET_FPS)
    print(f"Recording at {fps:.2f} FPS")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))
    
    frame_time = 1 / fps
    total_frames = int(duration * fps)
    
    start_time = time.perf_counter()
    for frame_count in range(total_frames):
        frame_start = time.perf_counter()
        
        mouse_x, mouse_y = pyautogui.position()
        
        left = max(mouse_x - width // 2, 0)
        top = max(mouse_y - height // 2, 0)
        
        screen_width, screen_height = pyautogui.size()
        if left + width > screen_width:
            left = screen_width - width
        if top + height > screen_height:
            top = screen_height - height
        
        monitor = {"left": left, "top": top, "width": width, "height": height}
        
        frame = np.array(sct.grab(monitor))
        frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
        
        cursor_x = mouse_x - left
        cursor_y = mouse_y - top
        frame = overlay_cursor(frame, cursor, cursor_x, cursor_y)
        
        out.write(frame)
        
        if frame_count % int(fps) == 0:
            elapsed_time = time.perf_counter() - start_time
            print(f"Processed {frame_count} frames. Current mouse position: ({mouse_x}, {mouse_y}). Elapsed time: {elapsed_time:.2f}s")
        
        # Wait precisely for next frame
        while time.perf_counter() - frame_start < frame_time:
            time.sleep(0.0001)
    
    out.release()
    cv2.destroyAllWindows()
    
    total_time = time.perf_counter() - start_time
    print(f"Total frames processed: {total_frames}")
    print(f"Actual recording duration: {total_time:.2f} seconds")
    print(f"Effective frame rate: {total_frames / total_time:.2f} FPS")
    return output_filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record screen in 2K resolution, following the mouse with custom cursor.")
    parser.add_argument("duration", type=str, help="Duration of the recording (e.g., '30s', '1m', '1m30s', '90')")
    parser.add_argument("portt", nargs='?', help="Use 'portt' for portrait mode (1440x2560)", default=None)
    args = parser.parse_args()

    try:
        duration_seconds = parse_duration(args.duration)
        is_portrait = args.portt == 'portt'
        orientation = "portrait" if is_portrait else "landscape"
        print(f"Recording for {duration_seconds} seconds in {orientation} orientation...")
        output_file = screen_record_2k_mouse_follow(duration_seconds, is_portrait)
        print(f"Recording complete. Captured and saved as '{output_file}'")
    finally:
        cleanup_small_files()