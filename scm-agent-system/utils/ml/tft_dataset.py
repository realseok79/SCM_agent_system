import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import logging
import os

logger = logging.getLogger("TFTDataset")

def reduce_mem_usage(df):
    """
    Pandas 데이터프레임의 메모리 사용량을 최소화하기 위한 Downcasting
    (32GB System RAM 한계를 극복하기 위해 설계됨)
    """
    start_mem = df.memory_usage().sum() / 1024**2
    logger.info(f"Memory usage of dataframe is {start_mem:.2f} MB")
    
    for col in df.columns:
        col_type = df[col].dtype
        
        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)  
            else:
                # PyTorch 텐서 기본형이 float32이므로 float16 범위라도 float32로 맞춤 (성능/호환성)
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)
        else:
            df[col] = df[col].astype('category')
            
    end_mem = df.memory_usage().sum() / 1024**2
    logger.info(f"Memory usage after optimization is: {end_mem:.2f} MB")
    logger.info(f"Decreased by {100 * (start_mem - end_mem) / start_mem:.1f}%")
    
    return df

class M5Dataset(Dataset):
    """
    M5 Forecasting 데이터셋 (GPU VRAM 전송에 최적화된 형태)
    """
    def __init__(self, X, y):
        # 텐서 변환 시 pin_memory가 효율적으로 동작하도록 메모리 연속성 확보 (contiguous)
        self.X = torch.as_tensor(X, dtype=torch.float32).unsqueeze(-1).contiguous()
        self.y = torch.as_tensor(y, dtype=torch.float32).contiguous()

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

def load_m5_data(csv_path="../../data/raw/sales_train_evaluation.csv", num_items=None):
    """
    M5 CSV 데이터를 로드하여 numpy 배열 형태로 반환합니다.
    (로컬 환경에서 경로를 찾을 수 있도록 루트 경로 처리 반영)
    """
    # 현재 스크립트 실행 위치가 어디든 루트의 data/raw를 바라보도록 보정
    if not os.path.isabs(csv_path):
        # 기본적으로 scm-agent-system/ 에서 실행한다고 가정
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if base_dir.endswith("scm-agent-system"):
            base_dir = os.path.dirname(base_dir) # 한단계 더 위 (프로젝트 루트)
        csv_path = os.path.join(base_dir, csv_path.lstrip("../../"))
        
    if not os.path.exists(csv_path):
        logger.warning(f"🚨 [{csv_path}] 파일을 찾을 수 없습니다! 로컬 테스트를 위해 Poisson 분포 Mock 데이터를 생성합니다.")
        # 파일이 없을 경우 OOM 방지 및 테스트용 Mock 데이터 생성
        total_days = 1941
        n_items = num_items if num_items else 50
        np.random.seed(42)
        return np.random.poisson(lam=15.0, size=(n_items, total_days)).astype(np.float32)
        
    logger.info(f"로컬 M5 데이터 로딩 시작: {csv_path}")
    # 메모리 방어를 위해 다운캐스팅 수행 (System RAM 방어)
    df = pd.read_csv(csv_path)
    df = reduce_mem_usage(df)
    
    # "d_"로 시작하는 날짜 컬럼만 추출
    sales_cols = [c for c in df.columns if c.startswith("d_")]
    
    if num_items:
        df = df.head(num_items)
        
    # [num_items, total_days] 형태의 numpy array 반환
    sales_data = df[sales_cols].values.astype(np.float32)
    logger.info(f"✅ 데이터 로드 완료. Shape: {sales_data.shape}")
    return sales_data

def create_dataloaders(X_tr, y_tr, X_val, y_val, batch_size=64, num_workers=4):
    """
    System RAM -> GPU VRAM 통로를 최적화한 DataLoader 생성
    Ryzen 5 5600X (6코어 12스레드) 활용
    """
    train_dataset = M5Dataset(X_tr, y_tr)
    val_dataset = M5Dataset(X_val, y_val)
    
    # Windows 환경에서 num_workers > 0 이면 multiprocessing 충돌 방지를 위해 main 스크립트에서 if __name__ == "__main__": 이 보장되어야 함
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,     # GPU로의 데이터 복사 가속
        persistent_workers=True if num_workers > 0 else False
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
        persistent_workers=True if num_workers > 0 else False
    )
    
    return train_loader, val_loader
