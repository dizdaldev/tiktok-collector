# TikTok Influencer Metadata Collector

Bu proje, TikTok'taki **public (herkese açık)** hesaplardan video metadatası toplar ve çıktıyı CSV + SQLite olarak kaydeder.

Öncelikli kullanım amacı: **influencer hesap analizi**.

## Önemli Not

- TikTok kullanım koşullarına ve yerel KVKK/gizlilik kurallarına uyun.
- Sadece meşru analiz/araştırma senaryolarında kullanın.
- TikTok tarafındaki değişiklikler zaman zaman akışı etkileyebilir.

## Neleri toplar?

- `video_id`
- `url`
- `author_username`
- `author_id`
- `description`
- `create_time_utc`
- `digg_count`, `comment_count`, `share_count`, `play_count`
- `source_target`
- `collected_at_utc`

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
pip install -e .
```

## Hızlı Başlangıç (Influencer odaklı)

### 1) Hesap listesini düzenle

[data/influencer_accounts.txt](data/influencer_accounts.txt) dosyasına her satıra bir kullanıcı adı yaz:

- `@` koyma
- yorum satırı için `#` kullanabilirsin

Örnek:

```text
danlabilic
reynmen
cznburak
```

### 2) Ayarları kontrol et

[config.yaml](config.yaml) içinde kritik alanlar:

- `targets.users_file`: hesap listesinin dosya yolu
- `limits.max_videos_per_target`:
	- `0` = mümkün olan tüm videolar
	- `N` = hesap başına N video
- `filters.min_videos_per_author`: minimum video sayısı eşiği
- `filters.min_median_play_count`: minimum median izlenme
- `filters.min_avg_like_count`: minimum ortalama like
- `filters.excluded_username_keywords`: kullanıcı adından eleme
- `filters.excluded_description_keywords`: içerik metninden eleme

### 3) Çalıştır

```bash
python run.py --config config.yaml
```

> Alternatif komut:
>
> ```bash
> tiktok-collect --config config.yaml
> ```

## Çıktılar

- CSV: `data/tiktok_videos.csv`
- SQLite: `data/tiktok_videos.db` (tablo: `tiktok_videos`)

## Mimari (kısa)

Toplama sırası:

1. `yt-dlp` (primary)
2. Playwright parser (fallback)

Bir hedef hesap hata verirse süreç tamamen durmaz; hesap atlanıp diğerlerine devam edilir.

## Sorun Giderme

- `Collected 0 records` görürsen:
	- hesap listesini kontrol et ([data/influencer_accounts.txt](data/influencer_accounts.txt))
	- filtreleri gevşet (`min_median_play_count`, `min_avg_like_count`)
	- [config.yaml](config.yaml) içinde `run.delay_seconds` ve `run.retries` artır
- Ağ/erişim sorunu varsa `.env` içinde proxy kullan:
	- `TIKTOK_PROXY=...`
	- `TIKTOK_USER_AGENT=...`

## Geliştirici Notu

Ana toplama akışı: [src/tiktok_collector/collector.py](src/tiktok_collector/collector.py)
