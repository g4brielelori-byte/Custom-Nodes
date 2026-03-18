"""
ComfyUI Preprocessor Contact Sheet  v2
========================================
Smart contact sheet node with:
- Detects installed preprocessors BEFORE running
- Runs only available ones
- Single image output (clean, only successes)
- STRING output with detailed report
- Button to inject a Base workflow for any preprocessor (list picker)
- Button to open VISUAL grid picker (clickable thumbnails → injects workflow)
"""

import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import traceback
import sys
import os
import json
import io
import base64

try:
    import server
    from aiohttp import web
    HAS_SERVER = True
except Exception:
    HAS_SERVER = False


# ---------------------------------------------------------------------------
#  Registry
# ---------------------------------------------------------------------------

PREPROCESSOR_REGISTRY = [
    {"name": "AnimeFace SemSeg",     "aio": "AnimeFace_SemSegPreprocessor",         "node": "AnimeFace_SemSegPreprocessor",         "cat": "segment"},
    {"name": "OneFormer COCO",       "aio": "OneFormer-COCO-SemSegPreprocessor",    "node": "OneFormer-COCO-SemSegPreprocessor",    "cat": "segment"},
    {"name": "OneFormer ADE20K",     "aio": "OneFormer-ADE20K-SemSegPreprocessor",  "node": "OneFormer-ADE20K-SemSegPreprocessor",  "cat": "segment"},
    {"name": "UniFormer SemSeg",     "aio": "UniFormer-SemSegPreprocessor",         "node": "UniFormer-SemSegPreprocessor",         "cat": "segment"},
    {"name": "SemSeg",               "aio": "SemSegPreprocessor",                   "node": "SemSegPreprocessor",                   "cat": "segment"},
    {"name": "SAM",                  "aio": "SAMPreprocessor",                      "node": "SAMPreprocessor",                      "cat": "segment"},
    {"name": "Canny",                "aio": "CannyEdgePreprocessor",                "node": "CannyEdgePreprocessor",                "cat": "edge"},
    {"name": "PyraCanny",            "aio": "PyraCannyPreprocessor",                "node": "PyraCannyPreprocessor",                "cat": "edge"},
    {"name": "Binary",               "aio": "BinaryPreprocessor",                   "node": "BinaryPreprocessor",                   "cat": "edge"},
    {"name": "HED",                  "aio": "HEDPreprocessor",                      "node": "HEDPreprocessor",                      "cat": "edge"},
    {"name": "PiDiNet",              "aio": "PiDiNetPreprocessor",                  "node": "PiDiNetPreprocessor",                  "cat": "edge"},
    {"name": "Scribble",             "aio": "ScribblePreprocessor",                 "node": "ScribblePreprocessor",                 "cat": "edge"},
    {"name": "Scribble XDoG",        "aio": "Scribble_XDoG_Preprocessor",           "node": "Scribble_XDoG_Preprocessor",           "cat": "edge"},
    {"name": "Scribble PiDiNet",     "aio": "Scribble_PiDiNet_Preprocessor",        "node": "Scribble_PiDiNet_Preprocessor",        "cat": "edge"},
    {"name": "FakeScribble",         "aio": "FakeScribblePreprocessor",              "node": "FakeScribblePreprocessor",              "cat": "edge"},
    {"name": "TEED",                 "aio": "TEEDPreprocessor",                     "node": "TEEDPreprocessor",                     "cat": "edge"},
    {"name": "M-LSD",                "aio": "M-LSDPreprocessor",                    "node": "M-LSDPreprocessor",                    "cat": "edge"},
    {"name": "DiffusionEdge",        "aio": "DiffusionEdge_Preprocessor",           "node": "DiffusionEdge_Preprocessor",           "cat": "edge",
     "note": "Not AIO-compatible — requires scikit-learn, use its dedicated node"},
    {"name": "AnyLineArt",           "aio": "AnyLineArtPreprocessor_aux",           "node": "AnyLineArtPreprocessor_aux",           "cat": "lineart"},
    {"name": "LineArt Realistic",    "aio": "LineArtPreprocessor",                  "node": "LineArtPreprocessor",                  "cat": "lineart"},
    {"name": "LineArt Anime",        "aio": "AnimeLineArtPreprocessor",             "node": "AnimeLineArtPreprocessor",             "cat": "lineart"},
    {"name": "LineArt Standard",     "aio": "LineartStandardPreprocessor",          "node": "LineartStandardPreprocessor",          "cat": "lineart"},
    {"name": "Manga2Anime LineArt",  "aio": "Manga2Anime_LineArt_Preprocessor",    "node": "Manga2Anime_LineArt_Preprocessor",    "cat": "lineart"},
    {"name": "DWPose",               "aio": "DWPreprocessor",                       "node": "DWPreprocessor",                       "cat": "pose"},
    {"name": "OpenPose",             "aio": "OpenposePreprocessor",                 "node": "OpenposePreprocessor",                 "cat": "pose"},
    {"name": "Animal Pose",          "aio": "AnimalPosePreprocessor",               "node": "AnimalPosePreprocessor",               "cat": "pose"},
    {"name": "DensePose",            "aio": "DensePosePreprocessor",                "node": "DensePosePreprocessor",                "cat": "pose"},
    {"name": "DepthAnything",        "aio": "DepthAnythingPreprocessor",            "node": "DepthAnythingPreprocessor",            "cat": "depth"},
    {"name": "DepthAnything V2",     "aio": "DepthAnythingV2Preprocessor",          "node": "DepthAnythingV2Preprocessor",          "cat": "depth"},
    {"name": "Zoe DepthAnything",    "aio": "Zoe_DepthAnythingPreprocessor",        "node": "Zoe_DepthAnythingPreprocessor",        "cat": "depth"},
    {"name": "Zoe Depth",            "aio": "Zoe-DepthMapPreprocessor",             "node": "Zoe-DepthMapPreprocessor",             "cat": "depth"},
    {"name": "MiDaS Depth",          "aio": "MiDaS-DepthMapPreprocessor",           "node": "MiDaS-DepthMapPreprocessor",           "cat": "depth"},
    {"name": "LeReS Depth",          "aio": "LeReS-DepthMapPreprocessor",           "node": "LeReS-DepthMapPreprocessor",           "cat": "depth"},
    {"name": "Metric3D Depth",       "aio": "Metric3D-DepthMapPreprocessor",        "node": "Metric3D-DepthMapPreprocessor",        "cat": "depth"},
    {"name": "MeshGraphormer Depth", "aio": "MeshGraphormer-DepthMapPreprocessor",  "node": "MeshGraphormer-DepthMapPreprocessor",  "cat": "depth"},
    {"name": "DSINE Normal",         "aio": "DSINE-NormalMapPreprocessor",          "node": "DSINE-NormalMapPreprocessor",          "cat": "normal"},
    {"name": "MiDaS Normal",         "aio": "MiDaS-NormalMapPreprocessor",          "node": "MiDaS-NormalMapPreprocessor",          "cat": "normal"},
    {"name": "BAE Normal",           "aio": "BAE-NormalMapPreprocessor",            "node": "BAE-NormalMapPreprocessor",            "cat": "normal"},
    {"name": "Metric3D Normal",      "aio": "Metric3D-NormalMapPreprocessor",       "node": "Metric3D-NormalMapPreprocessor",       "cat": "normal"},
    {"name": "MediaPipe FaceMesh",   "aio": "MediaPipe-FaceMeshPreprocessor",       "node": "MediaPipe-FaceMeshPreprocessor",       "cat": "face"},
    {"name": "Color",                "aio": "ColorPreprocessor",                    "node": "ColorPreprocessor",                    "cat": "color"},
    {"name": "Luminance",            "aio": "ImageLuminanceDetector",               "node": "ImageLuminanceDetector",               "cat": "color"},
    {"name": "Intensity",            "aio": "ImageIntensityDetector",               "node": "ImageIntensityDetector",               "cat": "color"},
    {"name": "Tile",                 "aio": "TilePreprocessor",                     "node": "TilePreprocessor",                     "cat": "tile"},
    {"name": "TTTile GF",            "aio": "TTPlanet_TileGF_Preprocessor",         "node": "TTPlanet_TileGF_Preprocessor",         "cat": "tile"},
    {"name": "TTTile Simple",        "aio": "TTPlanet_TileSimple_Preprocessor",     "node": "TTPlanet_TileSimple_Preprocessor",     "cat": "tile"},
    {"name": "Shuffle",              "aio": "ShufflePreprocessor",                  "node": "ShufflePreprocessor",                  "cat": "tile"},
    {"name": "Unimatch OptFlow",     "aio": "Unimatch_OptFlowPreprocessor",         "node": "Unimatch_OptFlowPreprocessor",         "cat": "flow",
     "note": "Not AIO-compatible — needs 2 frames, use its dedicated node"},
]

CATEGORY_COLORS = {
    "segment": (90, 50, 120), "edge": (45, 65, 120), "lineart": (55, 85, 140),
    "pose": (120, 45, 45), "depth": (45, 110, 55), "normal": (120, 100, 30),
    "face": (130, 70, 100), "color": (100, 80, 50), "tile": (70, 70, 70),
    "flow": (50, 90, 100),
}
CATEGORY_LABELS = {
    "segment": "SEGMENT", "edge": "EDGE", "lineart": "LINEART", "pose": "POSE",
    "depth": "DEPTH", "normal": "NORMAL", "face": "FACE", "color": "COLOR",
    "tile": "TILE/SHUFFLE", "flow": "OPTICAL FLOW",
}


# ---------------------------------------------------------------------------
#  Thumbnail cache: stores base64 thumbs from last run per node_id
# ---------------------------------------------------------------------------

_thumb_cache = {}
# { node_id_str: [ { "name", "aio", "cat", "thumb" (b64 jpeg) }, ... ] }


def _tensor_to_thumb_b64(tensor, width=220):
    """Convert a ComfyUI image tensor to a small base64 JPEG thumbnail."""
    x = tensor[0] if len(tensor.shape) == 4 else tensor
    pil = Image.fromarray(
        (x.cpu().numpy() * 255).clip(0, 255).astype(np.uint8), "RGB")
    ratio = width / pil.width
    h = int(pil.height * ratio)
    pil = pil.resize((width, h), Image.LANCZOS)
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
#  Base workflow template
# ---------------------------------------------------------------------------

def make_base_workflow(preprocessor_name, display_name):
    """AIO-based workflow: LoadImage → Scale → AIO_Preprocessor → Preview."""
    return {
        "nodes": [
            {
                "id": 1, "type": "LoadImage",
                "pos": [0, 0], "size": [315, 314],
                "inputs": [], "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [1]},
                    {"name": "MASK", "type": "MASK", "links": []},
                ],
                "widgets_values": ["example.png", "image"],
                "properties": {"Node name for S&R": "LoadImage"},
            },
            {
                "id": 2, "type": "ImageScaleToTotalPixels",
                "pos": [400, 60], "size": [315, 106],
                "inputs": [{"name": "image", "type": "IMAGE", "link": 1}],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [2]}],
                "widgets_values": ["nearest-exact", 1, 1],
                "properties": {"Node name for S&R": "ImageScaleToTotalPixels"},
            },
            {
                "id": 3, "type": "AIO_Preprocessor",
                "pos": [800, 40], "size": [340, 150],
                "inputs": [
                    {"name": "image", "type": "IMAGE", "link": 2},
                    {"name": "preprocessor", "type": "COMBO", "shape": 7,
                     "widget": {"name": "preprocessor"}},
                    {"name": "resolution", "type": "INT", "shape": 7,
                     "widget": {"name": "resolution"}},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [3]}],
                "widgets_values": [preprocessor_name, 1024],
                "properties": {
                    "cnr_id": "comfyui_controlnet_aux",
                    "Node name for S&R": "AIO_Preprocessor",
                },
            },
            {
                "id": 4, "type": "PreviewImage",
                "pos": [1240, 0], "size": [400, 400],
                "inputs": [{"name": "images", "type": "IMAGE", "link": 3}],
                "outputs": [],
                "properties": {"Node name for S&R": "PreviewImage"},
            },
        ],
        "links": [
            [1, 1, 0, 2, 0, "IMAGE"],
            [2, 2, 0, 3, 0, "IMAGE"],
            [3, 3, 0, 4, 0, "IMAGE"],
        ],
        "groups": [{
            "title": f"\U0001F4E6 AIO: {display_name} ({preprocessor_name})",
            "bounding": [-40, -60, 1700, 440],
            "color": "#3f5e9e",
            "font_size": 24,
        }],
    }


def make_dedicated_workflow(node_type, display_name):
    """Dedicated node workflow: LoadImage → Scale → Dedicated Node → Preview."""
    return {
        "nodes": [
            {
                "id": 1, "type": "LoadImage",
                "pos": [0, 0], "size": [315, 314],
                "inputs": [], "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [1]},
                    {"name": "MASK", "type": "MASK", "links": []},
                ],
                "widgets_values": ["example.png", "image"],
                "properties": {"Node name for S&R": "LoadImage"},
            },
            {
                "id": 2, "type": "ImageScaleToTotalPixels",
                "pos": [400, 60], "size": [315, 106],
                "inputs": [{"name": "image", "type": "IMAGE", "link": 1}],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [2]}],
                "widgets_values": ["nearest-exact", 1, 1],
                "properties": {"Node name for S&R": "ImageScaleToTotalPixels"},
            },
            {
                "id": 3, "type": node_type,
                "pos": [800, 40], "size": [380, 200],
                "inputs": [
                    {"name": "image", "type": "IMAGE", "link": 2},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [3]}],
                "properties": {
                    "cnr_id": "comfyui_controlnet_aux",
                    "Node name for S&R": node_type,
                },
            },
            {
                "id": 4, "type": "PreviewImage",
                "pos": [1280, 0], "size": [400, 400],
                "inputs": [{"name": "images", "type": "IMAGE", "link": 3}],
                "outputs": [],
                "properties": {"Node name for S&R": "PreviewImage"},
            },
        ],
        "links": [
            [1, 1, 0, 2, 0, "IMAGE"],
            [2, 2, 0, 3, 0, "IMAGE"],
            [3, 3, 0, 4, 0, "IMAGE"],
        ],
        "groups": [{
            "title": f"\U0001F3AF Dedicated: {display_name} ({node_type})",
            "bounding": [-40, -60, 1740, 440],
            "color": "#7c3f9e",
            "font_size": 24,
        }],
    }


# ---------------------------------------------------------------------------
#  API routes
# ---------------------------------------------------------------------------

if HAS_SERVER:
    @server.PromptServer.instance.routes.get("/contact_sheet/workflow")
    async def api_get_workflow(request):
        prep = request.query.get("preprocessor", "")
        mode = request.query.get("mode", "aio")
        entry = next((e for e in PREPROCESSOR_REGISTRY if e["aio"] == prep), None)
        display = entry["name"] if entry else prep

        if mode == "dedicated" and entry:
            node_type = entry.get("node", prep)
            wf = make_dedicated_workflow(node_type, display)
        else:
            wf = make_base_workflow(prep, display)
        return web.json_response(wf)

    @server.PromptServer.instance.routes.get("/contact_sheet/cells")
    async def api_get_cells(request):
        """Returns cached thumbnails from the last run for the visual grid picker."""
        node_id = str(request.query.get("node_id", ""))
        if node_id not in _thumb_cache:
            return web.json_response({"cells": []})
        return web.json_response({"cells": _thumb_cache[node_id]})


# ---------------------------------------------------------------------------
#  Discovery
# ---------------------------------------------------------------------------

def find_aio_class():
    try:
        import nodes
        cls = getattr(nodes, "NODE_CLASS_MAPPINGS", {}).get("AIO_Preprocessor")
        if cls: return cls
    except Exception:
        pass
    for mn, m in list(sys.modules.items()):
        if m is None: continue
        try:
            if "controlnet_aux" in mn.lower():
                cls = getattr(m, "NODE_CLASS_MAPPINGS", {}).get("AIO_Preprocessor")
                if cls: return cls
                cls = getattr(m, "AIO_Preprocessor", None)
                if cls: return cls
        except Exception:
            continue
    try:
        td = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(os.path.dirname(td)):
            fl = f.lower().replace("-", "_")
            if "controlnet" in fl and "aux" in fl:
                for sub in ["node_wrappers.AIO", "nodes.AIO"]:
                    try:
                        import importlib
                        cls = getattr(importlib.import_module(f"{f}.{sub}"),
                                      "AIO_Preprocessor", None)
                        if cls: return cls
                    except Exception:
                        pass
    except Exception:
        pass
    return None


def get_available_preprocessors():
    available, not_supported, aux_mappings = set(), set(), {}
    init_mod = None
    for mn, m in list(sys.modules.items()):
        if m is None: continue
        if mn.lower().endswith("comfyui_controlnet_aux") or (
            "controlnet_aux" in mn.lower() and mn.endswith("__init__")):
            init_mod = m
            break
    if init_mod is None:
        for p in ["custom_nodes.comfyui_controlnet_aux", "comfyui_controlnet_aux"]:
            try:
                import importlib
                init_mod = importlib.import_module(p)
                break
            except Exception:
                pass
    if init_mod:
        fn = getattr(init_mod, "preprocessor_options", None)
        if fn:
            try:
                available = set(fn()) - {"none"}
            except Exception:
                pass
        not_supported = set(getattr(init_mod, "AIO_NOT_SUPPORTED", []))
        aux_mappings = getattr(init_mod, "AUX_NODE_MAPPINGS", {})
    return available, not_supported, aux_mappings


def run_preprocessor(aio_class, image, name, res):
    try:
        r = aio_class().execute(name, image, resolution=res)
        if r and len(r) > 0 and isinstance(r[0], torch.Tensor):
            return r[0], None
        return None, "Returned empty or invalid result"
    except Exception as e:
        tb = traceback.format_exc()
        short = str(e)
        return None, f"{short}\n{tb}"


# ---------------------------------------------------------------------------
#  The Node
# ---------------------------------------------------------------------------

class PreprocessorContactSheet:

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "image": ("IMAGE",),
            "resolution": ("INT", {
                "default": 1024, "min": 256, "max": 2048, "step": 64,
                "tooltip": "Resolution passed to each preprocessor",
            }),
            "columns": ("INT", {
                "default": 5, "min": 1, "max": 12, "step": 1,
            }),
            "cell_width": ("INT", {
                "default": 384, "min": 128, "max": 1024, "step": 64,
                "tooltip": "Cell width — height auto from aspect ratio",
            }),
            "border": ("INT", {
                "default": 4, "min": 0, "max": 20, "step": 1,
            }),
            "font_size": ("INT", {
                "default": 16, "min": 8, "max": 48, "step": 1,
            }),
            "show_labels": ("BOOLEAN", {
                "default": True,
                "tooltip": "Show/hide name + category + resolution labels",
            }),
            "show_original": ("BOOLEAN", {
                "default": True,
                "tooltip": "Include original image as first cell",
            }),
            "title": ("STRING", {
                "default": "Preprocessor Contact Sheet",
                "multiline": False,
            }),
            "skip_preprocessors": ("STRING", {
                "default": "", "multiline": True,
                "placeholder": "Comma-separated AIO names to skip",
            }),
        },
        "hidden": {
            "unique_id": "UNIQUE_ID",
        }}

    RETURN_TYPES = ("IMAGE", "STRING",)
    RETURN_NAMES = ("contact_sheet", "report",)
    FUNCTION = "execute"
    CATEGORY = "image/analysis"
    DESCRIPTION = (
        "Runs all available preprocessors and builds a contact sheet.\n"
        "Output 1: clean contact sheet (successes only).\n"
        "Output 2: detailed report with errors and missing info.\n"
        "Use \U0001F3AF Pick from Grid to see actual results and inject a workflow."
    )

    # -- Helpers --

    @staticmethod
    def t2p(t):
        x = t[0] if len(t.shape) == 4 else t
        return Image.fromarray(
            (x.cpu().numpy() * 255).clip(0, 255).astype(np.uint8), "RGB")

    @staticmethod
    def p2t(img):
        return torch.from_numpy(
            np.array(img).astype(np.float32) / 255.0).unsqueeze(0)

    @staticmethod
    def get_font(sz):
        for p in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            try:
                return ImageFont.truetype(p, sz)
            except (OSError, IOError):
                continue
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    @staticmethod
    def fit_image(img, tw, th):
        sw, sh = img.size
        sc = min(tw / sw, th / sh)
        nw, nh = int(sw * sc), int(sh * sc)
        r = img.resize((nw, nh), Image.LANCZOS)
        c = Image.new("RGB", (tw, th), (10, 10, 10))
        c.paste(r, ((tw - nw) // 2, (th - nh) // 2))
        return c

    def build_sheet(self, cells, cols, cw, ar, brd, fsz, title,
                    show_labels, res):
        aw, ah = ar
        ch = int(cw * ah / aw) if aw > 0 else cw
        lh = (fsz * 3 + 20) if show_labels else 0
        th = (fsz + 30) if title.strip() else 0
        n = max(len(cells), 1)
        rows = math.ceil(n / cols)
        cfh = ch + lh
        w = cols * cw + (cols + 1) * brd
        h = rows * cfh + (rows + 1) * brd + th

        canvas = Image.new("RGB", (w, h), (18, 18, 18))
        draw = ImageDraw.Draw(canvas)
        font = self.get_font(fsz)
        fsm = self.get_font(max(8, fsz - 2))
        tf = self.get_font(fsz + 8)

        if title.strip() and tf:
            bb = draw.textbbox((0, 0), title, font=tf)
            draw.text(((w - bb[2] + bb[0]) // 2, (th - bb[3] + bb[1]) // 2),
                      title, fill=(220, 220, 220), font=tf)

        for idx, (name, cat, img) in enumerate(cells):
            r, c = idx // cols, idx % cols
            x = brd + c * (cw + brd)
            y = th + brd + r * (cfh + brd)

            if img:
                canvas.paste(self.fit_image(img, cw, ch), (x, y))

            if show_labels and lh > 0 and font and fsm:
                ly = y + ch
                cc = CATEGORY_COLORS.get(cat, (70, 70, 70))
                draw.rectangle([x, ly, x + cw, ly + lh], fill=cc)

                pad, line = 4, fsz + 2
                b1 = draw.textbbox((0, 0), name, font=font)
                draw.text((x + (cw - b1[2] + b1[0]) // 2, ly + pad),
                          name, fill=(240, 240, 240), font=font)

                cl = CATEGORY_LABELS.get(cat, cat.upper())
                b2 = draw.textbbox((0, 0), cl, font=fsm)
                draw.text((x + (cw - b2[2] + b2[0]) // 2, ly + pad + line),
                          cl, fill=(180, 180, 180), font=fsm)

                rt = f"res: {res}"
                b3 = draw.textbbox((0, 0), rt, font=fsm)
                draw.text((x + (cw - b3[2] + b3[0]) // 2, ly + pad + line * 2),
                          rt, fill=(140, 140, 140), font=fsm)

            draw.rectangle([x - 1, y - 1, x + cw, y + ch + lh],
                           outline=(50, 50, 50), width=1)

        return canvas

    # -- Main --

    def execute(self, image, resolution, columns, cell_width, border,
                font_size, show_labels, show_original, title,
                skip_preprocessors, unique_id=None):

        node_id = str(unique_id) if unique_id else str(id(self))

        skip = set()
        if skip_preprocessors.strip():
            for s in skip_preprocessors.replace("\n", ",").split(","):
                s = s.strip()
                if s:
                    skip.add(s)

        if len(image.shape) == 4:
            img_h, img_w = image.shape[1], image.shape[2]
        else:
            img_h, img_w = image.shape[0], image.shape[1]
        ar = (img_w, img_h)

        aio_class = find_aio_class()
        available, not_supported, aux_mappings = get_available_preprocessors()

        if aio_class is None:
            err = Image.new("RGB", (900, 200), (50, 15, 15))
            d = ImageDraw.Draw(err)
            f = self.get_font(22)
            if f:
                d.text((20, 20), "comfyui_controlnet_aux not found!",
                       fill=(255, 80, 80), font=f)
            return (self.p2t(err),
                    "ERROR: comfyui_controlnet_aux is not installed.\n"
                    "Install via ComfyUI Manager: search 'ControlNet Auxiliary Preprocessors'")

        report_lines = [
            f"=== PREPROCESSOR CONTACT SHEET REPORT ===",
            f"Image: {img_w}x{img_h} | Resolution: {resolution}",
            "",
        ]

        to_run = []
        not_aio_section = []
        skipped_section = []

        for e in PREPROCESSOR_REGISTRY:
            aio = e["aio"]
            name = e["name"]
            if aio in skip or name in skip:
                skipped_section.append(f"  {name} ({aio})")
                continue
            if aio in available:
                to_run.append(e)
            elif aio in not_supported or aio in aux_mappings:
                note = e.get("note", "Use its dedicated node instead of AIO")
                not_aio_section.append(f"  {name} ({aio})\n    -> {note}")
            else:
                not_aio_section.append(
                    f"  {name} ({aio})\n"
                    f"    -> Node not loaded / missing dependency")

        print(f"[ContactSheet] Will run: {len(to_run)} preprocessors")

        cells = []          # (name, cat, PIL) for the sheet
        thumb_list = []      # for the visual picker cache
        error_section = []

        if show_original:
            cells.append(("ORIGINAL", "color", self.t2p(image)))
            thumb_list.append({
                "name": "ORIGINAL", "aio": "__original__", "cat": "color",
                "thumb": _tensor_to_thumb_b64(image),
            })

        total = len(to_run)
        for i, e in enumerate(to_run):
            aio_name = e["aio"]
            display = e["name"]
            cat = e["cat"]

            print(f"[ContactSheet] [{i + 1}/{total}] {display}...")
            out_tensor, err_msg = run_preprocessor(
                aio_class, image, aio_name, resolution)

            if out_tensor is not None:
                cells.append((display, cat, self.t2p(out_tensor)))
                thumb_list.append({
                    "name": display, "aio": aio_name, "cat": cat,
                    "node": e.get("node", aio_name),
                    "thumb": _tensor_to_thumb_b64(out_tensor),
                })
            else:
                error_section.append(
                    f"  {display} ({aio_name})\n    -> {err_msg}")
                print(f"[ContactSheet]   FAILED: {err_msg.split(chr(10))[0]}")

        # Cache thumbnails for the visual picker
        _thumb_cache[node_id] = thumb_list

        # Report
        ok_count = len(cells) - (1 if show_original else 0)
        report_lines.append(f"EXECUTED: {ok_count} / {total} succeeded")
        report_lines.append("")

        if error_section:
            report_lines.append(f"--- RUNTIME ERRORS ({len(error_section)}) ---")
            report_lines.append("These preprocessors are installed but crashed:")
            report_lines.extend(error_section)
            report_lines.append("")
        if not_aio_section:
            report_lines.append(
                f"--- NOT AVAILABLE VIA AIO ({len(not_aio_section)}) ---")
            report_lines.append(
                "These need their own node or are not installed:")
            report_lines.extend(not_aio_section)
            report_lines.append("")
        if skipped_section:
            report_lines.append(f"--- SKIPPED BY USER ({len(skipped_section)}) ---")
            report_lines.extend(skipped_section)
            report_lines.append("")
        if not error_section and not not_aio_section:
            report_lines.append("All preprocessors available and working!")

        report = "\n".join(report_lines)

        # Build sheet
        if not cells:
            blank = Image.new("RGB", (cell_width, cell_width), (18, 18, 18))
            return (self.p2t(blank), report)

        sheet = self.build_sheet(
            cells, columns, cell_width, ar, border,
            font_size, title, show_labels, resolution)

        print(f"[ContactSheet] Done: {sheet.size[0]}x{sheet.size[1]}")
        return (self.p2t(sheet), report)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "PreprocessorContactSheet": PreprocessorContactSheet,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PreprocessorContactSheet": "Preprocessor Contact Sheet",
}
WEB_DIRECTORY = "./js"
