# Model Documentation: Qwen2.5-7B-Instruct

## Overview
The Qwen2.5-7B-Instruct is a causal language model based on the `qwen2` architecture. It is designed for high-performance text generation tasks with support for extended context lengths.

## Technical Specifications

### Architecture
*   **Model Type:** `qwen2`
*   **Architecture Class:** `Qwen2ForCausalLM`
*   **Hidden Size:** 3584
*   **Intermediate Size:** 18944
*   **Number of Hidden Layers:** 28
*   **Number of Attention Heads:** 28
*   **Number of Key-Value Heads:** 4

### Performance and Constraints
*   **Max Position Embeddings:** 32768
*   **Sliding Window:** 131072
*   **Max Window Layers:** 28
*   **Use Sliding Window:** False
*   **Attention Dropout:** 0.0
*   **RMS Norm Epsilon:** 1e-06
*   **RoPE Theta:** 1000000.0

### Tokenization
*   **Vocabulary Size:** 152064
*   **BOS Token ID:** 151643
*   **EOS Token ID:** 151645

### Configuration and Deployment
*   **Torch Data Type:** `bfloat16`
*   **Initializer Range:** 0.02
*   **Tie Word Embeddings:** False
*   **Use Cache:** True
*   **Transformers Version:** 4.43.1

***

### References
*   *Project:* codx-junior
*   *Category:* Models