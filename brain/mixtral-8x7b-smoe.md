# Mixtral 8x7B: Sparse Mixture of Experts

**Paper:** arXiv:2401.04088  
**Authors:** Mistral AI (Albert Q. Jiang et al.)  
**License:** Apache 2.0

## Overview
A Sparse Mixture of Experts (SMoE) language model with 8 experts per layer, achieving 47B total parameters but only using 13B active parameters during inference.

## Key Insights
- **SMoE Architecture:** Each layer has 8 feedforward experts; a router selects 2 experts per token, enabling dynamic specialization while maintaining efficiency
- **Efficient Inference:** Despite 47B total params, only 13B active during forward pass — cost equivalent to a 13B model with 47B model capacity
- **Benchmark Performance:** Outperforms Llama 2 70B and GPT-3.5 across all benchmarks; especially strong in mathematics, code generation, and multilingual tasks
- **Instruction Following:** Mixtral 8x7B - Instruct surpasses GPT-3.5 Turbo, Claude-2.1, and Gemini Pro on human benchmarks

## Technical Highlights
- 32k token context window
- Same transformer architecture as Mistral 7B with MoE layers replacing standard FFN
- Expert routing is token-dependent and dynamic per timestep

## Takeaway
Mixtral's sparse mixture of experts enables massive parameter count with efficient inference, democratizing access to 70B-class model performance.

## Tags
#llm #mixture-of-experts #moe #mistral #open-source #efficient-inference
