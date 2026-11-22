
from transformers import AutoTokenizer

# Load a pretrained tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "bert-base-uncased"
)

text = "NIFTY market is bullish today!"

# Tokenize
tokens = tokenizer.tokenize(text)

# Convert tokens into IDs
token_ids = tokenizer.convert_tokens_to_ids(tokens)

# Complete encoding
encoding = tokenizer(
    text,
    add_special_tokens=True
)

print("Original text:", text)
print("Tokens:", tokens)
print("Token IDs:", token_ids)
print("Complete encoding:", encoding)
print("Number of tokens:", len(encoding["input_ids"]))
