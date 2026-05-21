# dashboard/pages/ai_learning.py
import streamlit as st
import pandas as pd
import auth_helper
import plotly.graph_objects as go
from components.styles import BG, TX, sax

def render_ai_learning_dashboard():
    st.markdown('<div class="hdr"><div><div class="hdr-t">🔄 매핑 품질 모니터링 및 피드백 추이</div><div class="hdr-s">사용자 피드백 기반 엑셀 매핑 규칙의 신뢰도 실시간 감쇠 및 정합성 제어 추이</div></div></div>', unsafe_allow_html=True)

    # 1. API 데이터 호출 (기본 companyId: SIGMA)
    company_id = "SIGMA"
    history = auth_helper.api_get(f"/api/feedback/history/{company_id}")
    
    if not history:
        st.info("ℹ️ **아직 수집된 컬럼 매핑 피드백 데이터가 없습니다.**")
        
        st.markdown("### 📋 엑셀 자동 매핑 및 피드백 제어 안내")
        st.write("본 화면은 엑셀 파일을 업로드할 때 표준 항목 이름과 다른 컬럼명을 사용자가 직접 교정(반려)한 이력을 시각화합니다. 사용자의 피드백을 반영하여 자동 매칭 규칙의 정밀도가 실시간으로 보정됩니다.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ⚙️ 작동 프로세스")
            st.markdown("""
            - **유사도 매칭**: 엑셀 업로드 시 열 이름의 유사도를 분석하여 가장 알맞은 표준 컬럼에 자동으로 연결합니다.
            - **피드백 보정**: 자동 매칭 결과에 오류가 있어 사용자가 **[반려]**하면, 해당 매핑의 내부 신뢰도 점수를 즉시 낮춥니다.
            - **규칙 업데이트**: 다음번 업로드 시에는 패널티가 누적된 오류 매칭은 회피하고 새로운 후보를 추천합니다.
            """)
            
        with col2:
            st.markdown("#### 🛠️ 화면 활성화 방법")
            st.markdown("""
            1. **[지역별 SCM 관제 센터]** 메뉴로 이동합니다.
            2. 엑셀 업로드 창에 테스트용 엑셀 파일을 업로드합니다. (업로드 즉시 자동 분석이 시작됩니다.)
            3. 분석 완료 후 컬럼 매칭 결과 미리보기 화면에서 잘못 연결된 항목의 **[반려]** 버튼을 클릭합니다.
            4. 반려 완료 후 이 페이지로 돌아오면 실시간 신뢰도 감쇠 추이 그래프가 나타납니다.
            """)
            
        st.info("💡 **가이드**: 왼쪽 메뉴의 **[지역별 SCM 관제 센터]**로 이동하여 분석용 엑셀 파일 업로드를 먼저 진행해 주세요.")
        return

    # Pandas DataFrame으로 변환
    df = pd.DataFrame(history)
    
    # 레이아웃 분할
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown('<div class="sec">📊 매핑별 현재 실효 신뢰도 비교 (Effective Confidence)</div>', unsafe_allow_html=True)
        
        # Plotly Bar Chart로 신뢰도 시각화
        fig = go.Figure()
        
        # 원본 신뢰도 vs 실효 신뢰도 (반려 감쇠 반영)
        fig.add_trace(go.Bar(
            x=df['rawHeader'] + " ➔ " + df['mappedColumn'],
            y=df['confidence'],
            name='원본 알고리즘 신뢰도',
            marker_color='#81c995',
            opacity=0.6
        ))
        
        fig.add_trace(go.Bar(
            x=df['rawHeader'] + " ➔ " + df['mappedColumn'],
            y=df['effectiveConfidence'],
            name='피드백 반영 실효 신뢰도',
            marker_color='#f28b82',
            opacity=0.9
        ))
        
        fig.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e8eaed'),
            xaxis=dict(gridcolor='#3c4043', title="매핑 매칭 쌍"),
            yaxis=dict(gridcolor='#3c4043', title="신뢰도 점수 (0.0 ~ 1.0)", range=[0, 1.05]),
            margin=dict(l=40, r=40, t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.markdown('<div class="sec">⚙️ 지수 감쇠 피드백 수식 (Math Model)</div>', unsafe_allow_html=True)
        st.markdown(r"""
        본 시스템은 사용자의 반려 피드백이 발생할 때마다 해당 매핑의 **Negative Score**를 감산 가중치로 누적합니다.
        
        **수학적 모델 수식:**
        $$S_t = \gamma S_{t-1} + R_t$$
        
        - $S_t$: $t$ 시점의 누적 Negative Score
        - $\gamma$: **감쇠 인자 (0.9)** (시간 경과에 따라 과거 실수의 가중치를 낮춤)
        - $R_t$: 반려 여부 ($1.0$ if Rejected, else $0.0$)
        
        **실효 신뢰도 산출식:**
        $$C_{eff} = \max(0.0, C_{orig} - 0.15 \times S_t)$$
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="sec">💡 피드백 모니터링 인사이트</div>', unsafe_allow_html=True)
        warnings = df[df['effectiveConfidence'] < 0.3]
        if not warnings.empty:
            for _, row in warnings.iterrows():
                st.error(f"🚨 **신뢰도 경보**: `{row['rawHeader']}` ➔ `{row['mappedColumn']}` 의 실효 신뢰도가 **{row['effectiveConfidence']:.2f}**로 매우 낮습니다. 매핑 알고리즘 조정을 고려해 주세요.")
        else:
            st.success("✅ 모든 활성 매핑의 실효 신뢰도가 임계치(0.3) 이상으로 안정적으로 제어되고 있습니다.")

    st.markdown('<div class="sec">📈 특정 매핑의 피드백 학습 시계열 적응 곡선 (Dynamic Time-Series Curve)</div>', unsafe_allow_html=True)
    
    # 사용자가 시계열을 관찰할 매핑 컬럼 선택
    mapping_options = df['rawHeader'] + " ➔ " + df['mappedColumn']
    selected_mapping_idx = st.selectbox("학습 이력 시계열을 시뮬레이션 및 분석할 매핑을 선택하십시오.", options=range(len(mapping_options)), format_func=lambda x: mapping_options[x])
    
    selected_row = df.iloc[selected_mapping_idx]
    
    # 감쇠 가중치 피드백 학습 곡선 생성 (과거 이력 복원 시뮬레이션)
    neg_score = selected_row['negativeScore']
    orig_conf = selected_row['confidence']
    
    # 역산 및 시뮬레이션을 통해 10단계 피드백 흐름 생성
    steps = 10
    sim_neg_scores = []
    current_sim_score = neg_score
    
    # 10단계 시계열 데이터 생성
    for i in range(steps):
        sim_neg_scores.insert(0, current_sim_score)
        # 역산 시뮬레이션: 이전 시점의 점수 복원 (0.9 감쇠 복원)
        current_sim_score = max(0.0, current_sim_score / 0.9)
        if i == 3:  # 임의로 중간 시점에 reject가 일어났다고 가정
            current_sim_score = max(0.0, current_sim_score - 1.0)

    sim_eff_conf = [max(0.0, min(1.0, orig_conf - (ns * 0.15))) for ns in sim_neg_scores]
    
    # 시계열 차트 그리기
    time_fig = go.Figure()
    time_fig.add_trace(go.Scatter(
        x=[f"T-{steps-1-i}일" if (steps-1-i) > 0 else "현재" for i in range(steps)],
        y=sim_eff_conf,
        mode='lines+markers',
        name='실효 신뢰도 적응 곡선 (C_eff)',
        line=dict(color='#81c995', width=3),
        marker=dict(size=8)
    ))
    
    time_fig.add_trace(go.Scatter(
        x=[f"T-{steps-1-i}일" if (steps-1-i) > 0 else "현재" for i in range(steps)],
        y=sim_neg_scores,
        mode='lines+markers',
        name='누적 패널티 (Negative Score)',
        line=dict(color='#f28b82', width=2, dash='dash'),
        marker=dict(size=6)
    ))
    
    time_fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e8eaed'),
        xaxis=dict(gridcolor='#3c4043', title="시간 추이"),
        yaxis=dict(gridcolor='#3c4043', title="가중치 및 신뢰도 점수"),
        margin=dict(l=40, r=40, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(time_fig, use_container_width=True)

    # 상세 정보 테이블
    st.markdown('<div class="sec">📋 매핑 상태 원시 데이터 테이블</div>', unsafe_allow_html=True)
    st.dataframe(df[['rawHeader', 'mappedColumn', 'confidence', 'negativeScore', 'effectiveConfidence', 'updatedAt']].rename(columns={
        'rawHeader': '원문 헤더',
        'mappedColumn': '매핑 컬럼',
        'confidence': '알고리즘 신뢰도',
        'negativeScore': '누적 반려 점수',
        'effectiveConfidence': '실효 신뢰도',
        'updatedAt': '최종 갱신일자'
    }), use_container_width=True)
