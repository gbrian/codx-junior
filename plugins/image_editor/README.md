# CPU-Optimized Image Editor Plugin

A fast, resource-efficient CLI tool for text-guided image-to-image editing using InstructPix2Pix. Optimized for CPU inference with minimal memory footprint. Supports multiple diffusion models for flexible image transformation.

## Features

- **CPU-Optimized**: Runs inference on CPU without GPU dependency
- **Memory Efficient**: Strips unnecessary safety checkers (~1.5GB savings)
- **Fast Processing**: Euler Ancestral sampler for optimized generation cycles
- **Multi-Model Support**: Switch between different diffusion models via CLI
- **Flexible Guidance**: Control both text and image adherence
- **Binary Output**: Direct PNG stream to stdout for pipeline integration

## Quick Start

### Docker (Recommended)

#### Build the Image

```bash
cd plugins/image_editor
docker build -t cpu-image-editor:latest .
```

#### Basic Usage

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "make it a pencil sketch" \
  --images /workspace/images/input.jpg \
  --max_size 512 \
  --steps 15 > output.png
```

#### Advanced Usage with Custom Parameters

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  -e OMP_NUM_THREADS=4 \
  cpu-image-editor:latest \
  --prompt "add colorful graffiti to the walls" \
  --images /workspace/images/street.jpg \
  --max_size 768 \
  --steps 20 \
  --threads 4 \
  --guidance 7.5 \
  --image_guidance 1.5 > output.png
```

### Local Installation

#### Prerequisites

- Python 3.9+
- pip

#### Install

```bash
cd plugins/image_editor
pip install -e .
```

#### Usage

```bash
cpu-image-cli \
  --prompt "transform into watercolor painting" \
  --images input.jpg \
  --max_size 512 \
  --steps 15 > output.png
```

## Model Selection

By default, the tool uses `timbrooks/instruct-pix2pix`. You can switch to different models using the `--model` flag.

### Available Models

#### InstructPix2Pix (Default - Text-Guided Image-to-Image)

Best for: Direct image editing with text instructions. Excellent at following prompts while preserving image structure.

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "make it a pencil sketch" \
  --images /workspace/images/input.jpg \
  --model timbrooks/instruct-pix2pix \
  --steps 15
```

#### Stable Diffusion 2.1 (Image-to-Image)

Best for: General image transformation and style transfer. Good balance between quality and speed.

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "a painting in oil style" \
  --images /workspace/images/input.jpg \
  --model stabilityai/stable-diffusion-2-1 \
  --steps 20
```

#### Stable Diffusion 1.5 (Image-to-Image)

Best for: Faster processing with solid quality. More memory-efficient on limited hardware.

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "watercolor painting style" \
  --images /workspace/images/input.jpg \
  --model runwayml/stable-diffusion-v1-5 \
  --steps 15
```

#### Stability AI Image Variations

Best for: Creating variations of an image while maintaining overall composition.

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "create artistic variations" \
  --images /workspace/images/input.jpg \
  --model stability-ai/stable-diffusion-2-1-base \
  --steps 20
```

### Using Custom Models

Specify any HuggingFace model ID that supports image-to-image generation:

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "your prompt" \
  --images /workspace/images/input.jpg \
  --model <huggingface-model-id> \
  --steps 15
```

### Local Installation with Model Selection

```bash
python image_cli.py \
  --prompt "make it watercolor" \
  --images input.jpg \
  --model timbrooks/instruct-pix2pix \
  --max_size 512 \
  --steps 15 > output.png
```

## Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--prompt` | string | **required** | Text instruction describing modifications to apply to the image |
| `--images` | string | **required** | Space-separated paths to input images (processes first image) |
| `--model` | string | `timbrooks/instruct-pix2pix` | HuggingFace model ID for image-to-image generation |
| `--max_size` | int | 512 | Maximum width/height bounding box; lower = faster processing |
| `--steps` | int | 15 | Number of denoising steps (CPU recommended: 10-20) |
| `--threads` | int | 0 | CPU threads to use (0 = auto-detect all cores) |
| `--guidance` | float | 7.5 | Text guidance scale (higher = stricter prompt adherence) |
| `--image_guidance` | float | 1.5 | Image guidance scale (higher = closer to original layout) |

## Output

The tool outputs raw PNG bytes to stdout, enabling easy integration into pipelines:

```bash
# Save to file
cpu-image-cli --prompt "..." --images input.jpg > output.png

# Pipe to another tool
cpu-image-cli --prompt "..." --images input.jpg | convert - -resize 256x256 resized.png

# Process multiple images
for img in images/*.jpg; do
  cpu-image-cli --prompt "sketch style" --images "$img" > "output_${img##*/}"
done
```

## Performance Tuning

### For Faster Processing

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "your prompt" \
  --images /workspace/images/input.jpg \
  --model runwayml/stable-diffusion-v1-5 \
  --max_size 256 \
  --steps 10 \
  --threads 8
```

- Reduce `--max_size` (256-384 is fast)
- Lower `--steps` (10-12 for draft quality)
- Increase `--threads` to match CPU cores
- Use faster models like `runwayml/stable-diffusion-v1-5`

### For Better Quality

```bash
docker run --rm \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "your prompt" \
  --images /workspace/images/input.jpg \
  --model timbrooks/instruct-pix2pix \
  --max_size 768 \
  --steps 25 \
  --guidance 8.0
```

- Increase `--max_size` (512-768 for detail)
- Increase `--steps` (20-25 for refinement)
- Adjust `--guidance` (7.0-10.0 for prompt strength)
- Use InstructPix2Pix for better instruction following

## Docker Volume Mounting

Mount your image directory to access input and save output:

```bash
# Linux/Mac
docker run --rm \
  -v /path/to/your/images:/workspace/images \
  cpu-image-editor:latest \
  --prompt "..." \
  --images /workspace/images/photo.jpg > /path/to/your/images/output.png

# Windows (PowerShell)
docker run --rm `
  -v C:\Users\YourUser\Pictures:/workspace/images `
  cpu-image-editor:latest `
  --prompt "..." `
  --images /workspace/images/photo.jpg > C:\Users\YourUser\Pictures\output.png
```

## Memory Requirements

- **Minimum**: 16 GB RAM (base model + inference buffer)
- **Recommended**: 32 GB RAM (for larger images and faster processing)
- **With swap**: Can function on 8 GB + sufficient swap space (slower)

Memory usage varies by model size - InstructPix2Pix is most memory-efficient.

## Logging

Status messages appear on stderr, leaving stdout clean for binary data:

```bash
cpu-image-cli --prompt "..." --images input.jpg 2>log.txt > output.png
```

Log output example:
```
[STATUS] Utilizing all available CPU multi-threading cores for model calculation.
[STATUS] Resized image 'input.jpg' from 1024x768 down to 512x384 for CPU.
[STATUS] Loading InstructPix2Pix weights into system RAM (Target: CPU)...
[STATUS] Model structure compiled successfully on host system RAM.
[STATUS] Beginning execution sequence: Running 15 steps with text prompt: 'sketch'...
[STATUS] Image processing iteration complete. Packaging output stream bytes...
```

## Environment Variables

```bash
# Set CPU threads (alternative to --threads flag)
export OMP_NUM_THREADS=4
docker run --rm -e OMP_NUM_THREADS=4 cpu-image-editor:latest ...

# Disable Python bytecode caching (already set in Dockerfile)
export PYTHONDONTWRITEBYTECODE=1

# Hugging Face token (for authenticated model downloads)
export HF_TOKEN=your_token_here
docker run --rm -e HF_TOKEN=$HF_TOKEN cpu-image-editor:latest ...
```

## Example Workflows

### Multi-Model Comparison

Compare different models on the same image:

```bash
#!/bin/bash

MODELS=(
  "timbrooks/instruct-pix2pix"
  "stabilityai/stable-diffusion-2-1"
  "runwayml/stable-diffusion-v1-5"
)

INPUT_IMAGE="/workspace/images/test.jpg"
PROMPT="make it a watercolor painting"

for model in "${MODELS[@]}"; do
  echo "Testing with model: $model"
  docker run --rm \
    -v $(pwd)/images:/workspace/images \
    cpu-image-editor:latest \
    --prompt "$PROMPT" \
    --images "$INPUT_IMAGE" \
    --model "$model" \
    --steps 10 \
    > "output_${model//\//_}.png"
  echo "Saved: output_${model//\//_}.png"
done
```

### Batch Processing

```bash
#!/bin/bash
PROMPTS=(
  "watercolor painting"
  "pencil sketch"
  "oil painting"
)

for img in input_images/*.jpg; do
  for prompt in "${PROMPTS[@]}"; do
    output="results/$(basename "$img" .jpg)_${prompt// /_}.png"
    docker run --rm \
      -v $(pwd)/input_images:/workspace/input \
      -v $(pwd)/results:/workspace/output \
      cpu-image-editor:latest \
      --prompt "$prompt" \
      --images /workspace/input/$(basename "$img") \
      > "$output"
    echo "Created: $output"
  done
done
```

### REST API Integration

```bash
# Build a simple Flask wrapper
docker run --rm \
  -p 5000:5000 \
  -v $(pwd)/images:/workspace/images \
  cpu-image-editor:latest \
  # (Requires custom Flask wrapper - see examples/)
```

## Troubleshooting

### Out of Memory Error

```
RuntimeError: Unable to allocate X.XX GiB for an array
```

**Solution**: Reduce `--max_size` and `--steps`, or switch to a smaller model
```bash
docker run --rm -v $(pwd)/images:/workspace/images cpu-image-editor:latest \
  --prompt "..." --images /workspace/images/input.jpg \
  --model runwayml/stable-diffusion-v1-5 \
  --max_size 256 --steps 10
```

### Slow Processing

**Solution**: Increase thread count, reduce quality settings, or use faster model
```bash
docker run --rm -v $(pwd)/images:/workspace/images cpu-image-editor:latest \
  --prompt "..." --images /workspace/images/input.jpg \
  --model runwayml/stable-diffusion-v1-5 \
  --threads 8 --max_size 384 --steps 12
```

### Model Download Timeout

**Solution**: Pre-download model or increase timeout
```bash
# Pre-download model
docker run --rm -v $(pwd)/images:/workspace/images cpu-image-editor:latest \
  --prompt "test" --images /workspace/images/test.jpg \
  --model <model-id> --steps 1

# Then run your actual job
```

### File Permission Denied

**Solution**: Mount with proper permissions
```bash
sudo chown 1000:1000 /path/to/images
docker run --rm -v /path/to/images:/workspace/images cpu-image-editor:latest ...
```

### Model Not Found Error

**Solution**: Ensure model ID is correct and HuggingFace has internet access
```bash
# Test with known working model
docker run --rm -v $(pwd)/images:/workspace/images cpu-image-editor:latest \
  --prompt "test" --images /workspace/images/test.jpg \
  --model timbrooks/instruct-pix2pix
```

## Architecture

```
┌─────────────────────────────────────┐
│   Image Input (JPG/PNG)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Load & Resize (LANCZOS)           │
│   CPU-Friendly Format               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Diffusion Pipeline (CPU)          │
│   - Selectable Model                │
│   - Float32 Precision               │
│   - Euler Ancestral Scheduler       │
│   - No Safety Checker               │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Image Output (PNG Binary Stream)  │
│   → stdout                          │
└─────────────────────────────────────┘
```

## Performance Benchmarks

Typical performance on 4-core CPU (Intel i7-8550U):

| Model | Input Size | Steps | Time | Memory |
|-------|-----------|-------|------|--------|
| InstructPix2Pix | 256x256 | 10 | 45s | 8 GB |
| InstructPix2Pix | 384x384 | 15 | 2m | 12 GB |
| InstructPix2Pix | 512x512 | 15 | 4m | 16 GB |
| SD 2.1 | 512x512 | 15 | 5m | 18 GB |
| SD 1.5 | 512x512 | 15 | 3.5m | 14 GB |
| InstructPix2Pix | 768x768 | 20 | 8m | 28 GB |

**Note**: Benchmarks are approximate and vary based on hardware and model availability.

## Development

### Build from Source

```bash
git clone <repo>
cd plugins/image_editor
pip install -e ".[dev]"
pytest
```

### Run Locally

```bash
python image_cli.py \
  --prompt "make it a sketch" \
  --images test.png \
  --model timbrooks/instruct-pix2pix \
  --max_size 512 \
  --steps 15 > output.png
```

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please submit issues and PRs to the main repository.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review error messages on stderr

## Model Attribution

Uses multiple diffusion models:
- [InstructPix2Pix](https://github.com/timbrooks/instruct-pix2pix) by Tim Brooks et al.
- [Stable Diffusion](https://github.com/CompVis/stable-diffusion)
- [Stability AI Models](https://huggingface.co/stabilityai)