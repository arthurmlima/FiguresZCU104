import os
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

def display_dual_images(image_path, fb_file='/dev/fb0'):
    try:
        # Get screen info
        var_info = get_var_info(fb_file)
        fix_info = get_fix_info(fb_file)
        
        # Open the image
        image = Image.open(image_path)
        
        # Calculate new dimensions for each image
        new_width = var_info.xres // 2
        new_height = int(new_width * image.height / image.width)
        
        # Resize the image
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # Create a new image with two instances side by side
        combined_image = Image.new('RGB', (var_info.xres, var_info.yres))
        combined_image.paste(resized_image, (0, 0))
        combined_image.paste(resized_image, (new_width, 0))
        
        # Convert image to RGB format if necessary
        if combined_image.mode != 'RGB':
            combined_image = combined_image.convert('RGB')
        
        # Get image data as a numpy array
        image_array = np.array(combined_image)
        
        # Determine the correct pixel format
        if var_info.bits_per_pixel == 32:
            if var_info.blue[2] == 0:
                image_array = image_array[:, :, ::-1]  # Convert RGB to BGR
            image_array = np.insert(image_array, 3, 255, axis=2)  # Add alpha channel
        elif var_info.bits_per_pixel == 16:
            # Convert to RGB565
            r = (image_array[:,:,0] >> 3).astype(np.uint16) << 11
            g = (image_array[:,:,1] >> 2).astype(np.uint16) << 5
            b = (image_array[:,:,2] >> 3).astype(np.uint16)
            image_array = r | g | b
        
        # Flatten the array and convert to bytes
        image_bytes = image_array.flatten().tobytes()
        
        # Write to framebuffer
        with open(fb_file, 'wb') as f:
            f.write(image_bytes)

        print(f"Dual images displayed on {fb_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "FOGAO.jpg")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file 'FOGAO.jpg' not found in the script directory.")
        exit(1)
    
    display_dual_images(image_path)
    print("Dual images displayed on HDMI monitor. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nExiting...")
