# utils/ml/tft_network.py
import torch
import torch.nn as nn
import torch.nn.functional as F

class QuantileLoss(nn.Module):
    """
    비대칭 핀볼 손실 함수 (Quantile Loss)
    확률론적 시계열 예측을 위한 분위수 손실을 효율적으로 계산합니다.
    """
    def __init__(self, quantiles=[0.1, 0.5, 0.9]):
        super().__init__()
        self.quantiles = quantiles

    def forward(self, y_pred, y_true):
        # y_pred: [Batch, Horizon, 3] (분위수 0.1, 0.5, 0.9 예측값)
        # y_true: [Batch, Horizon] 또는 [Batch, Horizon, 1]
        if y_true.dim() == 2:
            y_true = y_true.unsqueeze(-1)  # [Batch, Horizon, 1]

        losses = []
        errors = y_true - y_pred  # [Batch, Horizon, 3]

        for i, q in enumerate(self.quantiles):
            err = errors[..., i]
            # Pinball loss: max(q * error, (q - 1) * error)
            loss_q = torch.max(q * err, (q - 1) * err)
            losses.append(loss_q.unsqueeze(-1))

        # 분위수 차원을 기준으로 결합 및 평균 계산
        losses = torch.cat(losses, dim=-1)  # [Batch, Horizon, 3]
        return losses.mean()

class GatedResidualNetwork(nn.Module):
    """
    Gated Residual Network (GRN)
    GLU (Gated Linear Unit)를 활용하여 정보의 흐름을 동적으로 차단하거나 활성화합니다.
    """
    def __init__(self, input_dim, hidden_dim, output_dim, dropout=0.1, context_dim=None):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        if context_dim is not None:
            self.context_fc = nn.Linear(context_dim, hidden_dim, bias=False)
        else:
            self.context_fc = None
            
        self.elu = nn.ELU()
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.gate = nn.Linear(hidden_dim, output_dim * 2)  # GLU splits input by half
        self.skip = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()
        self.layer_norm = nn.LayerNorm(output_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, context=None):
        # x: [B, input_dim] 또는 [B, L, input_dim]
        h = self.fc1(x)
        if context is not None and self.context_fc is not None:
            # context 차원 일치를 위해 차원 매칭 수행
            if context.dim() == 2 and h.dim() == 3:
                h = h + self.context_fc(context).unsqueeze(1)
            else:
                h = h + self.context_fc(context)
                
        h = self.elu(h)
        h = self.fc2(h)
        h = self.dropout(h)
        
        # PyTorch F.glu 함수를 활용하여 정보 흐름 제어 (Gating)
        gated = F.glu(self.gate(h), dim=-1)
        
        return self.layer_norm(self.skip(x) + gated)

class VariableSelectionNetwork(nn.Module):
    """
    Variable Selection Network (VSN)
    수많은 파생 시계열 피처 중 예측 성능 향상에 수학적 기여도가 높은 핵심 변수만 선택.
    """
    def __init__(self, num_features, d_model, dropout=0.1, context_dim=None):
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        
        # 각 변수별 고유 GRN 계층 정의
        self.single_grns = nn.ModuleList([
            GatedResidualNetwork(d_model, d_model, d_model, dropout=dropout, context_dim=context_dim)
            for _ in range(num_features)
        ])
        
        # 모든 피처를 결합한 평탄화 가중치 연산 GRN
        self.flattened_grn = GatedResidualNetwork(
            num_features * d_model, d_model, num_features, dropout=dropout, context_dim=context_dim
        )
        self.softmax = nn.Softmax(dim=-1)

    def forward(self, features, context=None):
        # features: [B, num_features, d_model] 또는 [B, L, num_features, d_model]
        shape = features.shape
        if len(shape) == 4:
            batch, seq_len, num_features, d_model = shape
            x = features.view(batch * seq_len, num_features, d_model)
        else:
            batch, num_features, d_model = shape
            seq_len = 1
            x = features

        # 1. 각 개별 피처의 GRN 순전파 수행
        var_outputs = []
        for i in range(self.num_features):
            var_outputs.append(self.single_grns[i](x[:, i, :], context))
            
        var_outputs = torch.stack(var_outputs, dim=1)  # [B * L, num_features, d_model]

        # 2. 모든 피처를 펼쳐 피처 중요도 가중치 산출
        flat_x = x.view(x.shape[0], -1)  # [B * L, num_features * d_model]
        weights = self.flattened_grn(flat_x, context)  # [B * L, num_features]
        weights = self.softmax(weights).unsqueeze(-1)  # [B * L, num_features, 1]

        # 3. 중요도 가중치가 반영된 최종 피처 합성
        selected_output = torch.sum(weights * var_outputs, dim=1)  # [B * L, d_model]

        if len(shape) == 4:
            selected_output = selected_output.view(batch, seq_len, d_model)
            weights = weights.view(batch, seq_len, num_features)
            
        return selected_output, weights

class TemporalFusionTransformer(nn.Module):
    """
    Temporal Fusion Transformer (TFT) 시계열 예측 네트워크
    """
    def __init__(self, num_features, d_model=64, num_heads=4, dropout=0.1, horizon=7):
        super().__init__()
        self.num_features = num_features
        self.d_model = d_model
        self.horizon = horizon

        # 피처 선형 투사 계층 (Embedding 역할)
        self.input_projection = nn.Linear(1, d_model)

        # 변수 선택 계층
        self.vsn = VariableSelectionNetwork(num_features, d_model, dropout=dropout)

        # 시간 정보 추출을 위한 LSTM 기반 인코더-디코더
        self.lstm = nn.LSTM(d_model, d_model, num_layers=1, batch_first=True, bidirectional=False)

        # 과거 특정 맥락 탐색을 위한 Multi-Head Attention
        self.attention = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        self.layer_norm = nn.LayerNorm(d_model)

        # 최종 예측 분위수 출력층 (Quantile 0.1, 0.5, 0.9)
        self.output_layer = nn.Linear(d_model, 3)

    def forward(self, x):
        # x: [Batch, SeqLen, NumFeatures]
        batch, seq_len, num_features = x.shape

        # 1. 텐서 공간 매핑 (Embedding) -> [Batch, SeqLen, NumFeatures, d_model]
        x_proj = self.input_projection(x.unsqueeze(-1))

        # 2. VSN 변수 기여도 필터 적용 -> [Batch, SeqLen, d_model]
        vsn_out, weights = self.vsn(x_proj)

        # 3. Temporal Processing (LSTM)
        lstm_out, _ = self.lstm(vsn_out)  # [Batch, SeqLen, d_model]

        # 4. Multi-Head Attention (Self-Attention)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        attn_out = self.layer_norm(lstm_out + attn_out)  # Residual Connection + Norm

        # 5. Horizon 기간만큼 슬라이싱 및 출력층 투사
        # 인코더/디코더 단순화 기조에 따라 가장 최근 시점의 최종 d_model 정보를 horizon 크기만큼 확장하여 사용
        last_step = attn_out[:, -1, :]  # [Batch, d_model]
        
        # Horizon 길이만큼 타겟 예측 텐서 복제 생성
        expanded = last_step.unsqueeze(1).repeat(1, self.horizon, 1)  # [Batch, Horizon, d_model]
        
        out = self.output_layer(expanded)  # [Batch, Horizon, 3]
        return out, weights
