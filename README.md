# Preprocessor Contact Sheet for ComfyUI

A custom node that runs **all ControlNet preprocessors** on your image at once and displays the results in a single contact sheet grid. Then pick the one you like and inject its workflow directly into your canvas.

## Features

- **Auto-discovery**: detects which preprocessors from `comfyui_controlnet_aux` are installed on your system
- **Batch execution**: runs all available preprocessors in sequence on the same image
- **Contact sheet output**: composites all results into a labeled grid with color-coded categories
- **Visual grid picker** (🎯 Pick from Grid): after running, opens an overlay with real thumbnails — click one to inject its workflow
- **AIO or Dedicated node**: choose between the generic AIO Preprocessor (dropdown) or the dedicated node with full parameter control
- **Click-to-place**: after choosing, click anywhere on the canvas to position the workflow — no overlapping
- **Detailed report**: string output listing successes, failures, missing nodes, and skipped preprocessors

## Requirements

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI's ControlNet Auxiliary Preprocessors](https://github.com/Fannovel16/comfyui_controlnet_aux) (`comfyui_controlnet_aux`)

## Installation

### Via ComfyUI Manager
Search for **Preprocessor Contact Sheet** in the ComfyUI Manager and install.

### Manual
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/ComfyUI-ContactSheet.git
```
Restart ComfyUI.

## Usage

1. Add the **Preprocessor Contact Sheet** node to your workflow
2. Connect an image and press **Queue Prompt**
3. View the contact sheet with all preprocessor results
4. Click **🎯 Pick from Grid** to open the visual picker
5. Click a thumbnail → choose **AIO** or **Dedicated** (or **Both**)
6. Click on the canvas to place the workflow

## Parameters

| Parameter | Description |
|---|---|
| `resolution` | Resolution passed to each preprocessor (512 for SD1.5, 1024 for SDXL) |
| `columns` | Number of columns in the grid |
| `cell_width` | Width of each cell in pixels (height follows aspect ratio) |
| `border` | Spacing between cells |
| `font_size` | Label text size |
| `show_labels` | Show/hide name + category labels |
| `show_original` | Include original image as first cell |
| `title` | Title text at the top of the grid |
| `skip_preprocessors` | Comma-separated list of preprocessor names to skip |

## License

MIT
