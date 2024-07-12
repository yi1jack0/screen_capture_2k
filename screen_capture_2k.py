import cv2
import numpy as np
from mss import mss
import time

def screen_record_2k():
    # Define the screen capture area (2K resolution)
    width, height = 1920, 1080
    
    # Initialize the screen capture
    sct = mss()
    monitor = {"top": 0, "left": 0, "width": width, "height": height}

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('output_2k_30fps.mp4', fourcc, 30.0, (width, height))

    # Set the duration for recording (in seconds)
    duration = 10
    start_time = time.time()

    while time.time() - start_time < duration:
        # Capture the screen
        frame = np.array(sct.grab(monitor))
        
        # Convert the frame from BGRA to BGR (remove alpha channel)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        
        # Write the frame to the output file
        out.write(frame)
        
        # Optional: Display the recording screen (uncomment to use)
        # cv2.imshow('Screen Capture', frame)
        
        # Check for 'q' key to quit early
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release everything when the job is finished
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    screen_record_2k()
    print("Recording complete. Output saved as 'output_2k_30fps.mp4'")