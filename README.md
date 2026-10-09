<div align="center">

# 🛡️ AI Weapon & Threat Detection System

An end-to-end, real-time computer vision system that detects weapons, separates **real threats** from **toy replicas**, and suppresses false alarms from **2D weapon prints** on clothing and posters.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![YOLO11](https://img.shields.io/badge/YOLO11-Ultralytics-00FFFF?style=for-the-badge)](https://docs.ultralytics.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

[![Stars](https://img.shields.io/github/stars/furqanzubair209-cell/ai-weapon-threat-detection?style=social)](https://github.com/furqanzubair209-cell/ai-weapon-threat-detection/stargazers)
[![Forks](https://img.shields.io/github/forks/furqanzubair209-cell/ai-weapon-threat-detection?style=social)](https://github.com/furqanzubair209-cell/ai-weapon-threat-detection/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/furqanzubair209-cell/ai-weapon-threat-detection?style=flat-square&color=blue)](https://github.com/furqanzubair209-cell/ai-weapon-threat-detection/commits)
[![Repo Size](https://img.shields.io/github/repo-size/furqanzubair209-cell/ai-weapon-threat-detection?style=flat-square&color=purple)](https://github.com/furqanzubair209-cell/ai-weapon-threat-detection)

**[Features](#-features) · [Architecture](#-architecture) · [Quick Start](#-quick-start) · [Training](#-training-pipeline) · [Project Structure](#-project-structure) · [Roadmap](#-roadmap)**

</div>

---

## 📸 Demo

<div align="center">

<!-- Replace with a screenshot or GIF of the dashboard detecting an object -->
![Dashboard demo](docs/demo.gif)

*Live dashboard with webcam feed, confidence scores, and adjustable thresholds*

</div>

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🎯 | **Real-Time Detection** | YOLO11s inference served through a low-latency FastAPI backend |
| 🔫 | **Dual-Tier Classification** | Separates **real weapons** (firearms, combat knives) from **toy weapons** (replicas) |
| 🧠 | **Hard-Negative Mining** | Trained on 2D drawings, posters, and illustrations with empty labels to cut false positives |
| 📷 | **Live Webcam Support** | Browser-based dashboard streams directly from the device camera |
| 📊 | **Confidence Metrics** | Per-detection confidence scores displayed in the UI |
| 🎚️ | **Adjustable Thresholds** | Tune sensitivity on the fly to match your deployment environment |
| 🪟 | **One-Click Launch** | `run_project.bat` starts the backend and dashboard on Windows |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A[📷 Webcam / Image Input] --> B[🌐 Web Dashboard<br/>HTML · CSS · JS]
    B -->|Frames via HTTP| C[⚡ FastAPI Backend<br/>backend.py]
    C --> D[🧠 YOLO11s Model<br/>best.pt · PyTorch]
    D --> E[🔍 OpenCV<br/>Pre/Post-processing]
    E -->|Boxes · Labels · Confidence| C
    C -->|JSON Response| B
    B --> F[🚨 Visual Alerts<br/>Real vs Toy Threat Levels]

    style D fill:#00FFFF,stroke:#0a0a0a,color:#000
    style C fill:#009688,stroke:#0a0a0a,color:#fff
    style F fill:#EE4C2C,stroke:#0a0a0a,color:#fff
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Model** | YOLO11s (Ultralytics), PyTorch |
| **Vision** | OpenCV |
| **Backend** | FastAPI, Uvicorn, Python |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Training** | Google Colab, Jupyter Notebook |

---

## 🚀 Quick Start

### Prerequisites

- Python **3.10+**
- A webcam (optional, for live detection)
- Windows is recommended for the one-click launcher; the manual steps work on any OS

### 1. Clone the repository

```bash
git clone https://github.com/furqanzubair209-cell/ai-weapon-threat-detection.git
cd ai-weapon-threat-detection
```

### 2. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 3. Run the application

**Option A: One-click (Windows)**

```bat
run_project.bat
```

**Option B: Manual**

```bash
uvicorn backend:app --host 127.0.0.1 --port 8000
```

Then open **http://127.0.0.1:8000** in your browser, allow webcam access, and start detecting.

> The trained weights (`best.pt`) are included in the repository, so the project runs immediately with no extra downloads.

---

## 🧪 Training Pipeline

The full training workflow lives in [`Weapon_Detection_System.ipynb`](Weapon_Detection_System.ipynb):

1. **Dataset curation**: collecting and organizing real weapon, toy weapon, and negative samples
2. **Hard-negative mining**: adding 2D weapon graphics (prints, posters, drawings) with empty label files so the model learns to ignore them
3. **Annotation conversion**: converting XML annotations to the YOLO format
4. **Two-stage training** with YOLO11s in PyTorch:
   - **Stage 1: Base training** for 100 epochs on the curated dataset
   - **Stage 2: Fine-tuning** for an additional 25 epochs to refine the model
5. **Export**: saving the best checkpoint as `best.pt` for deployment

---

## 📈 Results

| Metric | Value |
|---|---|
| mAP@0.5 | `TBD` |
| mAP@0.5:0.95 | `TBD` |
| Precision | `TBD` |
| Recall | `TBD` |
| Inference speed | `TBD` ms / frame |

> Fill in these values from your training run's `results.csv` or validation output.

---

## 📁 Project Structure

```text
ai-weapon-threat-detection/
├── frontend/                       # Web dashboard (HTML / CSS / JS)
├── backend.py                      # FastAPI inference server
├── best.pt                         # Fine-tuned YOLO11s weights
├── Weapon_Detection_System.ipynb   # Dataset, training, and export notebook
├── requirements.txt                # Python dependencies
├── run_project.bat                 # Windows one-click launcher
└── README.md                       # Project documentation
```

---

## 🗺️ Roadmap

- [ ] Multi-camera stream support (RTSP)
- [ ] Alert logging with timestamps and snapshots
- [ ] Export to ONNX / TensorRT for edge deployment
- [ ] Docker container for one-command setup

---

## 👨‍💻 Author

**Muhammad Furqan**: Frontend Software Engineer & Computer Science Undergraduate, Lahore, Pakistan

[![Portfolio](https://img.shields.io/badge/Portfolio-furqannewportfolio.netlify.app-000000?style=flat-square&logo=netlify&logoColor=white)](https://furqannewportfolio.netlify.app)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-muhammad--furqan-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/muhammad-furqan-228807304)
[![GitHub](https://img.shields.io/badge/GitHub-furqanzubair209--cell-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/furqanzubair209-cell)

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Feel free to open an [issue](https://github.com/furqanzubair209-cell/ai-weapon-threat-detection/issues) or submit a pull request.

---

## ⚠️ Disclaimer

This project is intended for **research, education, and security-system prototyping**. Automated detection should always be paired with human review. It is not a substitute for certified security infrastructure or law enforcement response.

---

<div align="center">

**If you found this project useful, please consider giving it a ⭐**

</div>
