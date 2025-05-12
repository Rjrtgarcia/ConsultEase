# ConsultEase Resources

This directory contains various resource files used by the ConsultEase application.

## Icons

The `icons` directory contains icons used throughout the application UI. The system supports PNG, SVG and JPG formats, with SVG recommended for best scaling at different resolutions.

### Standard Icons

The application uses a standardized set of icons to maintain UI consistency. Icon names are defined in `utils/icons.py` in the `Icons` class.

### Custom Icons

To add custom icons, simply place them in the `icons` directory with filenames matching the name constants defined in the `Icons` class. For example:

- `available.svg` - Icon for available faculty status
- `unavailable.svg` - Icon for unavailable faculty status
- `settings.svg` - Icon for settings functions
- `faculty.svg` - Icon for faculty entities

### Icon Guidelines

For best results with the touchscreen interface:
- Use simple, recognizable designs
- Maintain a consistent style across all icons
- Create icons at 64x64px minimum for good legibility
- Use SVG format for best scaling
- Ensure good contrast against both light and dark backgrounds

## Stylesheets

The application supports both light and dark themes, defined in `utils/stylesheet.py`. The theme can be switched with the `CONSULTEASE_THEME` environment variable:

```
# For light theme:
export CONSULTEASE_THEME=light

# For dark theme:
export CONSULTEASE_THEME=dark
```

## Adding Resources

When adding new resources:
1. Place files in the appropriate subdirectory
2. Update the relevant utility class if needed
3. Use the proper utility functions to access resources (e.g., `IconProvider.get_icon()`) 