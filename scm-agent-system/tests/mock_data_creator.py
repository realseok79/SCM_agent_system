import os
import pandas as pd

large_files = [
    "sales_train_evaluation.csv",
    "sales_train_validation.csv",
    "sell_prices.csv",
    "sample_submission.csv",
    "calendar.csv"
]

target_dir = "tests/mock_data"
os.makedirs(target_dir, exist_ok=True)

print("--- 1. 미니 데이터셋 생성 시작 (상위 1,000행) ---")
for file_name in large_files:
    if os.path.exists(file_name):
        print(f"Processing: {file_name} ...")
        # 청크로 읽어서 상위 1000줄만 가져오거나 그냥 head(1000)를 씁니다.
        try:
            df = pd.read_csv(file_name, nrows=1000)
            target_path = os.path.join(target_dir, file_name)
            df.to_csv(target_path, index=False)
            print(f"  -> Saved mock data to {target_path} (shape: {df.shape})")
        except Exception as e:
            print(f"  ❌ Error processing {file_name}: {e}")
    else:
        print(f"  ⚠️ Warning: {file_name} does not exist in root.")

print("\n--- 2. 기존 대용량 원본 파일 삭제 시작 ---")
for file_name in large_files:
    if os.path.exists(file_name):
        try:
            os.remove(file_name)
            print(f"  -> Deleted large file: {file_name}")
        except Exception as e:
            print(f"  ❌ Error deleting {file_name}: {e}")

print("\nMock data generation and cleanup complete!")
