#!/usr/bin/env python3
import sys
import argparse
import io
import os

# Redirect standard output to a null device immediately during module imports
stdout_backup = sys.stdout
sys.stdout = open(os.devnull, 'w')

try:
    import torch
    from PIL import Image
    from diffusers import StableDiffusionInstructPix2PixPipeline, StableDiffusionPipeline, EulerAncestralDiscreteScheduler
finally:
    sys.stdout = stdout_backup


def log_status(message: str):
    """Prints status updates to stderr to avoid corrupting the stdout byte stream."""
    sys.stderr.write(f"[STATUS] {message}\n")
    sys.stderr.flush()


def log_warning(message: str):
    """Prints warning messages to stderr."""
    sys.stderr.write(f"[WARNING] {message}\n")
    sys.stderr.flush()


def enforce_multiple_of_8(value: int) -> int:
    """Rounds value down to the nearest multiple of 8 (required by diffusion models)."""
    return (value // 8) * 8


def validate_image_size(size: int) -> int:
    """
    Validates and enforces image size constraints.
    
    Constraints:
    - Minimum: 256 pixels (practical lower bound)
    - Maximum: 1024 pixels (CPU memory safe)
    - Must be multiple of 8
    
    Returns the validated size.
    """
    MIN_SIZE = 256
    MAX_SIZE = 1024
    
    # Enforce bounds
    if size < MIN_SIZE:
        log_warning(f"Image size {size} is below minimum {MIN_SIZE}. Adjusting to {MIN_SIZE}.")
        size = MIN_SIZE
    elif size > MAX_SIZE:
        log_warning(f"Image size {size} exceeds maximum safe size {MAX_SIZE} for CPU inference. Adjusting to {MAX_SIZE}.")
        size = MAX_SIZE
    
    # Enforce multiple of 8
    aligned_size = enforce_multiple_of_8(size)
    if aligned_size != size:
        log_status(f"Adjusted image size from {size} to {aligned_size} (must be multiple of 8).")
        size = aligned_size
    
    # Estimate memory usage and warn if necessary
    estimated_memory_gb = (size * size * 4) / (1024**3)  # Rough estimate for float32
    if estimated_memory_gb > 2:
        log_warning(f"Image size {size}×{size} will require approximately {estimated_memory_gb:.1f}GB of system memory. Processing may be slow.")
    
    return size


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="CPU-Optimized CLI tool for Text-to-Image and Text-Image-to-Image editing. "
                    "Outputs raw image bytes directly to stdout."
    )
    
    # Required arguments
    parser.add_argument("--prompt", type=str, required=True, 
                        help="The text instruction for image generation or modification.")
    parser.add_argument("--images", type=str, required=False, default=None,
                        help="Space-separated paths to your input images, e.g., '/path/1.jpg /path/2.jpg'. "
                             "If not provided, generates image from text prompt only.")
    
    # Model selection
    parser.add_argument("--model", type=str, default=None,
                        help="HuggingFace model ID for image generation or editing. "
                             "Default: 'timbrooks/instruct-pix2pix' (requires input image) or "
                             "'runwayml/stable-diffusion-v1-5' (text-only). "
                             "Auto-selected based on input mode if not specified.")
    
    # Hardware tuneable limiters
    parser.add_argument("--max_size", type=int, default=512, 
                        help="Max width/height bounding box to resize images down to (256-1024). Lower equals faster processing.")
    parser.add_argument("--steps", type=int, default=15, 
                        help="Number of inference denoising steps. Recommended range for CPU: 10 to 20.")
    parser.add_argument("--threads", type=int, default=0, 
                        help="Number of CPU core threads for PyTorch to consume. Set to 0 to auto-utilize all cores.")
    parser.add_argument("--guidance", type=float, default=7.5, 
                        help="Text guidance scale (how heavily to weight your prompt text).")
    parser.add_argument("--image_guidance", type=float, default=1.5, 
                        help="Image guidance scale (how closely to stick to the original image layout). Only for image-to-image.")

    return parser.parse_args()


def process_and_resize_image(image_path: str, max_size: int) -> Image.Image:
    """Loads an image, converts it to RGB, and scales it down to match CPU constraints."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input file not found at: {image_path}")
        
    img = Image.open(image_path).convert("RGB")
    
    # Calculate scale factor maintaining aspect ratio
    width, height = img.size
    if width > max_size or height > max_size:
        scale = max_size / max(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        log_status(f"Resized image '{image_path}' from {width}x{height} down to {new_width}x{new_height} for CPU.")
    
    # Enforce 8-pixel alignment for diffusion model compatibility
    final_width = enforce_multiple_of_8(img.width)
    final_height = enforce_multiple_of_8(img.height)
    if final_width != img.width or final_height != img.height:
        img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)
        log_status(f"Aligned image dimensions to {final_width}x{final_height} (multiple of 8).")
    
    return img


def load_pipeline(model_id: str, is_text_to_image: bool):
    """Loads the specified pipeline model from HuggingFace."""
    log_status(f"Loading model: {model_id}")
    log_status("Loading weights into system RAM (Target: CPU)...")
    
    try:
        if is_text_to_image:
            # Use generic Stable Diffusion for text-to-image generation
            log_status("Mode: Text-to-Image generation")
            pipeline = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float32,
                safety_checker=None
            )
        else:
            # Try loading as InstructPix2Pix for image-to-image (backward compatibility)
            log_status("Mode: Image-to-Image editing")
            if "instruct-pix2pix" in model_id.lower():
                pipeline = StableDiffusionInstructPix2PixPipeline.from_pretrained(
                    model_id, 
                    torch_dtype=torch.float32,
                    safety_checker=None
                )
            else:
                # Fallback to generic Stable Diffusion Img2Img loader
                from diffusers import StableDiffusionImg2ImgPipeline
                pipeline = StableDiffusionImg2ImgPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float32,
                    safety_checker=None
                )
        
        # Enforce CPU execution framework
        pipeline.to("cpu")
        
        # Implement the highly efficient Euler Ancestral sampler for faster generation cycles
        pipeline.scheduler = EulerAncestralDiscreteScheduler.from_config(pipeline.scheduler.config)
        log_status("Model structure compiled successfully on host system RAM.")
        
        return pipeline
        
    except Exception as e:
        sys.stderr.write(f"[ERROR] Model failed to download or allocate in memory: {str(e)}\n")
        sys.exit(1)


def main():
    args = parse_arguments()
    
    # Step 1: Validate and enforce image size constraints
    validated_size = validate_image_size(args.max_size)
    
    # Step 2: Threading Optimization
    if args.threads > 0:
        torch.set_num_threads(args.threads)
        log_status(f"Configuring system execution to restrict usage to {args.threads} CPU threads.")
    else:
        log_status("Utilizing all available CPU multi-threading cores for model calculation.")

    # Step 3: Determine pipeline mode based on input images
    input_image = None
    is_text_to_image = args.images is None
    
    if not is_text_to_image:
        image_paths = [p.strip() for p in args.images.split() if p.strip()]
        if not image_paths:
            sys.stderr.write("[ERROR] No valid image paths were extracted from the --images argument string.\n")
            sys.exit(1)
            
        try:
            input_image = process_and_resize_image(image_paths[0], validated_size)
            log_status("Input image loaded successfully.")
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to load input image: {str(e)}\n")
            sys.exit(1)
    else:
        log_status("No input image provided. Generating image from text prompt only.")

    # Step 4: Auto-select model based on mode if not explicitly provided
    model_id = args.model
    if model_id is None:
        if is_text_to_image:
            model_id = "runwayml/stable-diffusion-v1-5"
            log_status("Auto-selected text-to-image model: runwayml/stable-diffusion-v1-5")
        else:
            model_id = "timbrooks/instruct-pix2pix"
            log_status("Auto-selected image-to-image model: timbrooks/instruct-pix2pix")

    # Step 5: Initialize Pipeline with configurable model
    pipeline = load_pipeline(model_id, is_text_to_image)

    # Step 6: Run Inference Process
    log_status(f"Beginning execution sequence: Running {args.steps} steps with text prompt: '{args.prompt}'...")
    try:
        if is_text_to_image:
            # Text-to-Image generation
            output_data = pipeline(
                prompt=args.prompt,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                height=validated_size,
                width=validated_size
            )
        else:
            # Image-to-Image editing
            output_data = pipeline(
                prompt=args.prompt,
                image=input_image,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                image_guidance_scale=args.image_guidance
            )
        
        output_image = output_data.images[0]
        log_status("Image processing iteration complete. Packaging output stream bytes...")
    except Exception as e:
        sys.stderr.write(f"[ERROR] Error occurred during generation pass: {str(e)}\n")
        sys.exit(1)

    # Step 7: Convert Image to Binary and Pipe Stream to Stdout
    try:
        byte_stream = io.BytesIO()
        output_image.save(byte_stream, format="PNG")
        binary_content = byte_stream.getvalue()
        
        sys.stderr.flush()
        sys.stdout.buffer.write(binary_content)
        sys.stdout.buffer.flush()
    except Exception as e:
        sys.stderr.write(f"[ERROR] Critical system failure while writing stream to stdout: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()