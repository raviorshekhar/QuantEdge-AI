
from bpe_tokenizer import BPETokenizer


corpus = {
    "low": 5,
    "lower": 2,
    "newest": 6,
    "widest": 3,
}


# --------------------------------------------------
# 1. Train Tokenizer
# --------------------------------------------------

tokenizer = BPETokenizer()

tokenizer.train(corpus, num_merges=5)

print("Learned rules:")
print(tokenizer.merge_rules)


# --------------------------------------------------
# 2. Text Encoding and Decoding
# --------------------------------------------------

word = "lowest"

tokens = tokenizer.encode(word)
decoded = tokenizer.decode(tokens)

print("\nText Encoding Test:")
print("Input:", word)
print("Tokens:", tokens)
print("Decoded:", decoded)


# --------------------------------------------------
# 3. Token ID Encoding and Decoding
# --------------------------------------------------

token_ids = tokenizer.encode_to_ids("lowest")

decoded_text = tokenizer.decode_from_ids(token_ids)

print("\nToken ID Test:")
print("Token to ID:", tokenizer.token_to_id)
print("Input:", "lowest")
print("Token IDs:", token_ids)
print("Decoded:", decoded_text)


# --------------------------------------------------
# 4. Save Tokenizer
# --------------------------------------------------

tokenizer.save("outputs/tokenizer.json")

print("\nTokenizer saved successfully!")


# --------------------------------------------------
# 5. Load Tokenizer
# --------------------------------------------------

loaded_tokenizer = BPETokenizer.load(
    "outputs/tokenizer.json"
)

print("Tokenizer loaded successfully!")


# --------------------------------------------------
# 6. Verify Loaded Tokenizer
# --------------------------------------------------

text = "lowest widest"

loaded_token_ids = loaded_tokenizer.encode_to_ids(text)

decoded = loaded_tokenizer.decode_from_ids(
    loaded_token_ids
)

print("\nSave/Load Verification:")
print("Input:", text)
print("Token IDs:", loaded_token_ids)
print("Decoded:", decoded)
