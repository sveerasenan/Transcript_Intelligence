"""
Test script to demonstrate text optimization for LLM token reduction.

This script shows how the optimize_text_for_llm() method reduces token usage
by removing filler words and compressing verbose phrases.

Usage:
    python test_text_optimization.py
"""

from services.llm_utils import LLMDataTokenizer

# Initialize tokenizer (will load config from config/llm.yaml)
tokenizer = LLMDataTokenizer('config/llm.yaml')

# Test samples (real-world examples from meeting summaries)
test_samples = [
    {
        "name": "Customer Support Call",
        "text": """Customer actually contacted us basically regarding the issue where they were 
really experiencing very slow performance with their backup jobs. In order to troubleshoot 
this issue, we need to conduct an investigation into the agent version. The customer was 
obviously frustrated and literally wanted a solution at this point in time. We provided 
assistance to them and made an attempt to resolve the problem. Prior to this call, they 
had reached out several times. Due to the fact that the issue persisted, we escalated 
it to engineering."""
    },
    {
        "name": "Renewal Discussion",
        "text": """The customer is currently in the process of evaluating renewal options. They 
have the ability to upgrade but are concerned about pricing. Taking into consideration 
the value they've received, we should probably give consideration to offering a discount. 
In the event that they decide not to renew, we may lose a significant account. We should 
make a decision soon and come to a decision on pricing strategy."""
    },
    {
        "name": "Technical Issue",
        "text": """Customer reported that they are basically unable to access their dashboard. 
The system is literally not responding and they are very frustrated. This is actually 
affecting their operations on a daily basis. We need to conduct an investigation and 
provide assistance as soon as possible. In relation to their previous tickets, this seems 
to be a recurring issue that we need to take into account."""
    }
]

print("=" * 80)
print("TEXT OPTIMIZATION DEMO - Token Reduction for LLM API Calls")
print("=" * 80)
print()

total_original = 0
total_optimized = 0

for idx, sample in enumerate(test_samples, 1):
    original_text = sample["text"].strip()
    optimized_text = tokenizer.optimize_text_for_llm(original_text)
    
    original_chars = len(original_text)
    optimized_chars = len(optimized_text)
    reduction = ((original_chars - optimized_chars) / original_chars * 100) if original_chars > 0 else 0
    
    # Rough token estimation: ~4 chars per token (English text average)
    original_tokens = original_chars // 4
    optimized_tokens = optimized_chars // 4
    token_reduction = original_tokens - optimized_tokens
    
    total_original += original_tokens
    total_optimized += optimized_tokens
    
    print(f"Sample {idx}: {sample['name']}")
    print("-" * 80)
    print(f"\n📝 ORIGINAL ({original_chars} chars, ~{original_tokens} tokens):")
    print(f"{original_text[:200]}...")
    print(f"\n✨ OPTIMIZED ({optimized_chars} chars, ~{optimized_tokens} tokens):")
    print(f"{optimized_text[:200]}...")
    print(f"\n💰 SAVINGS: {reduction:.1f}% chars | ~{token_reduction} tokens saved")
    print("\n" + "=" * 80 + "\n")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total Original: ~{total_original} tokens")
print(f"Total Optimized: ~{total_optimized} tokens")
print(f"Total Saved: ~{total_original - total_optimized} tokens")
print(f"Reduction: {((total_original - total_optimized) / total_original * 100):.1f}%")
print()
print("💡 Cost Impact (GPT-4o pricing: $5/1M input tokens):")
print(f"   Before: ${(total_original / 1_000_000 * 5):.6f}")
print(f"   After:  ${(total_optimized / 1_000_000 * 5):.6f}")
print(f"   Saved:  ${((total_original - total_optimized) / 1_000_000 * 5):.6f}")
print()
print("🎯 For batch analysis of 10 meetings:")
print(f"   Original: ~{total_original * 10} tokens (${(total_original * 10 / 1_000_000 * 5):.4f})")
print(f"   Optimized: ~{total_optimized * 10} tokens (${(total_optimized * 10 / 1_000_000 * 5):.4f})")
print(f"   Monthly savings (100 batches): ${((total_original - total_optimized) * 10 * 100 / 1_000_000 * 5):.2f}")
print("=" * 80)
