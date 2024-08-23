import os
import sys
import argparse
from PIL import Image
import numpy as np
import fcntl
import ctypes

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

def display_image(image_path, fb_file='/dev/fb0', debug=False):
    try:
        # Get screen info
        var_info = get_var_info(fb_file)
        fix_info = get_fix_info(fb_file)
        
        if debug:
            print(f"Screen resolution: {var_info.xres}x{var_info.yres}")
            print(f"Virtual resolution: {var_info.xres_virtual}x{var_info.yres_virtual}")
            print(f"Bits per pixel: {var_info.bits_per_pixel}")
            print(f"RGB format: {var_info.red[2]}, {var_info.green[2]}, {var_info.blue[2]}")
            print(f"Line length: {fix_info.line_length}")
            print(f"FB memory length: {fix_info.smem_len}")
        
        # Open the image and resize it to fit the screen
        image = Image.open(image_path)
        image = image.resize((var_info.xres, var_info.yres), Image.LANCZOS)
        
        # Convert image to RGB format
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Get image data as a numpy array
        image_array = np.array(image)
        
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

        if debug:
            print(f"Image displayed on {fb_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Display an image on the ZCU104 HDMI monitor.")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--fb", default="/dev/fb0", help="Framebuffer device (default: /dev/fb0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    if not os.path.exists(args.image_path):
        print(f"Error: Image file '{args.image_path}' not found.")
        sys.exit(1)
    
    display_image(args.image_path, args.fb, args.debug)
    print("Image displayed on HDMI monitor. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nExiting...")