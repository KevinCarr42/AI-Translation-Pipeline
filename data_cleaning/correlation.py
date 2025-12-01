import re
import numpy as np


def create_sentences(text_fr, text_en, linebreaks=True):
    if linebreaks:
        sentences_fr = [x.strip() for x in re.split(r'(?<![;,])[.?!]\s|\n\n', text_fr) if x != ""]
        sentences_en = [x.strip() for x in re.split(r'(?<![;,])[.?!]\s|\n\n', text_en) if x != ""]
    else:
        sentences_fr = [x.strip() for x in re.split(r'(?<![;,])[.?!]\s', text_fr) if x != ""]
        sentences_en = [x.strip() for x in re.split(r'(?<![;,])[.?!]\s', text_en) if x != ""]

    return sentences_fr, sentences_en


def create_similarity_matrix(sentences_fr, sentences_en, sentence_encoder, device):
    max_batch_size = 512

    embeddings_fr = sentence_encoder.encode(
        sentences_fr,
        convert_to_tensor=True,
        batch_size=min(max_batch_size, len(sentences_fr)),
        device=device
    )
    embeddings_en = sentence_encoder.encode(
        sentences_en,
        convert_to_tensor=True,
        batch_size=min(max_batch_size, len(sentences_en)),
        device=device
    )

    from sentence_transformers import util
    return util.pytorch_cos_sim(embeddings_fr, embeddings_en)


def align_sentences(similarity_matrix, device):
    threshold = 0.7
    n, m = similarity_matrix.shape

    similarity_matrix = similarity_matrix.cpu().numpy()
    weights = np.where(similarity_matrix >= threshold, similarity_matrix, 0.0)
    dp = np.zeros((n + 1, m + 1), dtype=np.float32)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score_match = dp[i - 1, j - 1] + weights[i - 1, j - 1]
            score_skip_fr = dp[i - 1, j]
            score_skip_en = dp[i, j - 1]
            dp[i, j] = np.max([score_match, score_skip_fr, score_skip_en])

    aligned_pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        current_val = dp[i, j]
        if np.isclose(current_val, dp[i - 1, j]):
            i -= 1
        elif np.isclose(current_val, dp[i, j - 1]):
            j -= 1
        else:
            similarity_score = similarity_matrix[i - 1, j - 1]
            if weights[i - 1, j - 1] > 0.0:
                aligned_pairs.append((i - 1, j - 1, float(similarity_score)))
            i -= 1
            j -= 1

    aligned_pairs.reverse()
    return aligned_pairs


def text_from_coordinates(aligned_pairs, sentences_fr, sentences_en, publication_number):
    correlated_list = []
    for i, j, similarity in aligned_pairs:
        correlated_list.append((publication_number, sentences_fr[i], sentences_en[j], round(similarity, 3)))

    return correlated_list


def correlate_and_clean_text(text_fr, text_en, publication_number, sentence_encoder, device, linebreaks=True):
    sentences_fr, sentences_en = create_sentences(text_fr, text_en, linebreaks)
    similarity_matrix = create_similarity_matrix(sentences_fr, sentences_en, sentence_encoder, device)
    aligned_pairs = align_sentences(similarity_matrix, device)

    return text_from_coordinates(aligned_pairs, sentences_fr, sentences_en, publication_number)
