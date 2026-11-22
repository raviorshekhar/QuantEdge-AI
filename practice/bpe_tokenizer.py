
import re
import json
from pathlib import Path


class BPETokenizer:

    def __init__(self):
        self.merge_rules = []
        self.vocabulary = {}
        self.token_vocabulary = set()
        self.token_to_id = {}
        self.id_to_token = {}
        self.trained = False

    # --------------------------------------------------
    # 1. TRAIN
    # --------------------------------------------------

    def train(self, corpus, num_merges=5):
        vocabulary = {}

        # Base characters and special tokens
        self.token_vocabulary = {
            "</w>", "<unk>", " ", "\t", "\n", "\r", "\v", "\f"
        }

        for word, frequency in corpus.items():
            symbols = tuple(list(word) + ["</w>"])

            vocabulary[symbols] = frequency
            self.token_vocabulary.update(word)

        self.merge_rules = []

        for _ in range(num_merges):

            pair_frequencies = {}

            # Calculate pair frequencies
            for symbols, frequency in vocabulary.items():

                for i in range(len(symbols) - 1):

                    pair = (symbols[i], symbols[i + 1])

                    pair_frequencies[pair] = (
                        pair_frequencies.get(pair, 0) + frequency
                    )

            if not pair_frequencies:
                break

            # Select most frequent pair
            best_pair = max(
                pair_frequencies,
                key=pair_frequencies.get
            )

            self.merge_rules.append(best_pair)

            merged_token = best_pair[0] + best_pair[1]
            self.token_vocabulary.add(merged_token)

            new_vocabulary = {}

            # Apply selected merge
            for symbols, frequency in vocabulary.items():

                merged = []
                i = 0

                while i < len(symbols):

                    if (
                        i < len(symbols) - 1
                        and symbols[i] == best_pair[0]
                        and symbols[i + 1] == best_pair[1]
                    ):

                        merged.append(merged_token)
                        i += 2

                    else:

                        merged.append(symbols[i])
                        i += 1

                new_vocabulary[tuple(merged)] = frequency

            vocabulary = new_vocabulary

        self.vocabulary = vocabulary
        self.trained = True

        self.build_token_id_mapping()

    # --------------------------------------------------
    # 2. BUILD TOKEN ID MAPPING
    # --------------------------------------------------

    def build_token_id_mapping(self):

        if not self.trained:
            raise RuntimeError("Tokenizer has not been trained")

        sorted_tokens = sorted(self.token_vocabulary)

        self.token_to_id = {
            token: token_id
            for token_id, token in enumerate(sorted_tokens)
        }

        self.id_to_token = {
            token_id: token
            for token, token_id in self.token_to_id.items()
        }

    # --------------------------------------------------
    # 3. ENCODE TEXT INTO TOKENS
    # --------------------------------------------------

    def encode(self, text):

        if not self.trained:
            raise RuntimeError("Tokenizer has not been trained")

        chunks = re.findall(r"\S+|\s+", text)

        all_tokens = []

        merge_ranks = {
            pair: rank
            for rank, pair in enumerate(self.merge_rules)
        }

        for chunk in chunks:

            # Preserve whitespace
            if chunk.isspace():
                all_tokens.extend(list(chunk))
                continue

            symbols = list(chunk) + ["</w>"]

            # Apply BPE merges according to learned ranks
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

            all_tokens.extend(symbols)

        return all_tokens

    # --------------------------------------------------
    # 4. DECODE TOKENS INTO TEXT
    # --------------------------------------------------

    def decode(self, tokens):

        text = "".join(tokens)

        return text.replace("</w>", "")

    # --------------------------------------------------
    # 5. ENCODE TEXT INTO TOKEN IDs
    # --------------------------------------------------

    def encode_to_ids(self, text):

        tokens = self.encode(text)

        unknown_id = self.token_to_id["<unk>"]

        return [
            self.token_to_id.get(token, unknown_id)
            for token in tokens
        ]

    # --------------------------------------------------
    # 6. DECODE TOKEN IDs INTO TEXT
    # --------------------------------------------------

    def decode_from_ids(self, token_ids):

        tokens = [
            self.id_to_token[token_id]
            for token_id in token_ids
        ]

        return self.decode(tokens)

    # --------------------------------------------------
    # 7. SAVE TOKENIZER
    # --------------------------------------------------

    def save(self, file_path):

        if not self.trained:
            raise RuntimeError("Tokenizer has not been trained")

        data = {
            "merge_rules": [
                list(pair) for pair in self.merge_rules
            ],

            "token_vocabulary": sorted(self.token_vocabulary),

            "vocabulary": [
                {
                    "symbols": list(symbols),
                    "frequency": frequency
                }
                for symbols, frequency in self.vocabulary.items()
            ]
        }

        file_path = Path(file_path)

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with file_path.open("w", encoding="utf-8") as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

    # --------------------------------------------------
    # 8. LOAD TOKENIZER
    # --------------------------------------------------

    @classmethod
    def load(cls, file_path):

        file_path = Path(file_path)

        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        tokenizer = cls()

        tokenizer.merge_rules = [
            tuple(pair)
            for pair in data["merge_rules"]
        ]

        tokenizer.token_vocabulary = set(
            data["token_vocabulary"]
        )

        tokenizer.vocabulary = {
            tuple(item["symbols"]): item["frequency"]
            for item in data["vocabulary"]
        }

        tokenizer.trained = True

        tokenizer.build_token_id_mapping()

        return tokenizer
