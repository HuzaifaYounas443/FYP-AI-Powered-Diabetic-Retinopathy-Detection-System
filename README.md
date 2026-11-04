# RetinAI — Diabetic Retinopathy Detection System
**Final Year Project | University of Haripur, Department of Information Technology**
*Muhammad Huzaifa & Fahad Niaz*

---

## 📁 Project Structure

```
dr_detection/
├── app.py                    # Flask application (main entry point)
├── requirements.txt          # Python dependencies
├── instance/
│   └── dr_detection.db       # SQLite database (auto-created)
├── uploads/                  # Patient retinal images (auto-created)
├── models/                   # ← PUT YOUR .pth FILES HERE
│   ├── EfficientNet-B5_best.pth
│   └── ResNet101_best.pth
├── utils/
│   ├── db.py                 # SQLite database helpers
│   ├── predict.py            # Ensemble AI prediction engine
│   └── email_service.py      # SMTP email report sender
├── static/
│   ├── css/
│   │   ├── main.css          # Core styles (dark theme)
│   │   ├── landing.css       # Landing page styles
│   │   └── auth.css          # Auth page styles
│   └── js/
│       ├── main.js           # Shared JavaScript
│       └── scan.js           # Scan page logic
└── templates/
    ├── base.html             # Base template with topbar
    ├── landing.html          # Public landing page
    ├── auth.html             # Login / Sign-up (shared)
    ├── dashboard.html        # Doctor dashboard
    ├── scan.html             # Retinal scan upload & results
    ├── report.html           # Individual scan report
    └── history.html          # Scan history table
```

---

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.10 or newer
- pip

### 2. Create & activate virtual environment
```bash
cd dr_detection
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **GPU support:** If you have a CUDA GPU, install the CUDA-enabled torch:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
> ```

### 4. Place your trained model files
Copy your `.pth` files into the `models/` folder:

```
models/
├── EfficientNet-B5_best.pth   ← rename if different
└── ResNet101_best.pth         ← rename if different
```

If the model filenames differ, update the paths in `utils/predict.py`:
```python
MODEL_PATHS = {
    'efficientnet': 'models/YOUR_EFFICIENTNET_FILE.pth',
    'resnet101':    'models/YOUR_RESNET_FILE.pth',
}
```

> **Demo mode:** If no model files are found, the system runs in **Demo Mode** — it still works and shows results, but they are simulated (based on image brightness). A warning banner is shown.

### 5. Configure email (optional but recommended)

Set environment variables before running:

```bash
# Windows (PowerShell)
$env:SMTP_USER = "your_gmail@gmail.com"
$env:SMTP_PASS = "your_app_password"

# macOS / Linux
export SMTP_USER="your_gmail@gmail.com"
export SMTP_PASS="your_app_password"
```

> **Gmail App Password:** Go to Google Account → Security → 2-Step Verification → App Passwords. Create one for "Mail". Use that 16-character password as `SMTP_PASS`.

> **Skip email:** If not configured, the app works fine — email buttons will show an error message but won't crash.

### 6. Run the application
```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔑 Features

| Feature | Details |
|---|---|
| **Sign Up / Login** | Secure password hashing with Werkzeug |
| **Topbar Navigation** | Dashboard · New Scan · History · User menu |
| **Ensemble AI** | EfficientNet-B5 + ResNet-101 averaged predictions |
| **5-Stage DR Classification** | No DR → Mild → Moderate → Severe → Proliferative |
| **Confidence Score** | Per-class probability bars shown visually |
| **Clinical Recommendations** | Auto-generated per severity level |
| **Patient Records** | SQLite database with full scan history |
| **Email Reports** | SMTP sends HTML report to patient email |
| **Searchable History** | Filter by patient name |
| **Print Reports** | Browser print dialog from report page |
| **Dark Theme UI** | Professional medical-grade design |

---

## 🗄 Database Schema

Two tables are created automatically in `instance/dr_detection.db`:

**users** — Stores doctor accounts
```sql
id, full_name, email, password_hash, role, created_at
```

**scans** — Stores all retinal scan results
```sql
id, doctor_id, patient_name, patient_email, patient_age, patient_id,
image_path, severity_level, severity_label, confidence,
model_predictions (JSON), recommendations, created_at
```

---

## 🤖 Adding a Third Model

When your third model finishes training, add it to `utils/predict.py`:

```python
# In MODEL_PATHS
MODEL_PATHS = {
    'efficientnet': 'models/EfficientNet-B5_best.pth',
    'resnet101':    'models/ResNet101_best.pth',
    'model3':       'models/YourThirdModel_best.pth',  # ← add this
}

# Add a class definition
class YourThirdModel(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        # ... your architecture
    def forward(self, x):
        return self.backbone(x)

# In _load_models(), add loading logic similar to existing models
```

---

## 📧 Email Configuration

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port (TLS) |
| `SMTP_USER` | *(required)* | Sender email |
| `SMTP_PASS` | *(required)* | SMTP password / app password |

For Outlook / Office365, set `SMTP_HOST=smtp.office365.com`.

---

## ⚙️ Production Deployment

For production (hospital / clinic use):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Set a strong secret key:
```bash
export SECRET_KEY="your-very-long-random-secret-key-here"
```

### Docker deployment

The project includes `Dockerfile`, `docker-compose.yml`, `.dockerignore`, and
`.gitignore`. The Docker image contains the application and Python
dependencies, while model weights and patient-related runtime data are kept
outside the image.

1. Copy the trained checkpoints into the local `models/` directory:

   ```
   models/
   ├── EfficientNet-B5_best.pth
   └── ResNet101_best.pth
   ```

2. Create a `.env` file next to `docker-compose.yml`:

   ```dotenv
   DOCKER_USERNAME=your-dockerhub-username
   SECRET_KEY=replace-with-a-long-random-secret
   SMTP_USER=
   SMTP_PASS=
   ```

3. Build and start the application:

   ```powershell
   docker compose up --build -d
   ```

4. Open `http://localhost:5000`.

The Compose file mounts `models/`, `instance/`, `uploads/`, and
`static/generated/`. This means the database, uploaded images, generated
reports, and Grad-CAM images survive container replacement. If the model files
are not present, the application starts in demo mode; it does not provide real
AI predictions.

To publish the image to Docker Hub:

```powershell
docker login
docker compose build
docker push your-dockerhub-username/retinai:latest
```

On the deployment server, create the same `.env` file, place or download the
model checkpoints into `models/`, then run:

```powershell
docker compose pull
docker compose up -d
```

For a real deployment, use a persistent host or managed volume for the mounted
data directories, set a unique production `SECRET_KEY`, use HTTPS through a
reverse proxy, and disable Flask debug mode. The default container uses one
Gunicorn worker because each additional worker can load another copy of both
PyTorch models into memory.

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| Model not loading | Check file path in `utils/predict.py`; check for `model_state_dict` key |
| Email not sending | Verify `SMTP_USER`/`SMTP_PASS`; use Gmail App Password not account password |
| CUDA out of memory | Set `IMAGE_SIZE = 224` in predict.py or use CPU |
| Database locked | Delete `instance/dr_detection.db` to reset (⚠ loses all data) |
| Port 5000 in use | Run `python app.py` with `app.run(port=5001)` |

---

## 🏥 DR Severity Reference

| Level | Name | Recommended Action |
|---|---|---|
| 0 | No DR | Annual follow-up |
| 1 | Mild DR | 12-month follow-up |
| 2 | Moderate DR | 6-month follow-up + ophthalmologist referral |
| 3 | Severe DR | Urgent referral within 1 month |
| 4 | Proliferative DR | Emergency — immediate treatment required |

---

*Built with Flask · PyTorch · SQLite · Sora Font · Font Awesome*
