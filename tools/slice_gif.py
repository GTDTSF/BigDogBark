import os
import sys

try:
    from PIL import Image
except ImportError:
    print("Please install Pillow: uv run --with pillow python tools/slice_gif.py")
    sys.exit(1)

def slice_gif(gif_path, output_dir):
    if not os.path.exists(gif_path):
        print(f"Error: {gif_path} not found.")
        sys.exit(1)
        
    os.makedirs(output_dir, exist_ok=True)
    
    with Image.open(gif_path) as im:
        count = 0
        try:
            while True:
                im.seek(count)
                # Convert to RGBA to preserve transparency
                frame = im.convert("RGBA")
                out_path = os.path.join(output_dir, f"frame_{count:03d}.png")
                frame.save(out_path)
                count += 1
        except EOFError:
            pass # End of sequence
    print(f"Successfully extracted {count} frames to {output_dir}")

if __name__ == "__main__":
    # Get paths relative to project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gif_file = os.path.join(root_dir, "assets", "bark.gif")
    out_dir = os.path.join(root_dir, "assets", "bark_frames")
    
    print(f"Slicing GIF: {gif_file}")
    slice_gif(gif_file, out_dir)
