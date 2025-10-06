#!/usr/bin/env python3
"""
Script to generate tray icon variants for different states
"""

from PIL import Image, ImageDraw
import os

def create_base_icon():
    """Create a simple base icon"""
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple AI assistant icon (circle with "AI" text)
    draw.ellipse([4, 4, size-4, size-4], fill=(59, 130, 246), outline=(37, 99, 235), width=2)
    
    # Add "AI" text (simplified)
    draw.text((10, 8), "AI", fill=(255, 255, 255))
    
    return img

def create_listening_icon():
    """Create listening state icon with microphone indicator"""
    img = create_base_icon()
    draw = ImageDraw.Draw(img)
    
    # Add microphone indicator (small circle in corner)
    draw.ellipse([20, 20, 28, 28], fill=(34, 197, 94), outline=(22, 163, 74), width=1)
    
    return img

def create_processing_icon():
    """Create processing state icon with animated indicator"""
    img = create_base_icon()
    draw = ImageDraw.Draw(img)
    
    # Add processing indicator (small orange circle)
    draw.ellipse([20, 20, 28, 28], fill=(249, 115, 22), outline=(234, 88, 12), width=1)
    
    return img

def create_error_icon():
    """Create error state icon"""
    img = create_base_icon()
    draw = ImageDraw.Draw(img)
    
    # Change base color to red
    draw.ellipse([4, 4, 28, 28], fill=(239, 68, 68), outline=(220, 38, 38), width=2)
    
    # Add error indicator (exclamation mark)
    draw.text((10, 8), "!", fill=(255, 255, 255))
    
    return img

def create_offline_icon():
    """Create offline state icon (grayed out)"""
    img = create_base_icon()
    draw = ImageDraw.Draw(img)
    
    # Change base color to gray
    draw.ellipse([4, 4, 28, 28], fill=(107, 114, 128), outline=(75, 85, 99), width=2)
    
    return img

def main():
    """Generate all tray icon variants"""
    icons = {
        'tray-icon': create_base_icon(),
        'tray-icon-listening': create_listening_icon(),
        'tray-icon-processing': create_processing_icon(),
        'tray-icon-error': create_error_icon(),
        'tray-icon-offline': create_offline_icon()
    }
    
    # Create icons in different formats for different platforms
    for name, img in icons.items():
        # PNG for Linux
        img.save(f'{name}.png')
        
        # ICO for Windows (multiple sizes)
        img.resize((16, 16), Image.Resampling.LANCZOS).save(f'{name}.ico')
        
        # Template PNG for macOS (will be converted to ICNS)
        if 'Template' not in name:
            template_img = img.copy()
            # Make it template-style (black and white with alpha)
            pixels = template_img.load()
            for i in range(template_img.size[0]):
                for j in range(template_img.size[1]):
                    r, g, b, a = pixels[i, j]
                    if a > 0:  # If not transparent
                        # Convert to grayscale and make it template-style
                        gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                        pixels[i, j] = (0, 0, 0, a)  # Black with original alpha
            template_img.save(f'{name}Template.png')
    
    print("Generated tray icon variants:")
    for name in icons.keys():
        print(f"  - {name}.png")
        print(f"  - {name}.ico")
        print(f"  - {name}Template.png")

if __name__ == '__main__':
    main()