# scripts/export_onnx.py
import os
import sys
import torch

# 상위 디렉토리(scm-agent-system)를 Python Path에 추가하여 utils 모듈을 찾을 수 있도록 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ml.tft_network import TemporalFusionTransformer

def export_onnx(model_path="outputs/global_base_model.pt", onnx_path="outputs/global_base_model.onnx"):
    print("🚀 Initializing Temporal Fusion Transformer for ONNX export...")
    
    # 1. 모델 아키텍처 초기화
    model = TemporalFusionTransformer(num_features=1, d_model=16, num_heads=2, horizon=7)
    
    # 2. PyTorch 가중치 로드
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
        print(f"✅ Pre-trained weights loaded successfully from: {model_path}")
    else:
        print(f"⚠️ No pre-trained model found at {model_path}. Exporting base initialized model.")
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        torch.save(model.state_dict(), model_path)
        print(f"💡 Initialized model state saved to: {model_path}")

    model.eval()
    
    # 3. 더미 입력 데이터 생성 (BatchSize=1, SeqLen=30, NumFeatures=1)
    dummy_input = torch.randn(1, 30, 1, dtype=torch.float32)
    
    # 4. ONNX 내보내기 진행
    print("⚡ Exporting PyTorch model graph to ONNX...")
    os.makedirs(os.path.dirname(onnx_path), exist_ok=True)
    
    # TFT 모델은 (predictions, vsn_weights) 두 개의 텐서를 반환함
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=14,  # MultiheadAttention 및 GLU 지원을 위한 Opset 14 사용
        do_constant_folding=True,
        input_names=["input_sales"],
        output_names=["predictions", "vsn_weights"],
        dynamic_axes={
            "input_sales": {0: "batch_size"},
            "predictions": {0: "batch_size"},
            "vsn_weights": {0: "batch_size"}
        }
    )
    print(f"🎉 Model successfully compiled and exported to ONNX format: {onnx_path}")

if __name__ == "__main__":
    # 실행 경로에 따른 절대 경로 처리
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pt_path = os.path.join(base_dir, "outputs", "global_base_model.pt")
    onnx_path = os.path.join(base_dir, "outputs", "global_base_model.onnx")
    
    export_onnx(pt_path, onnx_path)
