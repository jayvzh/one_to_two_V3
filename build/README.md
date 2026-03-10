# Build Resources

This directory contains build resources for electron-builder.

## Required Files

### Windows
- `icon.ico` - Windows application icon (256x256 or larger, multi-resolution recommended)

### macOS
- `icon.icns` - macOS application icon (512x512 or larger)

### Linux
- `icon.png` - Linux application icon (512x512)
- `icons/` - Directory containing various size icons for Linux

## Creating Icons

### Method 1: Using electron-icon-builder (Recommended)

```bash
# Install electron-icon-builder
npm install -D electron-icon-builder

# Generate icons from a 1024x1024 PNG
npx electron-icon-builder --input=./build/icon-source.png --output=./build
```

### Method 2: Using electron-icon-maker

```bash
# Install electron-icon-maker
npm install -D electron-icon-maker

# Generate icons
npx electron-icon-maker --input=./build/icon-source.png --output=./build
```

### Method 3: Manual Creation

1. **Windows ICO**: Use tools like:
   - [ConvertICO](https://convertio.co/png-ico/)
   - [ICO Convert](https://icoconvert.com/)
   - GIMP with ICO plugin

2. **macOS ICNS**: Use tools like:
   - `iconutil` (macOS built-in)
   - [Icon Convert](https://cloudconvert.com/png-to-icns)

3. **Linux PNG**: Just a high-resolution PNG (512x512 or 1024x1024)

## Icon Requirements

| Platform | Format | Sizes |
|----------|--------|-------|
| Windows | ICO | 16x16, 24x24, 32x32, 48x48, 64x64, 128x128, 256x256 |
| macOS | ICNS | 16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024 |
| Linux | PNG | 512x512 (or 1024x1024) |

## Current Status

- [ ] `icon.ico` - Windows icon
- [ ] `icon.icns` - macOS icon
- [ ] `icon.png` - Linux icon
- [x] `installer.nsh` - NSIS installer script

## Placeholder Icons

If you don't have icons yet, you can:
1. Use a placeholder icon during development
2. Generate icons from a logo PNG using the tools above
3. Hire a designer to create professional icons

## Notes

- Icons should be square with transparent backgrounds
- Use PNG format for the source image
- Recommended source size: 1024x1024 pixels
- Keep the source PNG for future regeneration
