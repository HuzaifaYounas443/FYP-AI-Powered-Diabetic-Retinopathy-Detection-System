"""
GradCAM (Gradient-weighted Class Activation Mapping) for model interpretability.
Visualizes which regions of the retinal image the model focuses on for predictions.
"""
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import cv2
import re


class GradCAM:
    def __init__(self, model, target_layer, device='cpu'):
        """
        Initialize GradCAM for a given model and target layer.
        
        Args:
            model: PyTorch model
            target_layer: The name of the layer to target (e.g., 'backbone.features[-1]')
            device: 'cpu' or 'cuda'
        """
        self.model = model
        self.device = device
        self.target_layer = target_layer
        self.gradient = None
        self.activation = None
        self.forward_hook_handle = None
        self.backward_hook_handle = None
        
        # Register hooks
        self._register_hooks()
    
    def _register_hooks(self):
        """Register forward and backward hooks on the target layer."""
        def forward_hook(module, input, output):
            self.activation = output.detach()
        
        def backward_hook(module, grad_input, grad_output):
            self.gradient = grad_output[0].detach()
        
        # Get the target layer
        target_layer_module = self._get_layer(self.model, self.target_layer)
        self.forward_hook_handle = target_layer_module.register_forward_hook(forward_hook)
        self.backward_hook_handle = target_layer_module.register_full_backward_hook(backward_hook)

    def close(self):
        if self.forward_hook_handle is not None:
            self.forward_hook_handle.remove()
            self.forward_hook_handle = None
        if self.backward_hook_handle is not None:
            self.backward_hook_handle.remove()
            self.backward_hook_handle = None
    
    def _get_layer(self, model, layer_name):
        """Get a layer from the model by name (supports nested attributes and indices)."""
        layer = model
        for attr in layer_name.split('.'):
            match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\[(-?\d+)\]', attr)
            if match:
                layer = getattr(layer, match.group(1))[int(match.group(2))]
            else:
                layer = getattr(layer, attr)
        return layer
    
    def generate(self, input_tensor, class_idx=None):
        """
        Generate GradCAM heatmap for the given input.
        
        Args:
            input_tensor: Input tensor (1, 3, H, W)
            class_idx: Target class index. If None, uses the predicted class.
        
        Returns:
            heatmap: GradCAM heatmap (H, W)
        """
        # Forward pass
        output = self.model(input_tensor)
        
        # Determine target class
        if class_idx is None:
            class_idx = output.argmax(dim=1).item()
        
        # Zero gradients
        self.model.zero_grad()
        
        # Backward pass
        target = output[0, class_idx]
        target.backward()
        
        # Calculate GradCAM
        gradients = self.gradient[0]  # (C, H, W)
        activations = self.activation[0]  # (C, H, W)
        
        # Global average pooling of gradients
        weights = gradients.mean(dim=(1, 2))  # (C,)
        
        # Weighted sum of activations
        heatmap = torch.zeros(activations.shape[1:], device=self.device)
        for i, weight in enumerate(weights):
            heatmap += weight * activations[i]
        
        # ReLU to keep only positive contributions
        heatmap = F.relu(heatmap)
        
        # Normalize
        heatmap = heatmap / (heatmap.max() + 1e-8)
        
        return heatmap.cpu().numpy()


def overlay_gradcam(image_array, heatmap, alpha=0.4, colormap=cv2.COLORMAP_JET):
    """
    Overlay GradCAM heatmap on the original image.
    
    Args:
        image_array: Original image (H, W, 3) with values 0-255
        heatmap: GradCAM heatmap (H, W) with values 0-1
        alpha: Transparency of the heatmap overlay
        colormap: OpenCV colormap
    
    Returns:
        overlay_image: Image with overlaid heatmap
    """
    # Normalize heatmap to 0-255
    heatmap_255 = (heatmap * 255).astype(np.uint8)
    
    # Resize heatmap to match image size
    if heatmap_255.shape != image_array.shape[:2]:
        heatmap_255 = cv2.resize(heatmap_255, (image_array.shape[1], image_array.shape[0]))
    
    # Apply colormap
    heatmap_color = cv2.applyColorMap(heatmap_255, colormap)
    # Convert from BGR to RGB
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
    
    # Blend images
    overlay = cv2.addWeighted(image_array, 1 - alpha, heatmap_color, alpha, 0)
    
    return overlay


def create_gradcam_for_models(models, input_tensor, class_idx=None):
    """
    Create GradCAM visualizations for multiple models.
    
    Args:
        models: Dictionary of {name: model}
        input_tensor: Input tensor (1, 3, H, W)
        class_idx: Target class index
    
    Returns:
        heatmaps: Dictionary of {name: heatmap}
    """
    device = input_tensor.device
    heatmaps = {}
    
    for name, model in models.items():
        gradcam = None
        try:
            # Different target layers for different architectures
            if 'efficientnet' in name.lower():
                target_layer = 'backbone.features[-1]'
            elif 'resnet' in name.lower():
                target_layer = 'backbone.layer4[-1]'
            else:
                target_layer = None
            
            if target_layer:
                gradcam = GradCAM(model, target_layer, device=device)
                heatmap = gradcam.generate(input_tensor, class_idx)
                heatmaps[name] = heatmap
        except Exception as e:
            print(f"[GradCAM] Could not generate for {name}: {e}")
        finally:
            if gradcam is not None:
                gradcam.close()
    
    return heatmaps
