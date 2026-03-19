# 110_process_maxar_omnimask.py
import argparse
import os
import numpy as np
import rasterio
from rasterio.windows import Window
import logging
import torch # Assuming PyTorch based on repo logic

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def load_omnimask_model(model_path):
    """
    Loads the trained Deep Learning model weights.
    Adapting this to the common patterns found in the akveg-map repository.
    """
    logging.info(f"Loading model weights from: {model_path}")
    # This is a placeholder for the specific architecture instantiation 
    # used in your akveg-map/02a_data_reflectance_vhr/omni logic.
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = torch.load(model_path, map_location=device)
    model.eval()
    return model, device

def process_image(input_path, output_path, model_path):
    """
    Applies the omnimask deep learning model to the 16-bit TOA imagery.
    Operates on windows to manage VHR memory requirements.
    """
    model, device = load_omnimask_model(model_path)
    
    logging.info(f"Opening image: {input_path}")
    with rasterio.open(input_path) as src:
        profile = src.profile.copy()
        profile.update(
            dtype=rasterio.uint8,
            count=1,
            nodata=0,
            compress='lzw'
        )

        with rasterio.open(output_path, 'w', **profile) as dst:
            # Iterate through blocks for memory efficiency
            for _, window in src.block_windows(1):
                # Read 16-bit Scaled Integer data [0, 10000]
                # Maxar standard bands: B, G, R, NIR
                img_data = src.read(window=window).astype(np.float32)
                
                # 1. Normalize to [0, 1] for the DL model
                img_data /= 10000.0
                
                # 2. Convert to Tensor and add Batch dimension [C, H, W] -> [1, C, H, W]
                input_tensor = torch.from_numpy(img_data).unsqueeze(0).to(device)
                
                # 3. Inference
                with torch.no_grad():
                    # Predict cloud/shadow classes
                    output = model(input_tensor)
                    # Get class with highest probability
                    pred_mask = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()
                
                # Write uint8 mask block to disk
                dst.write(pred_mask.astype(np.uint8), 1, window=window)

    logging.info(f"Inference complete. Mask saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Omnimask DL logic for Maxar TOA imagery.")
    parser.add_argument("--input", required=True, help="Path to input 16-bit TOA GeoTIFF")
    parser.add_argument("--output", required=True, help="Path to save the output mask")
    parser.add_argument("--model", default="./models/omnimask_weights.pt", help="Path to model weights")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        logging.error(f"Input file not found: {args.input}")
    else:
        process_image(args.input, args.output, args.model)