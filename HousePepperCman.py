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

def display_six_images(image_paths, fb_file='/dev/fb0', margin_percent=5):
    try:
        if len(image_paths) != 6:
            raise ValueError("Exactly six image paths must be provided.")

        # Get screen info
        var_info = get_var_info(fb_file)
        fix_info = get_fix_info(fb_file)
        
        # Calculate margins
        horizontal_margin = int(var_info.xres * margin_percent / 100)
        vertical_margin = int(var_info.yres * margin_percent / 100)
        
        # Calculate available space for images
        available_width = (var_info.xres - 4 * horizontal_margin) // 3
        available_height = (var_info.yres - 3 * vertical_margin) // 2
        
        # Create a new image for the layout
        layout = Image.new('RGB', (var_info.xres, var_info.yres), color='black')
        
        # Process each image
        for i, image_path in enumerate(image_paths):
            with Image.open(image_path) as img:
                # Calculate scaling factor to fit within available space while maintaining aspect ratio
                scale = min(available_width / img.width, available_height / img.height)
                new_size = (int(img.width * scale), int(img.height * scale))
                
                # Resize the image
                resized_img = img.resize(new_size, Image.LANCZOS)
                
                # Calculate position to center the image in its cell
                x_offset = horizontal_margin + (i % 3) * (available_width + horizontal_margin)
                y_offset = vertical_margin + (i // 3) * (available_height + vertical_margin)
                x_offset += (available_width - new_size[0]) // 2
                y_offset += (available_height - new_size[1]) // 2
                
                # Paste the resized image onto the layout
                layout.paste(resized_img, (x_offset, y_offset))
        
        # Convert layout to RGB format if necessary
        if layout.mode != 'RGB':
            layout = layout.convert('RGB')
        
        # Get image data as a numpy array
        image_array = np.array(layout)
        
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

        print(f"Six images displayed in a 2x3 grid on {fb_file}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    encrypted_dir = os.path.join(script_dir, "Encrypted")
    
    # Define the six image paths here
    image_paths = [
        os.path.join(encrypted_dir, "plain_House.jpg"),
        os.path.join(encrypted_dir, "plain_Pepper.jpg"),
        os.path.join(encrypted_dir, "plain_Cman.jpg"),  # Placeholder for the third image in the top row
        os.path.join(encrypted_dir, "House.jpg"),
        os.path.join(encrypted_dir, "Pepper.jpg"),
        os.path.join(encrypted_dir, "Cman.jpg"),
    ]
    
    # Check if all image files exist
    for path in image_paths:
        if not os.path.exists(path):
            print(f"Error: Image file '{path}' not found.")
            exit(1)
    
    display_six_images(image_paths)
    print("Six images displayed in a 2x3 grid on HDMI monitor. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        while True:
            pass
    except KeyboardInterrupt:
        print("\nExiting...")
