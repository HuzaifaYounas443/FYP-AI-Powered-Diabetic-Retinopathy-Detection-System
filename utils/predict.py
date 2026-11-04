"""
Ensemble prediction using EfficientNet-B5 + ResNet101 (+ optional 3rd model).
Falls back to a demo mode if model files are not found.
Applies CLAHE preprocessing to match training preprocessing.
Includes GradCAM for model interpretability.
"""
import os
import re
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import cv2

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

CLASS_NAMES = {
    0: 'No DR',
    1: 'Mild DR',
    2: 'Moderate DR',
    3: 'Severe DR',
    4: 'Proliferative DR'
}

SEVERITY_COLORS = {0: '#22c55e', 1: '#84cc16', 2: '#f59e0b', 3: '#f97316', 4: '#ef4444'}

RECOMMENDATIONS = {
    0: "No signs of diabetic retinopathy detected. Continue regular annual eye examinations and maintain good blood sugar control.",
    1: "Mild non-proliferative diabetic retinopathy detected. Follow-up examination in 12 months recommended. Optimize blood glucose, blood pressure, and lipid control.",
    2: "Moderate non-proliferative diabetic retinopathy detected. Follow-up examination in 6 months recommended. Referral to ophthalmologist advised. Strict metabolic control required.",
    3: "Severe non-proliferative diabetic retinopathy detected. Urgent referral to ophthalmologist required within 1 month. High risk of progression to proliferative DR.",
    4: "Proliferative diabetic retinopathy detected. URGENT referral to retinal specialist required. Treatment (laser photocoagulation or anti-VEGF injections) may be necessary to prevent vision loss."
}

# ─── MODEL DEFINITIONS ─────────────────────────────────────────────────────────

class EfficientNetB5Model(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        from torchvision.models import efficientnet_b5
        self.backbone = efficientnet_b5(weights=None)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)


class ResNet101Model(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        from torchvision.models import resnet101
        self.backbone = resnet101(weights=None)
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(inplace=True),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)


# ─── MODEL LOADING ─────────────────────────────────────────────────────────────

_models = {}

MODEL_PATHS = {
    'efficientnet': os.path.join(os.path.dirname(__file__), '..', 'models', 'EfficientNet-B5_best.pth'),
    'resnet101': os.path.join(os.path.dirname(__file__), '..', 'models', 'ResNet101_best.pth'),
}

def _load_models():
    global _models
    if _models:
        return _models

    def _load_checkpoint(path):
        try:
            return torch.load(path, map_location=DEVICE, weights_only=False)
        except TypeError:
            return torch.load(path, map_location=DEVICE)

    # EfficientNet-B5
    eff_path = os.path.abspath(MODEL_PATHS['efficientnet'])
    if os.path.exists(eff_path):
        try:
            model = EfficientNetB5Model()
            state = _load_checkpoint(eff_path)
            if isinstance(state, dict) and 'model_state_dict' in state:
                state = state['model_state_dict']
            model.load_state_dict(state, strict=False)
            model.to(DEVICE).eval()
            _models['efficientnet'] = model
            print(f"[DR] EfficientNet-B5 loaded from {eff_path}")
        except Exception as e:
            print(f"[DR] Could not load EfficientNet: {e}")

    # ResNet101
    res_path = os.path.abspath(MODEL_PATHS['resnet101'])
    if os.path.exists(res_path):
        try:
            model = ResNet101Model()
            state = _load_checkpoint(res_path)
            if isinstance(state, dict) and 'model_state_dict' in state:
                state = state['model_state_dict']
            model.load_state_dict(state, strict=False)
            model.to(DEVICE).eval()
            _models['resnet101'] = model
            print(f"[DR] ResNet-101 loaded from {res_path}")
        except Exception as e:
            print(f"[DR] Could not load ResNet101: {e}")

    return _models


# ─── TRANSFORMS ────────────────────────────────────────────────────────────────

def apply_clahe(image_array, clip_limit=2.0, tile_grid_size=(8, 8)):
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve contrast.
    Matches the preprocessing used during model training.
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image_array, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE to the L (lightness) channel
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l = clahe.apply(l)
    
    # Merge back and convert to RGB
    lab = cv2.merge([l, a, b])
    rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    
    return rgb

def get_transform(size=256):
    """
    Transform pipeline matching training preprocessing.
    Includes CLAHE, resizing, and ImageNet normalization.
    """
    def clahe_then_to_pil(x):
        """Apply CLAHE and convert back to PIL Image."""
        clahe_result = apply_clahe(np.array(x))
        return Image.fromarray(clahe_result)
    
    return transforms.Compose([
        transforms.Lambda(clahe_then_to_pil),  # Apply CLAHE and convert to PIL
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])


# ─── MAIN PREDICTION ───────────────────────────────────────────────────────────

def predict_image(image_path: str) -> dict:
    img = Image.open(image_path).convert('RGB')
    transform = get_transform(256)
    tensor = transform(img).unsqueeze(0).to(DEVICE)

    models = _load_models()
    all_probs = []
    model_predictions = {}

    if models:
        with torch.no_grad():
            for name, model in models.items():
                out = model(tensor)
                probs = torch.softmax(out, dim=1).cpu().numpy()[0]
                all_probs.append(probs)
                pred_class = int(np.argmax(probs))
                model_predictions[name] = {
                    'label': CLASS_NAMES[pred_class],
                    'level': pred_class,
                    'confidence': float(probs[pred_class]),
                    'probabilities': {CLASS_NAMES[i]: float(p) for i, p in enumerate(probs)}
                }

        # Ensemble: average probabilities
        ensemble_probs = np.mean(all_probs, axis=0)
    else:
        # Demo mode – deterministic mock based on image brightness
        pixel_mean = np.array(img).mean() / 255.0
        base = np.array([0.6, 0.15, 0.12, 0.08, 0.05])
        shift = int(pixel_mean * 4)
        ensemble_probs = np.roll(base, shift)
        ensemble_probs = np.abs(ensemble_probs)
        ensemble_probs /= ensemble_probs.sum()
        model_predictions['demo'] = {
            'label': CLASS_NAMES[int(np.argmax(ensemble_probs))],
            'level': int(np.argmax(ensemble_probs)),
            'confidence': float(np.max(ensemble_probs)),
            'probabilities': {CLASS_NAMES[i]: float(p) for i, p in enumerate(ensemble_probs)}
        }

    severity_level = int(np.argmax(ensemble_probs))
    confidence = float(ensemble_probs[severity_level])

    return {
        'severity_level': severity_level,
        'severity_label': CLASS_NAMES[severity_level],
        'confidence': round(confidence * 100, 2),
        'severity_color': SEVERITY_COLORS[severity_level],
        'recommendations': RECOMMENDATIONS[severity_level],
        'model_predictions': model_predictions,
        'ensemble_probabilities': {CLASS_NAMES[i]: round(float(p) * 100, 2) for i, p in enumerate(ensemble_probs)},
        'demo_mode': len(models) == 0
    }


# ─── GRADCAM VISUALIZATION ────────────────────────────────────────────────────

def generate_gradcam(image_path: str, target_class: int = None, output_dir: str = None, output_name: str = None) -> dict:
    """
    Generate GradCAM visualizations for the image.
    Shows which regions the models focus on for their predictions.
    
    Args:
        image_path: Path to the retinal image
        target_class: Target class for GradCAM (0-4). If None, uses predicted class.
        output_dir: Optional directory to save a representative overlay image.
        output_name: Optional filename stem for the saved overlay.
    
    Returns:
        Dictionary with GradCAM heatmap information for each model
    """
    from .gradcam import create_gradcam_for_models, overlay_gradcam
    
    img = Image.open(image_path).convert('RGB')
    img_array = np.array(img)
    transform = get_transform(256)
    tensor = transform(img).unsqueeze(0).to(DEVICE)
    
    models = _load_models()
    
    if not models:
        return {'error': 'Models not loaded', 'demo_mode': True}
    
    # Predict if target_class not specified
    if target_class is None:
        with torch.no_grad():
            for name, model in models.items():
                out = model(tensor)
                target_class = int(torch.argmax(out, dim=1).cpu().numpy()[0])
                break  # Use first model's prediction
    
    # Generate GradCAM for each model
    heatmaps = create_gradcam_for_models(models, tensor, class_idx=target_class)
    
    # Create overlay images
    result = {
        'target_class': target_class,
        'target_label': CLASS_NAMES[target_class],
        'heatmaps': {},
        'gradcam_path': None
    }

    static_root = STATIC_ROOT
    if output_dir is None:
        output_dir = os.path.join(static_root, 'generated', 'gradcam')
    os.makedirs(output_dir, exist_ok=True)
    base_name = output_name or os.path.splitext(os.path.basename(image_path))[0]
    
    for name, heatmap in heatmaps.items():
        # Create overlay
        overlay = overlay_gradcam(img_array, heatmap, alpha=0.5)
        
        # Store statistics
        result['heatmaps'][name] = {
            'mean_activation': float(heatmap.mean()),
            'max_activation': float(heatmap.max()),
            'min_activation': float(heatmap.min())
        }

        if result['gradcam_path'] is None:
            safe_name = re.sub(r'[^A-Za-z0-9_-]+', '_', f'{base_name}_{name}_gradcam')
            filename = f'{safe_name}.png'
            full_path = os.path.join(output_dir, filename)
            Image.fromarray(overlay).save(full_path)
            result['gradcam_path'] = os.path.relpath(full_path, static_root).replace('\\', '/')
    
    return result

