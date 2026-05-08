# CE322 Pattern Recognition — TikTok Project
**Denizhan İZDAL | 20210607027**

## Proje Özeti
Turkish TikTok influencer videolarının metadata'sından pattern recognition yöntemleriyle engagement sınıflandırması ve kümeleme analizi.

## Dataset
- `data/tiktok_videos.csv` — Ham dataset (55.160 video, 214 influencer)

## Notebook Çalıştırma Sırası
1. `01_data_preprocessing.ipynb` — Veri temizleme, outlier kaldırma
2. `02_feature_engineering.ipynb` — Feature extraction & label oluşturma
3. `03_supervised_classification.ipynb` — 5 model eğitimi & karşılaştırma
4. `04_unsupervised_clustering.ipynb` — K-Means, Hierarchical, Influencer clustering
5. `05_evaluation_and_results.ipynb` — Final sonuçlar & görseller

## Gereksinimler
```
pip install pandas numpy matplotlib seaborn scikit-learn scipy nbformat
```

## Özellikler (Feature Matrix)
- Temporal: posting_hour, day_of_week, month, time_gap_days
- Ratio: like_to_play, comment_to_play, share_to_play
- Text: desc_length, word_count, hashtag_density
- Log-transformed: log_digg_count, log_comment_count, log_share_count
- Categorical: author_category (one-hot)

## Modeller (Supervised)
- Logistic Regression (baseline)
- Naive Bayes
- K-Nearest Neighbors (k=7)
- SVM (RBF kernel)
- Decision Tree (max_depth=8)

## Değerlendirme Metrikleri
Accuracy, Precision, Recall, F1-macro (macro-averaged for class imbalance), Confusion Matrix

## Target Label
3-class performance label (Low / Medium / High) based on play_count quantile thresholds.
⚠️ engagement_rate is used as an INPUT feature — not the target.
