# Icons Directory

This directory contains icons for the GUI application.

## Structure

Icons are organized by category:
- `actions/` - Action icons (add, remove, edit, save, etc.)
- `status/` - Status icons (success, error, warning, info)
- `dialogs/` - Dialog icons (question, information, warning, error)
- `wizard/` - Wizard step icons
- `tools/` - Tool icons (git, python, ai)

## Icon Format

Icons should be provided in PNG format with the following sizes:
- 16x16 (small)
- 24x24 (medium)
- 32x32 (large)
- 48x48 (xlarge)

## Fallback

The `default.png` icon in the root icons directory is used as a fallback when a requested icon is not found.

## Themes

Theme-specific icons can be placed in subdirectories:
- `light/` - Light theme icons
- `dark/` - Dark theme icons

The icon loader will first check theme-specific directories before falling back to the default icons.