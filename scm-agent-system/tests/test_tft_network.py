# tests/test_tft_network.py
import torch
import pytest
from utils.ml.tft_network import QuantileLoss, GatedResidualNetwork, VariableSelectionNetwork, TemporalFusionTransformer

def test_quantile_loss():
    loss_fn = QuantileLoss(quantiles=[0.1, 0.5, 0.9])
    
    # 3 분위수 예측
    y_pred = torch.tensor([[[10.0, 15.0, 20.0]]], dtype=torch.float32)  # [1, 1, 3]
    y_true = torch.tensor([[15.0]], dtype=torch.float32)  # [1, 1]
    
    # 오차: y_true - y_pred = [5, 0, -5]
    # pinball_0.1 = max(0.1 * 5, -0.9 * 5) = 0.5
    # pinball_0.5 = max(0.5 * 0, -0.5 * 0) = 0.0
    # pinball_0.9 = max(0.9 * -5, -0.1 * -5) = 0.5
    # 평균 손실: (0.5 + 0.0 + 0.5) / 3 = 0.3333...
    
    loss = loss_fn(y_pred, y_true)
    assert pytest.approx(loss.item(), abs=1e-4) == 0.3333

def test_gated_residual_network():
    # 2D Input
    x = torch.randn(8, 16)
    grn = GatedResidualNetwork(input_dim=16, hidden_dim=32, output_dim=16)
    out = grn(x)
    assert out.shape == (8, 16)

    # 3D Input with Context
    x_3d = torch.randn(8, 5, 16)
    context = torch.randn(8, 8)
    grn_context = GatedResidualNetwork(input_dim=16, hidden_dim=32, output_dim=24, context_dim=8)
    out_3d = grn_context(x_3d, context)
    assert out_3d.shape == (8, 5, 24)

def test_variable_selection_network():
    # 3D Input: [B, num_features, d_model]
    x = torch.randn(4, 5, 16)
    vsn = VariableSelectionNetwork(num_features=5, d_model=16)
    out, weights = vsn(x)
    assert out.shape == (4, 16)
    assert weights.shape == (4, 5, 1)

    # 4D Input: [B, L, num_features, d_model]
    x_4d = torch.randn(4, 10, 5, 16)
    out_4d, weights_4d = vsn(x_4d)
    assert out_4d.shape == (4, 10, 16)
    assert weights_4d.shape == (4, 10, 5)

def test_temporal_fusion_transformer():
    x = torch.randn(4, 30, 5)  # [Batch=4, SeqLen=30, Features=5]
    tft = TemporalFusionTransformer(num_features=5, d_model=16, num_heads=2, horizon=7)
    
    out, weights = tft(x)
    assert out.shape == (4, 7, 3)  # [Batch=4, Horizon=7, Quantiles=3]
    assert weights.shape == (4, 30, 5)
