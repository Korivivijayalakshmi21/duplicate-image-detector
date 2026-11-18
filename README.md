# DupliDetect

> **Cloud-Based Duplicate Image Detection System**  
> A professional Django web application for detecting exact and visually similar duplicate images using SHA-256 hashing and perceptual hashing (pHash).

---

## Problem Statement

Organizations and individuals accumulate thousands of images over time, leading to storage waste from duplicate and near-duplicate files. DupliDetect automatically detects these duplicates using cryptographic and perceptual hashing algorithms, helping users identify exact copies, resized versions, and visually similar images.

## Features

| Feature | Description |
|---------|-------------|
| 🔐 Authentication | Secure login/logout with CSRF protection |
| 📤 Drag-and-Drop Upload | Multi-file upload with live preview |
| 🔍 SHA-256 Detection | Exact duplicate detection via cryptographic hashing |
| 🎨 pHash Detection | Visual duplicate detection via perceptual hashing |
| 📊 Dashboard | Real-time KPI cards and Chart.js visualizations |
| 🗂️ Image Library | Searchable, filterable, sortable grid |
| 👥 Duplicate Groups | Automatic grouping of related images |
| ⚖️ Image Comparison | Side-by-side comparison with similarity scores |
| 📋 Reports | Full report with CSV export |
| 🧪 Test Suite | 12 automated test cases (TC01–TC12) |
| 🌱 Sample Data | Management command to load demo images |
| ☁️ Cloud-Ready | Abstracted storage layer for AWS S3 |

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Django 4.2 |
| Frontend | Bootstrap 5.3, Chart.js 4, Font Awesome 6 |
| Database | SQLite (dev), PostgreSQL-ready |
| Image Processing | Pillow, ImageHash |
| Hashing | hashlib SHA-256, pHash (64-bit) |
| Testing | Django TestCase, pytest-django |
| Static Files | WhiteNoise |

## Duplicate Detection Methodology

### 1. SHA-256 Exact Detection
Every uploaded image is hashed with SHA-256. If the hash already exists in the database (for the same user), the new image is classified as an **Exact Duplicate** with 100% similarity.

### 2. Perceptual Hash (pHash) Visual Detection
Each image is also hashed with perceptual hashing (pHash), which captures the visual "fingerprint" of an image at a low resolution. The **Hamming distance** between two pHashes measures how different they look:

| Hamming Distance | Classification |
|-----------------|----------------|
| 0 | Exact Duplicate (perceptual) |
| 1 – 5 | Highly Similar |
| 6 – 10 | Possible Duplicate |
| > 10 | Unique |

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Browser (Bootstrap 5)              │
└──────────────────────────┬──────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────┐
│              Django Application Layer                 │
│  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ │
│  │accounts  │ │ images  │ │dashboard │ │ reports │ │
│  └──────────┘ └────┬────┘ └──────────┘ └─────────┘ │
│               ┌────▼──────────────────┐              │
│               │    Detection Engine   │              │
│               │  hash_service.py      │              │
│               │  similarity_service.py│              │
│               │  detection_service.py │              │
│               └────────────────────── ┘              │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│          Database (SQLite / PostgreSQL)               │
│  Image | DuplicateGroup | DuplicateRelation           │
└─────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│        Storage (Local media/ → AWS S3)               │
└─────────────────────────────────────────────────────┘
```

## Database Schema

```
Image
├── id, user (FK)
├── filename, file (ImageField)
├── file_size, mime_type
├── width, height
├── sha256_hash (indexed)
├── perceptual_hash (indexed)
├── status [unique|exact_duplicate|highly_similar|possible_duplicate]
└── uploaded_at

DuplicateGroup
├── id
├── group_type [exact|similar]
└── created_at

DuplicateRelation
├── id
├── image (FK → Image)
├── duplicate_group (FK → DuplicateGroup)
├── similarity_score (0–100%)
├── detection_type [sha256|perceptual]
└── hamming_distance
```

## Installation

```bash
# 1. Clone / navigate to project
cd duplicate_image_detector

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# Edit .env and set SECRET_KEY

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create admin user
python manage.py createsuperuser

# 7. Load sample data
python manage.py load_sample_data

# 8. Start server
python manage.py runserver
```

## Quick Setup (Windows)

```batch
setup.bat
```

## Environment Variables

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3

# AWS S3 (optional, for cloud storage)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1
```

## Loading Sample Data

```bash
python manage.py load_sample_data
# Creates demo user (demo / demo1234) with 10 sample images
# Demonstrates: exact duplicates, resized versions, similar images, unique images

python manage.py load_sample_data --clear
# Clears existing images then reloads samples

python manage.py clear_images --username demo
# Removes all images for the demo user
```

## Running Tests

```bash
# Django test runner
python manage.py test tests --verbosity=2

# Or with pytest
pytest tests/ -v
```

### Test Cases

| ID | Test | Expected |
|----|------|----------|
| TC01 | Upload valid JPG | Successful upload, unique status |
| TC02 | Upload PNG | Successful upload |
| TC03 | Upload unsupported file | Validation error |
| TC04 | Upload exact duplicate | Exact duplicate detected |
| TC05 | Upload resized version | Visually similar detected |
| TC06 | Upload unique image | Unique status |
| TC07 | Search image | Matching images displayed |
| TC08 | Filter duplicates | Only duplicates shown |
| TC09 | Image comparison | Similarity score displayed |
| TC10 | Dashboard stats | Stats match database |
| TC11 | Empty upload | Validation error |
| TC12 | Unauthorized access | Redirect to login |

## Demo Flow (3–5 minutes)

1. Open `http://127.0.0.1:8000`
2. Login: `demo / demo1234`
3. View the Dashboard (stats, charts)
4. Go to **Upload Images** → drag and drop images
5. Observe exact duplicate detection (upload same image twice)
6. Observe visual duplicate detection
7. Go to **Duplicate Groups** → open a group
8. Go to **Compare Images** → select two images
9. Go to **Image Library** → search `landscape`
10. Apply filter: `Exact Duplicates`
11. Go to **Reports** → review stats → Export CSV
12. Return to Dashboard → verify updated statistics

## Screenshots

> Place screenshots in `docs/screenshots/` and link here.

## Future Enhancements

- AWS S3 / Google Cloud Storage integration
- Batch delete duplicate images
- Email digest reports
- API endpoints for programmatic access
- Configurable thresholds per user
- Video duplicate detection
- Multi-user organization support

## Known Limitations

- Large image uploads may be slow on low-end machines
- pHash similarity depends on image content; very small solid-colour images may show unexpected matches
- No real-time progress bar for large batch uploads (page submits synchronously)

## License

MIT License — Academic Project
