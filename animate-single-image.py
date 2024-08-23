import os
import time
import math
import fcntl
import ctypes
import numpy as np
from PIL import Image

# FBIOGET_VSCREENINFO and FBIOGET_FSCREENINFO ioctl commands
FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602

class FixScreenInfo(ctypes.Structure):
    _fields_ = [
        ('id_name', ctypes.c_char * 16),
        ('smem_start', ctypes.c_ulong),
        ('smem_len', ctypes.c_uint32),
        ('type', ctypes.c_uint32),
        ('type_aux', ctypes.c_uint32),
        ('visual', ctypes.c_uint32),
        ('xpanstep', ctypes.c_uint16),
        ('ypanstep', ctypes.c_uint16),
        ('ywrapstep', ctypes.c_uint16),
        ('line_length', ctypes.c_uint32),
        ('mmio_start', ctypes.c_ulong),
        ('mmio_len', ctypes.c_uint32),
        ('accel', ctypes.c_uint32),
        ('capabilities', ctypes.c_uint16),
        ('reserved', ctypes.c_uint16 * 2),
    ]

class VarScreenInfo(ctypes.Structure):
    _fields_ = [
        ('xres', ctypes.c_uint32),
        ('yres', ctypes.c_uint32),
        ('xres_virtual', ctypes.c_uint32),
        ('yres_virtual', ctypes.c_uint32),
        ('xoffset', ctypes.c_uint32),
        ('yoffset', ctypes.c_uint32),
        ('bits_per_pixel', ctypes.c_uint32),
        ('grayscale', ctypes.c_uint32),
        ('red', ctypes.c_uint32 * 3),
        ('green', ctypes.c_uint32 * 3),
        ('blue', ctypes.c_uint32 * 3),
        ('transp', ctypes.c_uint32 * 3),
    ]

def get_fix_info(fb_file):
    fix_info = FixScreenInfo()
    with open(fb_file, 'r') as f:
        fcntl.ioctl(f.fileno(), FBIOGET_FSCREENINFO, fix_info)
    return fix_info

def get_var_info(fb_file):
    var_info = VarScreenInfo()
    with open(fb_file, 'r') as f:
        fcntl.ioctl(f.fileno(), FBIOGET_VSCREENINFO, var_info)
    return var_info

def animate_image(image_path, fb_file='/dev/fb0', duration=30, fps=30):
    try:
        # Get screen info
        var_info = get_var_info(fb_file)
        fix_info = get_fix_info(fb_file)
        
        # Open and resize the image
        with Image.open(image_path) as img:
            img_width, img_height = img.size
            scale_factor = min(var_info.xres / img_width * 0.5, var_info.yres / img_height * 0.5)
            new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
            img_resized = img.resize(new_size, Image.LANCZOS)
        
        # Create a blank canvas for animation
        canvas = Image.new('RGB', (var_info.xres, var_info.yres), color='black')
        
        # Animation parameters
        center_x, center_y = var_info.xres // 2, var_info.yres // 2
        radius = min(var_info.xres, var_info.yres) * 0.25
        angular_speed = 2 * math.pi / 5  # Complete a circle in 5 seconds
        
        start_time = time.time()
        while time.time() - start_time < duration:
            t = time.time() - start_time
            angle = t * angular_speed
            
            x = int(center_x + radius * math.cos(angle) - new_size[0] / 2)
            y = int(center_y + radius * math.sin(angle) - new_size[1] / 2)
            
            # Create a new frame
            frame = canvas.copy()
            frame.paste(img_resized, (x, y))
            
            # Convert frame to numpy array
            frame_array = np.array(frame)
            
            # Determine the correct pixel format
            if var_info.bits_per_pixel == 32:
                if var_info.blue[2] == 0:
                    frame_array = frame_array[:, :, ::-1]  # Convert RGB to BGR
                frame_array = np.insert(frame_array, 3, 255, axis=2)  # Add alpha channel
            elif var_info.bits_per_pixel == 16:
                # Convert to RGB565
                r = (frame_array[:,:,0] >> 3).astype(np.uint16) << 11
                g = (frame_array[:,:,1] >> 2).astype(np.uint16) << 5
                b = (frame_array[:,:,2] >> 3).astype(np.uint16)
                frame_array = r | g | b
            
            # Flatten the array and convert to bytes
            frame_bytes = frame_array.flatten().tobytes()
            
            # Write to framebuffer
            with open(fb_file, 'wb') as f:
                f.write(frame_bytes)
            
            time.sleep(1/fps)
        
        print(f"Animation completed after {duration} seconds")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "FOGAO.jpg")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file 'FOGAO.jpg' not found in the script directory.")
        exit(1)
    
    animate_image(image_path)
    print("Animation finished. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nExiting...")
