import json
import os
import pandas as pd
import requests
from model_utils import classifier

# CONFIGURATION
API_BASE_URL = "https://web-production-edebc.up.railway.app"
API_KEY = "dev-secret-key-12345"
FEEDBACK_FILE = "feedback_data.json"
BASE_DATA_FILE = "base_training_data.csv"

def download_cloud_feedback():
    print(f"Connecting to cloud at {API_BASE_URL}...")
    headers = {"X-API-Key": API_KEY}
    try:
        response = requests.get(f"{API_BASE_URL}/export_feedback", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data:
                with open(FEEDBACK_FILE, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"Downloaded {len(data)} feedback entries from cloud.")
                return True
            else:
                print("Cloud feedback is empty.")
        else:
            print(f"Failed to connect: {response.status_code}")
    except Exception as e:
        print(f"Error connecting to cloud: {e}")
    return False

def retrain_model():
    print("--- Retraining Pipeline Started ---")
    
    # 1. Sync data from Cloud
    if not download_cloud_feedback():
        if not os.path.exists(FEEDBACK_FILE):
            print("No local or cloud feedback data found. Skipping retraining.")
            return

    # 2. Load Feedback
    with open(FEEDBACK_FILE, "r") as f:
        feedback_data = json.load(f)

    df_feedback = pd.DataFrame(feedback_data)
    
    # 3. Combine with Base Data
    if os.path.exists(BASE_DATA_FILE):
        df_base = pd.read_csv(BASE_DATA_FILE)
        df_combined = pd.concat([df_base, df_feedback], ignore_index=True)
    else:
        df_combined = df_feedback

    # 4. Train
    print(f"Retraining Model on {len(df_combined)} total examples...")
    classifier.train(df_combined['text'], df_combined['label'])
    
    # 5. Save Progress
    df_combined.to_csv(BASE_DATA_FILE, index=False)
    print("--- Retraining Complete. Model Updated locally. ---")
    print("ACTION REQUIRED: Push 'spam_model.joblib' and 'base_training_data.csv' to GitHub to update production AI.")

if __name__ == "__main__":
    retrain_model()
