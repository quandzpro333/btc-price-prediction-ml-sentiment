"""
Walk-forward cross-validation (expanding window) — dùng chung cho mọi script train
trong dự án, đảm bảo mọi model được đánh giá theo CÙNG một phương pháp luận, có thể
so sánh công bằng với nhau (xem thêm giải thích trong ml/analysis.ipynb).
"""
from typing import Iterator, Tuple
import numpy as np


def walk_forward_splits(
    n_samples: int, n_splits: int = 5, min_train_size: float = 0.3
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """
    Sinh ra các cặp (train_idx, test_idx) kiểu 'expanding window': fold sau luôn có
    tập train lớn hơn fold trước (bao gồm cả dữ liệu test của fold trước đó) — mô
    phỏng đúng cách một hệ thống thực tế được huấn luyện lại định kỳ khi có thêm dữ
    liệu mới, không bao giờ dùng dữ liệu tương lai để huấn luyện.
    """
    min_train = int(n_samples * min_train_size)
    remaining = n_samples - min_train
    fold_size = remaining // n_splits

    for i in range(n_splits):
        train_end = min_train + i * fold_size
        test_end = train_end + fold_size if i < n_splits - 1 else n_samples
        yield np.arange(0, train_end), np.arange(train_end, test_end)
