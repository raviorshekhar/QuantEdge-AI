
from collections import Counter

corpus = {
    "low": 5,
    "lower": 2,
    "newest": 6,
    "widest": 3,
}


def initialize_vocabulary(corpus):
    vocabulary = {}

    for word, frequency in corpus.items():
        symbols = list(word) + ["</w>"]
        vocabulary[tuple(symbols)] = frequency

    return vocabulary


def get_pair_frequencies(vocabulary):
    pairs = Counter()

    for symbols, frequency in vocabulary.items():
        for i in range(len(symbols) - 1):
            pair = (symbols[i], symbols[i + 1])
            pairs[pair] += frequency

    return pairs


def merge_pair(pair, vocabulary):
    new_vocabulary = {}
    first, second = pair

    for symbols, frequency in vocabulary.items():
        merged = []
        i = 0

        while i < len(symbols):
            if (
                i < len(symbols) - 1
                and symbols[i] == first
                and symbols[i + 1] == second
            ):
                merged.append(first + second)
                i += 2
            else:
                merged.append(symbols[i])
                i += 1

        new_vocabulary[tuple(merged)] = frequency

    return new_vocabulary




def tokenize_word(word, merge_rules):
    symbols = list(word) + ["</w>"]

    merge_ranks = {
        pair: rank
        for rank, pair in enumerate(merge_rules)
    }

    while len(symbols) >= 2:
        available_pairs = [
            (symbols[i], symbols[i + 1])
            for i in range(len(symbols) - 1)
            if (symbols[i], symbols[i + 1]) in merge_ranks
        ]

        if not available_pairs:
            break

        best_pair = min(
            available_pairs,
            key=lambda pair: merge_ranks[pair]
        )

        merged = []
        i = 0

        while i < len(symbols):
            if (
                i < len(symbols) - 1
                and (symbols[i], symbols[i + 1]) == best_pair
            ):
                merged.append(best_pair[0] + best_pair[1])
                i += 2
            else:
                merged.append(symbols[i])
                i += 1

        symbols = merged

    return symbols





# Initialize vocabulary
vocabulary = initialize_vocabulary(corpus)

print("Initial vocabulary:")
for symbols, frequency in vocabulary.items():
    print(symbols, frequency)


# Training loop
merge_rules = []

for step in range(5):
    pair_frequencies = get_pair_frequencies(vocabulary)

    if not pair_frequencies:
        break

    best_pair, frequency = pair_frequencies.most_common(1)[0]

    # Store learned merge rule
    merge_rules.append(best_pair)

    vocabulary = merge_pair(best_pair, vocabulary)

    print(f"\nMerge {step + 1}: {best_pair}")
    print("Frequency:", frequency)

    for symbols, count in vocabulary.items():
        print(symbols, count)


print("\nLearned BPE Merge Rules:")
for rank, rule in enumerate(merge_rules):
    print(rank, rule)

print("\nTokenization Test:")

result = tokenize_word("lowest", merge_rules)

print("Input:", "lowest")
print("Tokens:", result)