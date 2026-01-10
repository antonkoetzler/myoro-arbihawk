# Setup Guide

## Prerequisites

- Python 3.10 or higher
- API-Football API key from RapidAPI

## Installation

1. **Navigate to arbihawk directory:**

   ```bash
   cd arbihawk
   ```

2. **Activate virtual environment:**

   ```bash
   # Windows
   .\venv\Scripts\Activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

## Running

`python main.py`

## Project Structure

```bash
arbihawk/
├── data/           # Data collection module
├── models/          # Prediction models
├── docs/            # Documentation
├── config.py        # Configuration
└── main.py          # Entry point
```

## Next Steps

1. Implement data collection in `data/collector.py`
2. Implement model training in `models/predictor.py`
3. Add feature engineering
4. Train and test the model
