
import numpy as np
from collections import Counter


# --------------------------------------------------
# 1. CORPUS
# --------------------------------------------------

corpus = [
    "the quick brown fox jumps over the lazy dog"
]

# Repeat the sentence to create more training examples
corpus = corpus * 100


# --------------------------------------------------
# 2. TOKENIZATION AND VOCABULARY
# --------------------------------------------------

tokens = []

for sentence in corpus:
    tokens.extend(sentence.lower().split())

word_counts = Counter(tokens)

vocabulary = sorted(word_counts.keys())

word_to_id = {
    word: idx
    for idx, word in enumerate(vocabulary)
}

id_to_word = {
    idx: word
    for word, idx in word_to_id.items()
}

vocab_size = len(vocabulary)

print("Vocabulary:", vocabulary)
print("Vocabulary Size:", vocab_size)


# --------------------------------------------------
# 3. GENERATE CBOW TRAINING DATA
# --------------------------------------------------

window_size = 2

training_data = []

for sentence in corpus:
    sentence_tokens = sentence.lower().split()

    for i in range(window_size, len(sentence_tokens) - window_size):

        context = (
            sentence_tokens[i - window_size:i]
            + sentence_tokens[i + 1:i + window_size + 1]
        )

        target = sentence_tokens[i]

        context_ids = [
            word_to_id[word]
            for word in context
        ]

        target_id = word_to_id[target]

        training_data.append((context_ids, target_id))

# --------------------------------------------------
# 4. INITIALIZE MODEL PARAMETERS
# --------------------------------------------------

np.random.seed(42)

embedding_dim = 10
learning_rate = 0.05
epochs = 100

# Input embedding matrix
W_in = np.random.randn(
    vocab_size, embedding_dim
) * 0.01

# Output weight matrix
W_out = np.random.randn(
    embedding_dim, vocab_size
) * 0.01


# --------------------------------------------------
# 5. SOFTMAX FUNCTION
# --------------------------------------------------

def softmax(x):

    exp_values = np.exp(x - np.max(x))

    return exp_values / np.sum(exp_values)


# --------------------------------------------------
# 6. TRAIN CBOW MODEL
# --------------------------------------------------

for epoch in range(epochs):

    total_loss = 0

    np.random.shuffle(training_data)

    for context_ids, target_id in training_data:

        # Forward propagation

        context_embeddings = W_in[context_ids]

        hidden = np.mean(
            context_embeddings,
            axis=0
        )

        logits = hidden @ W_out

        probabilities = softmax(logits)

        # Cross-entropy loss

        loss = -np.log(
            probabilities[target_id] + 1e-12
        )

        total_loss += loss

        # Backpropagation

        d_logits = probabilities.copy()

        d_logits[target_id] -= 1

        dW_out = np.outer(hidden, d_logits)

        d_hidden = W_out @ d_logits

        dW_in = np.zeros_like(W_in)

        for context_id in context_ids:

            dW_in[context_id] += (
                d_hidden / len(context_ids)
            )

        # Gradient descent update

        W_out -= learning_rate * dW_out

        W_in -= learning_rate * dW_in

    average_loss = total_loss / len(training_data)

    if (epoch + 1) % 10 == 0:

        print(
            f"Epoch {epoch + 1}, Loss: {average_loss:.4f}"
        )


# --------------------------------------------------
# 7. PREDICT TARGET WORD
# --------------------------------------------------

def predict(context_words):

    context_ids = [
        word_to_id[word]
        for word in context_words
    ]

    embeddings = W_in[context_ids]

    hidden = np.mean(embeddings, axis=0)

    logits = hidden @ W_out

    probabilities = softmax(logits)

    predicted_id = np.argmax(probabilities)

    return id_to_word[predicted_id], probabilities


# --------------------------------------------------
# 8. TEST PREDICTION
# --------------------------------------------------

context = ["the", "quick", "fox", "jumps"]

predicted_word, probabilities = predict(context)

print("\nPrediction Test:")
print("Context:", context)
print("Predicted Target:", predicted_word)

# Display top 5 predictions
top_indices = np.argsort(probabilities)[::-1][:5]

print("\nTop 5 Predictions:")

for idx in top_indices:

    print(
        id_to_word[idx],
        ":", round(float(probabilities[idx]), 4)
    )


# --------------------------------------------------
# 9. DISPLAY LEARNED EMBEDDINGS
# --------------------------------------------------

print("\nLearned Word Embeddings:")

for word, word_id in word_to_id.items():

    print(word, ":", W_in[word_id])



# --------------------------------------------------
# 10. COSINE SIMILARITY
# --------------------------------------------------

def cosine_similarity(word1, word2):

    vector1 = W_in[word_to_id[word1]]
    vector2 = W_in[word_to_id[word2]]

    similarity = np.dot(vector1, vector2) / (
        np.linalg.norm(vector1) *
        np.linalg.norm(vector2)
    )

    return float(similarity)


# --------------------------------------------------
# 11. TEST WORD SIMILARITY
# --------------------------------------------------

word_pairs = [
    ("fox", "the"),
    ("quick", "brown"),
    ("dog", "lazy"),
    ("fox", "dog"),
]

print("\nCosine Similarity Results:")

for word1, word2 in word_pairs:

    score = cosine_similarity(word1, word2)

    print(
        f"{word1} vs {word2}: {score:.8f}"
    )
