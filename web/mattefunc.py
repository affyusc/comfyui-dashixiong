import torch
import numpy as np
import cv2
from PIL import Image
from .guidedfilter import GuidedFilter

try:
    from transformers import VitMatteForImageMatting
except ImportError:
    print("请安装 transformers: pip install transformers")
    VitMatteForImageMatting = None

try:
    import pymatting
except ImportError:
    print("请安装 pymatting: pip install pymatting")
    pymatting = None

def guided_filter_alpha(img, alpha, r):
    """使用引导滤波处理 alpha 通道"""
    gf = GuidedFilter(r, 1e-4)
    return gf.filter(img, alpha)

def mask_edge_detail(img, mask, r, black_point=0.15, white_point=0.99):
    """使用 PyMatting 处理边缘细节"""
    if pymatting is None:
        print("未安装 pymatting，跳过细节处理")
        return mask
    trimap = generate_trimap(mask, r)
    alpha = pymatting.estimate_alpha_cf(img, trimap)
    return histogram_remap(alpha, black_point, white_point)

def histogram_remap(mask, black_point=0.15, white_point=0.99):
    """重映射直方图"""
    mask = (mask - black_point) / (white_point - black_point)
    mask = torch.clamp(mask, 0, 1)
    return mask

def generate_trimap(mask, r):
    """生成三值图"""
    mask_np = mask.numpy() if isinstance(mask, torch.Tensor) else mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (r, r))
    eroded = cv2.erode(mask_np, kernel)
    dilated = cv2.dilate(mask_np, kernel)
    trimap = np.full(mask_np.shape, 0.5)
    trimap[eroded >= 0.99] = 1
    trimap[dilated <= 0.01] = 0
    return trimap

def generate_VITMatte_trimap(mask, erode, dilate):
    """生成 VITMatte 的三值图"""
    # 确保 mask 是正确的 2D numpy 数组
    if isinstance(mask, torch.Tensor):
        mask_np = mask.squeeze().cpu().numpy()  # 移除多余的维度
    else:
        mask_np = mask
    
    # 确保是 2D 数组
    if mask_np.ndim > 2:
        mask_np = mask_np.squeeze()
    
    # 确保数值范围在 0-1 之间
    if mask_np.max() > 1:
        mask_np = mask_np / 255.0
        
    # 创建结构元素
    kernel_e = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (erode, erode))
    kernel_d = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate))
    
    # 转换为 uint8 类型进行腐蚀和膨胀
    mask_uint8 = (mask_np * 255).astype(np.uint8)
    eroded = cv2.erode(mask_uint8, kernel_e)
    dilated = cv2.dilate(mask_uint8, kernel_d)
    
    # 创建 trimap
    trimap = np.full(mask_np.shape, 128, dtype=np.uint8)
    trimap[eroded >= 250] = 255  # 前景
    trimap[dilated <= 5] = 0     # 背景
    
    return trimap

def preprocess_vitmatte(image, trimap):
    """预处理图像和 trimap 用于 VitMatte"""
    # 确保图像是 PIL.Image
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)
    if not isinstance(trimap, Image.Image):
        trimap = Image.fromarray(trimap)
    
    # 调整大小到 1024x1024
    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    trimap = trimap.resize((1024, 1024), Image.Resampling.NEAREST)
    
    # 转换为 numpy 数组
    image = np.array(image)
    trimap = np.array(trimap)
    
    # 归一化
    image = image.astype(np.float32) / 255.0
    trimap = trimap.astype(np.float32) / 255.0
    
    # 转换为 torch tensor
    image = torch.from_numpy(image).permute(2, 0, 1).unsqueeze(0)
    trimap = torch.from_numpy(trimap).unsqueeze(0).unsqueeze(0)
    
    return {
        "pixel_values": image,
        "trimap": trimap
    }

def generate_VITMatte(image, trimap, local_files_only=False, device='cuda'):
    """使用 VITMatte 生成 alpha 遮罩"""
    if VitMatteForImageMatting is None:
        print("未安装 transformers，跳过 VITMatte")
        return trimap
        
    try:
        model = VitMatteForImageMatting.from_pretrained(
            "hustvl/vitmatte-small-composition-1k",
            local_files_only=local_files_only
        ).to(device)
        
        # 预处理输入
        inputs = preprocess_vitmatte(image, trimap)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # 推理
        with torch.no_grad():
            outputs = model(**inputs)
            alpha = outputs.pred_alpha if hasattr(outputs, 'pred_alpha') else outputs.logits
        
        # 后处理
        alpha = alpha.squeeze().cpu()
        
        # 调整回原始大小
        if isinstance(image, Image.Image):
            orig_size = image.size[::-1]  # PIL.Image.size 返回 (width, height)
        else:
            orig_size = image.shape[:2]  # numpy array shape 是 (height, width)
            
        alpha = torch.nn.functional.interpolate(
            alpha.unsqueeze(0).unsqueeze(0),
            size=orig_size,
            mode='bilinear',
            align_corners=False
        ).squeeze()
        
        return alpha
        
    except Exception as e:
        print(f"VITMatte 处理出错: {e}")
        import traceback
        traceback.print_exc()
        return torch.from_numpy(trimap).float()