
from collections import Counter

corpus = [
    "the quick brown fox jumps over the lazy dog"
]

corpus = corpus * 100

# Step 1: Build vocabulary
tokens = []

for sentence in corpus:
    tokens.extend(sentence.lower().split())

word_counts = Counter(tokens)

vocabulary = sorted(word_counts.keys())

word_to_id = {
    word: idx for idx, word in enumerate(vocabulary)
}

id_to_word = {
    idx: word for word, idx in word_to_id.items()
}

vocab_size = len(vocabulary)

print("Vocabulary:", vocabulary)
print("Vocabulary Size:", vocab_size)


# Step 2: Generate Skip-gram training pairs

window_size = 2

training_data = []

for sentence in corpus:
    sentence_tokens = sentence.lower().split()

    for i, target_word in enumerate(sentence_tokens):

        start = max(0, i - window_size)
        end = min(len(sentence_tokens), i + window_size + 1)

        for j in range(start, end):

            if i != j:
                context_word = sentence_tokens[j]

                target_id = word_to_id[target_word]
                context_id = word_to_id[context_word]

                training_data.append((target_id, context_id))


print("\nTotal Training Pairs:", len(training_data))

print("\nFirst 10 Training Pairs:")

for target_id, context_id in training_data[:10]:
    print(
        id_to_word[target_id],
        "->",
        id_to_word[context_id]
    )


import numpy as np

# Step 3: Initialize model parameters

embedding_dim = 10
learning_rate = 0.05
epochs = 100

np.random.seed(42)

W_in = np.random.randn(vocab_size, embedding_dim) * 0.01

W_out = np.random.randn(embedding_dim, vocab_size) * 0.01

print("\nModel Parameters:")
print("W_in shape:", W_in.shape)
print("W_out shape:", W_out.shape)


# Step 4: Softmax function

def softmax(logits):
    exp_values = np.exp(logits - np.max(logits))
    return exp_values / np.sum(exp_values)


# Step 5: Forward pass

def forward(target_id):
    hidden = W_in[target_id]

    logits = hidden @ W_out

    probabilities = softmax(logits)

    return hidden, probabilities


# Test forward pass

target_id = word_to_id["brown"]

hidden, probabilities = forward(target_id)

print("\nForward Pass Test:")
print("Input Word: brown")
print("Hidden Shape:", hidden.shape)
print("Probability Shape:", probabilities.shape)
print("Probability Sum:", np.sum(probabilities))


# Step 6: Training one sample

def train_one_sample(target_id, context_id):

    global W_in, W_out

    # Forward pass
    hidden = W_in[target_id]
    logits = hidden @ W_out
    probabilities = softmax(logits)

    # Calculate loss
    loss = -np.log(probabilities[context_id] + 1e-10)

    # Backpropagation
    d_logits = probabilities.copy()
    d_logits[context_id] -= 1

    dW_out = np.outer(hidden, d_logits)

    d_hidden = W_out @ d_logits

    dW_in = np.zeros_like(W_in)
    dW_in[target_id] += d_hidden

    # Update weights
    W_out -= learning_rate * dW_out
    W_in -= learning_rate * dW_in

    return loss


# Test one training sample

target_id = word_to_id["brown"]
context_id = word_to_id["quick"]

loss = train_one_sample(target_id, context_id)

print("\nSingle Training Sample Test:")
print("Input Word: brown")
print("Expected Context Word: quick")
print("Loss:", loss)


# Step 7: Train Skip-gram model

for epoch in range(epochs):

    np.random.shuffle(training_data)

    total_loss = 0

    for target_id, context_id in training_data:

        loss = train_one_sample(target_id, context_id)

        total_loss += loss

    average_loss = total_loss / len(training_data)

    if (epoch + 1) % 10 == 0:
        print(
            f"Epoch {epoch + 1}, "
            f"Loss: {average_loss:.4f}"
        )


# Step 8: Prediction test

target_word = "brown"
target_id = word_to_id[target_word]

_, probabilities = forward(target_id)

top_indices = np.argsort(probabilities)[::-1][:5]

print("\nSkip-gram Prediction Test:")
print("Input Word:", target_word)
print("Top 5 Predicted Context Words:")

for idx in top_indices:
    print(
        f"{id_to_word[idx]} : {probabilities[idx]:.6f}"
    )


# Step 9: Display learned embeddings

print("\nLearned Word Embeddings:")

for word in vocabulary:
    embedding = W_in[word_to_id[word]]
    print(f"{word}: {embedding}")


# Step 10: Cosine similarity

def cosine_similarity(word1, word2):

    vector1 = W_in[word_to_id[word1]]
    vector2 = W_in[word_to_id[word2]]

    similarity = np.dot(vector1, vector2) / (
        np.linalg.norm(vector1) * np.linalg.norm(vector2)
    )

    return float(similarity)


word_pairs = [
    ("fox", "the"),
    ("quick", "brown"),
    ("dog", "lazy"),
    ("fox", "dog"),
]

print("\nCosine Similarity Results:")

for word1, word2 in word_pairs:
    score = cosine_similarity(word1, word2)
    print(f"{word1} vs {word2}: {score:.8f}")
