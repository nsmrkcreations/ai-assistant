#!/usr/bin/env python3
"""
Script to generate high-resolution application icons
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon(size):
    """Create application icon at specified size"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Create a modern gradient background
    for i in range(size):
        for j in range(size):
            # Distance from center
            center = size // 2
            distance = ((i - center) ** 2 + (j - center) ** 2) ** 0.5
            max_distance = center * 1.4
            
            if distance <= center:
                # Gradient from blue to purple
                ratio = distance / center
                r = int(59 + (147 - 59) * ratio)  # 59 to 147
                g = int(130 + (51 - 130) * ratio)  # 130 to 51
                b = int(246 + (234 - 246) * ratio)  # 246 to 234
                
                img.putpixel((i, j), (r, g, b, 255))
    
    # Add "AI" text in the center
    font_size = max(size // 4, 12)
    try:
        # Try to use a nice font if available
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
    
    text = "AI"
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Draw text with shadow for better visibility
    shadow_offset = max(1, size // 64)
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 128))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    return img

def main():
    """Generate application icons in various sizes"""
    sizes = [16, 24, 32, 48, 64, 128, 256, 512, 1024]
    
    print("Generating application icons...")
    
    for size in sizes:
        icon = create_app_icon(size)
        filename = f"icon-{size}x{size}.png"
        icon.save(filename)
        print(f"  - {filename}")
    
    # Create ICO file with multiple sizes for Windows
    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    ico_images = [create_app_icon(size) for size in ico_sizes]
    ico_images[0].save("icon.ico", format='ICO', sizes=[(size, size) for size in ico_sizes])
    print("  - icon.ico (multi-size)")
    
    # Create ICNS file for macOS (requires pillow-heif or similar)
    try:
        # For ICNS, we need specific sizes
        icns_sizes = [16, 32, 64, 128, 256, 512, 1024]
        icns_images = []
        
        for size in icns_sizes:
            img = create_app_icon(size)
            icns_images.append(img)
            # Also create @2x versions for retina displays
            if size <= 512:
                img_2x = create_app_icon(size * 2)
                icns_images.append(img_2x)
        
        # Save as ICNS (this might require additional libraries)
        # For now, just save the largest as PNG for manual conversion
        create_app_icon(1024).save("icon-1024.png")
        print("  - icon-1024.png (for ICNS conversion)")
        
    except Exception as e:
        print(f"  - ICNS creation failed: {e}")
    
    print("Application icons generated successfully!")

if __name__ == '__main__':
    main()