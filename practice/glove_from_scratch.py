
import numpy as np

# Step 1: Prepare corpus

corpus = [
    "the quick brown fox jumps over the lazy dog"
]

corpus = corpus * 100


# Step 2: Build vocabulary

tokens = []

for sentence in corpus:
    tokens.extend(sentence.lower().split())

vocabulary = sorted(set(tokens))

word_to_id = {
    word: idx for idx, word in enumerate(vocabulary)
}

id_to_word = {
    idx: word for word, idx in word_to_id.items()
}

vocab_size = len(vocabulary)

print("Vocabulary:", vocabulary)
print("Vocabulary Size:", vocab_size)


# Step 3: Build co-occurrence matrix

window_size = 2

cooccurrence_matrix = np.zeros(
    (vocab_size, vocab_size),
    dtype=np.float64
)

for sentence in corpus:

    sentence_tokens = sentence.lower().split()

    for i, target_word in enumerate(sentence_tokens):

        target_id = word_to_id[target_word]

        start = max(0, i - window_size)
        end = min(len(sentence_tokens), i + window_size + 1)

        for j in range(start, end):

            if i != j:

                context_word = sentence_tokens[j]
                context_id = word_to_id[context_word]

                distance = abs(i - j)

                cooccurrence_matrix[target_id, context_id] += (
                    1.0 / distance
                )


# Step 4: Display matrix

print("\nCo-occurrence Matrix:")
print(cooccurrence_matrix)

print("\nMatrix Shape:", cooccurrence_matrix.shape)

print(
    "Is Symmetric:",
    np.allclose(cooccurrence_matrix, cooccurrence_matrix.T)
)


# Step 5: Display selected word pairs

word_pairs = [
    ("brown", "quick"),
    ("brown", "fox"),
    ("brown", "the"),
    ("dog", "lazy")
]

print("\nSelected Co-occurrence Values:")

for word1, word2 in word_pairs:

    id1 = word_to_id[word1]
    id2 = word_to_id[word2]

    value = cooccurrence_matrix[id1, id2]

    print(f"{word1} - {word2}: {value}")


# Step 6: GloVe hyperparameters

embedding_dim = 10
x_max = 100
alpha = 0.75

# Step 7: GloVe weighting function

def weighting_function(x):

    if x == 0:
        return 0.0

    if x < x_max:
        return (x / x_max) ** alpha

    return 1.0


# Step 8: Test weighting function

test_values = [0, 1, 10, 50, 100, 200]

print("\nGloVe Weighting Function:")

for value in test_values:

    weight = weighting_function(value)

    print(f"X = {value:3d}, Weight = {weight:.4f}")


# Step 9: Initialize GloVe parameters

np.random.seed(42)

W = np.random.randn(vocab_size, embedding_dim) * 0.01

W_context = np.random.randn(vocab_size, embedding_dim) * 0.01

b = np.zeros(vocab_size)

b_context = np.zeros(vocab_size)


print("\nGloVe Model Parameters:")

print("W shape:", W.shape)
print("W_context shape:", W_context.shape)

print("b shape:", b.shape)
print("b_context shape:", b_context.shape)


# Step 10: Test GloVe prediction

word1 = "brown"
word2 = "quick"

id1 = word_to_id[word1]
id2 = word_to_id[word2]

prediction = (
    np.dot(W[id1], W_context[id2])
    + b[id1]
    + b_context[id2]
)

actual = np.log(cooccurrence_matrix[id1, id2])

print("\nGloVe Prediction Test:")
print(f"Word Pair: {word1} - {word2}")
print("Predicted log co-occurrence:", prediction)
print("Actual log co-occurrence:", actual)


# Step 11: GloVe loss function

def calculate_loss():

    total_loss = 0.0

    for i in range(vocab_size):
        for j in range(vocab_size):

            x = cooccurrence_matrix[i, j]

            if x == 0:
                continue

            weight = weighting_function(x)

            prediction = (
                np.dot(W[i], W_context[j])
                + b[i]
                + b_context[j]
            )

            actual = np.log(x)

            error = prediction - actual

            total_loss += weight * (error ** 2)

    return total_loss


# Step 12: Initial loss

initial_loss = calculate_loss()

print("\nInitial GloVe Loss:", initial_loss)


# Step 13: GloVe training parameters

learning_rate = 0.05
epochs = 100


# Step 14: Train GloVe model

def train_glove():

    for epoch in range(epochs):

        total_loss = 0.0

        for i in range(vocab_size):
            for j in range(vocab_size):

                x = cooccurrence_matrix[i, j]

                if x == 0:
                    continue

                weight = weighting_function(x)

                # Forward pass
                prediction = (
                    np.dot(W[i], W_context[j])
                    + b[i]
                    + b_context[j]
                )

                actual = np.log(x)

                error = prediction - actual

                # Gradient calculation
                gradient = 2 * weight * error

                grad_W = gradient * W_context[j]
                grad_W_context = gradient * W[i]

                grad_b = gradient
                grad_b_context = gradient

                # Parameter updates
                W[i] -= learning_rate * grad_W
                W_context[j] -= learning_rate * grad_W_context

                b[i] -= learning_rate * grad_b
                b_context[j] -= learning_rate * grad_b_context

                total_loss += weight * (error ** 2)

        if (epoch + 1) % 10 == 0:
            print(
                f"Epoch {epoch + 1}, "
                f"Loss: {total_loss:.4f}"
            )


# Step 15: Execute training

print("\nTraining GloVe Model:")

train_glove()

print("\nFinal GloVe Loss:", calculate_loss())


# Step 16: Extract final GloVe embeddings

embeddings = W + W_context

print("\nLearned GloVe Embeddings:")

for word in vocabulary:
    vector = embeddings[word_to_id[word]]
    print(f"{word}: {vector}")


# Step 17: Cosine similarity

def cosine_similarity(word1, word2):

    vector1 = embeddings[word_to_id[word1]]
    vector2 = embeddings[word_to_id[word2]]

    similarity = np.dot(vector1, vector2) / (
        np.linalg.norm(vector1) * np.linalg.norm(vector2)
    )

    return float(similarity)


word_pairs = [
    ("fox", "the"),
    ("quick", "brown"),
    ("dog", "lazy"),
    ("fox", "dog")
]

print("\nGloVe Cosine Similarity Results:")

for word1, word2 in word_pairs:

    score = cosine_similarity(word1, word2)

    print(f"{word1} vs {word2}: {score:.8f}")
