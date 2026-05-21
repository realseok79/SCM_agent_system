# scripts/train_global_m5.py
import os
import torch
import numpy as np
import logging
from torch.utils.data import TensorDataset, DataLoader
from utils.ml.tft_network import TemporalFusionTransformer, QuantileLoss

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainGlobalM5")

# Mock MLflow in case it's not installed or configured in the environment
try:
    import mlflow
    import mlflow.pytorch
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    class MockMLflow:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def log_param(self, key, value): logger.info(f"[MLflow Param] {key}: {value}")
        def log_metric(self, key, value, step=None): logger.info(f"[MLflow Metric] {key}: {value} (step={step})")
        def start_run(self, *args, **kwargs): return self
    mlflow = MockMLflow()

class TimeSeriesCrossValidator:
    """
    Time-Series Cross Validation (Rolling Window Generator)
    시간 흐름의 인과 관계(Temporal Causality)를 지키며 데이터를 Train/Validation 슬라이스로 분할합니다.
    """
    def __init__(self, lookback_window=30, horizon=7, stride=1):
        self.lookback_window = lookback_window
        self.horizon = horizon
        self.stride = stride

    def split(self, data):
        # data: NumPy array of shape [num_items, total_days]
        num_items, total_days = data.shape
        # 생성할 수 있는 총 윈도우 수 계산
        num_windows = (total_days - self.lookback_window - self.horizon) // self.stride + 1
        
        for w in range(num_windows):
            start_idx = w * self.stride
            mid_idx = start_idx + self.lookback_window
            end_idx = mid_idx + self.horizon
            
            # X: 과거 판매량 [num_items, lookback_window]
            # y: 미래 판매량 [num_items, horizon]
            X = data[:, start_idx:mid_idx]
            y = data[:, mid_idx:end_idx]
            
            # 훈련 및 검증 세트로 동적 분할 (80% Train, 20% Val)
            split_point = int(num_items * 0.8)
            yield (
                (X[:split_point], y[:split_point]),  # Train
                (X[split_point:], y[split_point:])   # Val
            )

class EarlyStopping:
    """
    Early Stopping Safeguard
    Validation Loss 향상이 멈췄을 때 훈련을 일찍 종료하여 과적합을 방지합니다.
    """
    def __init__(self, patience=3, min_delta=0.0001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float("inf")
        self.early_stop = False

    def __call__(self, val_loss):
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        return self.early_stop

def train_global_model(total_days=100, num_items=50, epochs=5, batch_size=8, lr=0.001):
    logger.info("🎬 Initializing TFT Global Model Training...")
    
    # 1. 시뮬레이션용 M5 판매량 시계열 데이터 생성 [num_items, total_days]
    np.random.seed(42)
    sales_data = np.random.poisson(lam=15.0, size=(num_items, total_days)).astype(np.float32)
    
    # 2. Time-Series CV 제너레이터 준비
    cv = TimeSeriesCrossValidator(lookback_window=30, horizon=7, stride=5)
    
    # 3. 모델, 손실 함수, 옵티마이저 선언
    # 피처는 단순 판매량 시퀀스 1개이므로 num_features=1
    model = TemporalFusionTransformer(num_features=1, d_model=16, num_heads=2, horizon=7)
    loss_fn = QuantileLoss(quantiles=[0.1, 0.5, 0.9])
    
    # Weight Decay를 정규화 항으로 포함하는 AdamW 옵티마이저 사용
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    early_stopping = EarlyStopping(patience=3)

    os.makedirs("outputs", exist_ok=True)
    
    with mlflow.start_run(run_name="TFT_Global_M5_Training") as run:
        mlflow.log_param("lookback_window", 30)
        mlflow.log_param("horizon", 7)
        mlflow.log_param("lr", lr)
        mlflow.log_param("weight_decay", 1e-4)

        # CV 폴드를 돌며 점진적 훈련 수행
        for fold, (train_data, val_data) in enumerate(cv.split(sales_data)):
            logger.info(f"🌀 Training on Fold {fold + 1}...")
            
            X_tr, y_tr = train_data
            X_val, y_val = val_data
            
            # PyTorch 텐서 캐스팅 및 DataLoader 구축
            # TFT는 [Batch, SeqLen, NumFeatures] 형태 입력을 기대하므로 Feature 차원을 마지막에 추가
            train_dataset = TensorDataset(
                torch.tensor(X_tr).unsqueeze(-1), 
                torch.tensor(y_tr)
            )
            val_dataset = TensorDataset(
                torch.tensor(X_val).unsqueeze(-1), 
                torch.tensor(y_val)
            )
            
            train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
            val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
            
            # 에포크 훈련 루프
            for epoch in range(epochs):
                model.train()
                train_loss = 0.0
                
                for batch_x, batch_y in train_loader:
                    optimizer.zero_grad()
                    out, _ = model(batch_x)
                    loss = loss_fn(out, batch_y)
                    loss.backward()
                    optimizer.step()
                    train_loss += loss.item() * batch_x.size(0)
                    
                train_loss /= len(train_loader.dataset)
                
                # Validation 평가
                model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for batch_x, batch_y in val_loader:
                        out, _ = model(batch_x)
                        loss = loss_fn(out, batch_y)
                        val_loss += loss.item() * batch_x.size(0)
                        
                val_loss /= len(val_loader.dataset)
                
                logger.info(f"Epoch {epoch+1}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
                mlflow.log_metric(f"fold_{fold}_train_loss", train_loss, step=epoch)
                mlflow.log_metric(f"fold_{fold}_val_loss", val_loss, step=epoch)
                
                # Early Stopping 체크
                if early_stopping(val_loss):
                    logger.info("🛑 Early Stopping triggered. Stopping training.")
                    break
            
            # 가중치 갱신된 전역 모델 저장
            torch.save(model.state_dict(), "outputs/global_base_model.pt")
            logger.info("💾 Saved global model check-point to outputs/global_base_model.pt")

if __name__ == "__main__":
    train_global_model()
