const PptxGenJS = require('pptxgenjs');

async function main() {
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_16x9';
  pres.title = 'SCM 운영 지능화 플랫폼 최종';

  // Color palette - McKinsey style dark theme
  const C = {
    navy:    '1A2744',
    purple:  '5B5EA6',
    purpleL: '8B8DC4',
    teal:    '2EC4C4',
    white:   'FFFFFF',
    offWhite:'F0F0F8',
    gray:    '94A3B8',
    grayL:   'E8E8F0',
    darkText:'1E293B',
    cardBg:  'F7F7FC',
    green:   '10B981',
    amber:   'F59E0B',
  };

  // ─────────────────────────────────────────
  // Slide 1: Title
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };
    for (let i = 0; i < 6; i++) {
      sl.addShape(pres.shapes.LINE, { x: i * 2, y: 0, w: 0, h: 5.625, line: { color: '2A3A5C', width: 0.5 } });
    }
    sl.addShape(pres.shapes.OVAL, { x: 6.5, y: -1.5, w: 5, h: 5, fill: { color: C.purple, transparency: 80 } });
    sl.addShape(pres.shapes.OVAL, { x: 7.2, y: -0.8, w: 3.5, h: 3.5, fill: { color: C.teal, transparency: 85 } });
    
    sl.addText('Team Sigma', { x: 0.6, y: 1.0, w: 4, h: 0.4, fontSize: 13, color: C.purpleL, charSpacing: 3 });
    sl.addText('SCM 운영 지능화', { x: 0.6, y: 1.5, w: 9, h: 1.1, fontSize: 54, color: C.white, bold: true, fontFace: 'Arial Black' });
    sl.addText('플랫폼', { x: 0.6, y: 2.55, w: 9, h: 1.0, fontSize: 54, color: C.teal, bold: true, fontFace: 'Arial Black' });
    sl.addText('수요 예측 및 확률론적 재고 최적화 Multi-Agent 시스템', { x: 0.6, y: 3.7, w: 7, h: 0.5, fontSize: 16, color: C.gray, italic: true });
    
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.25, w: 10, h: 0.375, fill: { color: C.purple } });
    sl.addText('AI × 수리최적화 × 엔터프라이즈 아키텍처', { x: 0.6, y: 5.28, w: 8, h: 0.32, fontSize: 11, color: C.white });
  }

  // ─────────────────────────────────────────
  // Slide 2: AS-IS vs TO-BE
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };
    
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 4.8, h: 5.625, fill: { color: C.navy } });
    sl.addText('AS-IS', { x: 0.4, y: 0.35, w: 4, h: 0.45, fontSize: 12, color: C.purpleL, bold: true });
    sl.addText('운영 비효율의 임계점', { x: 0.4, y: 0.85, w: 4, h: 0.7, fontSize: 26, color: C.white, bold: true });
    
    const asis = [
      '엑셀 수기 취합으로 인한\n데이터 병목 및 휴먼 에러',
      '담당자 직관에 의존하는\n부정확한 발주',
      '부서별 데이터 단절로\n과잉 안전재고 축적',
      '블랙스완 대응 불가 및\nAI 환각 리스크'
    ];
    asis.forEach((item, i) => {
      sl.addShape(pres.shapes.OVAL, { x: 0.4, y: 1.75 + i * 0.92, w: 0.28, h: 0.28, fill: { color: C.purpleL } });
      sl.addText(item, { x: 0.8, y: 1.7 + i * 0.92, w: 3.7, h: 0.75, fontSize: 12, color: C.offWhite });
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 4.8, y: 0, w: 5.2, h: 5.625, fill: { color: C.offWhite } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 4.8, y: 0, w: 5.2, h: 0.08, fill: { color: C.purple } });
    sl.addText('TO-BE', { x: 5.1, y: 0.35, w: 4.5, h: 0.45, fontSize: 12, color: C.purple, bold: true });
    sl.addText('자율적 운영 지능화', { x: 5.1, y: 0.85, w: 4.6, h: 0.7, fontSize: 26, color: C.navy, bold: true });
    
    const tobe = [
      ['Zero-Click 자동화', 'AI가 비정형 문서 스키마 자동 매핑, 담당자 개입 차단'],
      ['수리 모델 기반 의사결정', 'TFT + 음이항 분포로 수요 변동성 정량화, 확률론적 최적화'],
      ['통합 워크플로우', '기업의 지능형 뇌(Brain) 구축, 내외부 데이터 포괄 방어']
    ];
    tobe.forEach(([t, d], i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.82 + i * 1.18, w: 0.06, h: 0.8, fill: { color: C.teal } });
      sl.addText(t, { x: 5.3, y: 1.82 + i * 1.18, w: 4.4, h: 0.35, fontSize: 13, color: C.navy, bold: true });
      sl.addText(d, { x: 5.3, y: 2.15 + i * 1.18, w: 4.4, h: 0.45, fontSize: 11, color: C.gray });
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 4.3, y: 2.5, w: 0.6, h: 0.08, fill: { color: C.purple } });
    sl.addText('▶', { x: 4.62, y: 2.38, w: 0.35, h: 0.35, fontSize: 14, color: C.purple });
    sl.addText('02', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 3: Data Fusion & Data Integrity (방어 1)
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.purple } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.25, w: 1.6, h: 0.35, fill: { color: C.purple } });
    sl.addText('핵심 가치 1', { x: 0.5, y: 0.25, w: 1.6, h: 0.35, fontSize: 11, color: C.white, bold: true, align: 'center' });
    sl.addText('데이터 융합 및 정합성 검증', { x: 0.5, y: 0.72, w: 9, h: 0.65, fontSize: 26, color: C.navy, bold: true });
    
    // Columns
    const cols = [
      { title: '내부 데이터 자동화', color: C.purple, items: ['Zero-Click Silent AI', '다중 시트 엑셀 스키마 자동 분석', '비정형 문서 구조화'] },
      { title: '외부 실시간 데이터 융합', color: C.teal, items: ['API 연동: GDELT, KMA,\nSpire, FRED', 'LogisticsRiskScorer', '외부 변수 통합 리스크 산출'] },
      { title: '통합 방어 체계', color: C.navy, items: ['내외부 데이터 포괄 모니터링', '블랙스완 사전 감지', '태풍, 항만 적체 즉각 대응'] }
    ];
    cols.forEach((col, i) => {
      const x = 0.5 + i * 3.17;
      sl.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w: 3.0, h: 2.6, fill: { color: C.cardBg }, line: { color: C.grayL } });
      sl.addShape(pres.shapes.RECTANGLE, { x, y: 1.5, w: 3.0, h: 0.07, fill: { color: col.color } });
      sl.addText(col.title, { x: x + 0.15, y: 1.6, w: 2.7, h: 0.4, fontSize: 12, color: col.color, bold: true });
      col.items.forEach((item, j) => {
        sl.addShape(pres.shapes.OVAL, { x: x + 0.18, y: 2.15 + j * 0.65, w: 0.1, h: 0.1, fill: { color: col.color } });
        sl.addText(item, { x: x + 0.35, y: 2.1 + j * 0.65, w: 2.5, h: 0.55, fontSize: 10, color: C.darkText });
      });
    });

    // 방어 무기 1: 데이터 정합성 명시
    sl.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 4.3, w: 9.35, h: 0.8, fill: { color: '111D36' }, line: { color: C.teal, width: 1.5 } });
    sl.addText('✔️ 데이터 정합성 검증 (Historical API Extraction)', { x: 0.7, y: 4.4, w: 8.8, h: 0.3, fontSize: 11, color: C.teal, bold: true });
    sl.addText('Kaggle 발주 데이터의 타임스탬프를 기준으로 해당 시점의 과거 KMA(날씨) 및 FRED(경제) Historical 데이터를 API로 추출·융합하여 모델 학습 및 정합성을 확보했습니다.', { x: 0.7, y: 4.7, w: 8.8, h: 0.3, fontSize: 10, color: C.white });

    sl.addText('03', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 4: Demand Forecasting & Baseline (방어 2)
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 4.6, h: 5.625, fill: { color: C.navy } });
    sl.addText('수요 예측 엔진', { x: 0.4, y: 0.4, w: 4, h: 0.45, fontSize: 12, color: C.purpleL });
    sl.addText('수리적 모델링과\n비용 최적화', { x: 0.4, y: 0.95, w: 4, h: 1.4, fontSize: 32, color: C.white, bold: true });
    
    const badges = [['TFT', 'Temporal Fusion Transformer', C.purple], ['NB', '음이항 분포 모델링', C.teal]];
    badges.forEach(([t, d, c], i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.7 + i * 0.9, w: 0.55, h: 0.45, fill: { color: c } });
      sl.addText(t, { x: 0.4, y: 2.7 + i * 0.9, w: 0.55, h: 0.45, fontSize: 11, color: C.white, bold: true, align: 'center' });
      sl.addText(d, { x: 1.05, y: 2.72 + i * 0.9, w: 3.2, h: 0.4, fontSize: 12, color: C.offWhite });
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 4.6, y: 0, w: 5.4, h: 5.625, fill: { color: '111D36' } });
    sl.addText('비용 최소화 목적 함수 (MinimizeTotalCost)', { x: 4.9, y: 0.4, w: 4.8, h: 0.4, fontSize: 13, color: C.purpleL, bold: true });
    
    sl.addShape(pres.shapes.RECTANGLE, { x: 4.9, y: 0.9, w: 4.8, h: 0.8, fill: { color: '0D1B33' }, line: { color: C.purple } });
    sl.addText('Minimize TC(Q) = 재고유지비 + 주문비 + 품절패널티', { x: 5.0, y: 1.0, w: 4.6, h: 0.3, fontSize: 11, color: C.teal, fontFace: 'Consolas' });
    sl.addText('Q_final = max(MOQ, ⌈Net_Q / Lot⌉ × Lot)', { x: 5.0, y: 1.3, w: 4.6, h: 0.3, fontSize: 11, color: C.white, fontFace: 'Consolas' });

    // 방어 무기 2: 베이스라인 명시
    sl.addShape(pres.shapes.RECTANGLE, { x: 4.9, y: 2.1, w: 4.8, h: 2.7, fill: { color: '1A2744' }, line: { color: C.amber, width: 1.5 } });
    sl.addText('✔️ 시뮬레이션 베이스라인 (Baseline 명시)', { x: 5.1, y: 2.3, w: 4.5, h: 0.3, fontSize: 12, color: C.amber, bold: true });
    
    sl.addShape(pres.shapes.OVAL, { x: 5.1, y: 2.8, w: 0.1, h: 0.1, fill: { color: C.amber } });
    sl.addText('비교군 (Control Group):', { x: 5.3, y: 2.7, w: 4.2, h: 0.3, fontSize: 11, color: C.white, bold: true });
    sl.addText('기존 발주 시스템 (6개월 단순 이동평균(MA) 및 고정 안전재고 산출 방식) 대비 당사의 TFT + 음이항 ROP 시스템 적용 결과 비교', { x: 5.3, y: 3.0, w: 4.2, h: 0.6, fontSize: 10, color: C.gray });

    sl.addShape(pres.shapes.OVAL, { x: 5.1, y: 3.7, w: 0.1, h: 0.1, fill: { color: C.amber } });
    sl.addText('단위 비용 가정 (Kaggle M5 기준):', { x: 5.3, y: 3.6, w: 4.2, h: 0.3, fontSize: 11, color: C.white, bold: true });
    sl.addText('데이터의 실제 단가를 기준으로 재고유지비(연 20%) 및 결품 패널티(단가의 1.5배)로 통제 후 최적화 연산 수행', { x: 5.3, y: 3.9, w: 4.2, h: 0.6, fontSize: 10, color: C.gray });

    sl.addText('04', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 5: XAI
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.teal } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.25, w: 1.6, h: 0.35, fill: { color: C.teal } });
    sl.addText('핵심 가치 3', { x: 0.5, y: 0.25, w: 1.6, h: 0.35, fontSize: 11, color: C.white, bold: true, align: 'center' });
    sl.addText('통제 가능한 AI (XAI)', { x: 0.5, y: 0.72, w: 9, h: 0.65, fontSize: 26, color: C.navy, bold: true });
    
    const steps = [
      { step: '1단계', title: '대수적 수리 필터', color: C.purple, items: ['MOQ 제약 및 천장 함수 적용', 'AI 환각 대수적 원천 차단'] },
      { step: '2단계', title: 'LLM Diagnoser', color: C.teal, items: ['위험 상황 자연어 알림 생성', '"조달 3.5일 지연 예상, 안전재고 15% 상향 권장"'] },
      { step: '3단계', title: '하이브리드 승인 분기', color: C.navy, items: ['일상 발주 → AUTO_APPROVED', '위험 발주 → PENDING 강제 전환', '담당자 반려 사유 자가 학습'] }
    ];
    steps.forEach((s, i) => {
      const x = 0.5 + i * 3.17;
      sl.addShape(pres.shapes.RECTANGLE, { x, y: 1.6, w: 3.0, h: 3.3, fill: { color: C.cardBg }, line: { color: C.grayL } });
      sl.addShape(pres.shapes.RECTANGLE, { x, y: 1.6, w: 3.0, h: 0.55, fill: { color: s.color } });
      sl.addText(s.step, { x: x + 0.12, y: 1.63, w: 1.2, h: 0.28, fontSize: 10, color: C.white, bold: true });
      sl.addText(s.title, { x: x + 0.12, y: 1.9, w: 2.75, h: 0.42, fontSize: 13, color: s.color, bold: true });
      s.items.forEach((item, j) => {
        sl.addShape(pres.shapes.OVAL, { x: x + 0.15, y: 2.48 + j * 0.82, w: 0.13, h: 0.13, fill: { color: s.color } });
        sl.addText(item, { x: x + 0.35, y: 2.42 + j * 0.82, w: 2.55, h: 0.65, fontSize: 11, color: C.darkText });
      });
    });

    [1.17, 4.34].forEach(ax => {
      sl.addShape(pres.shapes.RECTANGLE, { x: ax, y: 3.38, w: 0.65, h: 0.06, fill: { color: C.gray } });
      sl.addText('▶', { x: ax + 0.47, y: 3.25, w: 0.25, h: 0.28, fontSize: 13, color: C.gray });
    });
    sl.addText('05', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 6: Architecture
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: 'F8F8FC' };
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.navy } });
    sl.addText('기술 아키텍처', { x: 0.5, y: 0.22, w: 4, h: 0.5, fontSize: 26, color: C.navy, bold: true });
    sl.addText('확장성과 안정성 보장', { x: 0.5, y: 0.72, w: 5, h: 0.4, fontSize: 14, color: C.gray });
    
    // Left Box
    sl.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.25, w: 4.4, h: 3.85, fill: { color: C.navy } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.25, w: 4.4, h: 0.5, fill: { color: C.purple } });
    sl.addText('Transaction Layer', { x: 0.55, y: 1.3, w: 4.1, h: 0.4, fontSize: 14, color: C.white, bold: true });
    sl.addText('Java Spring Boot', { x: 0.6, y: 1.9, w: 4.1, h: 0.35, fontSize: 12, color: C.purpleL, bold: true });
    
    const springItems = ['엔터프라이즈 데이터 파이프라인', 'Spring Security + JWT + RBAC', 'PostgreSQL: 단일 진실 공급원 (SSOT)', 'Flyway DB 버전 관리', '배치 상태 관리 (트랜잭션 롤백)'];
    springItems.forEach((item, i) => {
      sl.addShape(pres.shapes.OVAL, { x: 0.6, y: 2.38 + i * 0.48, w: 0.12, h: 0.12, fill: { color: C.purpleL } });
      sl.addText(item, { x: 0.82, y: 2.33 + i * 0.48, w: 3.7, h: 0.42, fontSize: 11, color: C.offWhite });
    });

    // Right Box
    sl.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.25, w: 4.4, h: 3.85, fill: { color: '111D36' } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 5.2, y: 1.25, w: 4.4, h: 0.5, fill: { color: C.teal } });
    sl.addText('AI Inference & Agent Layer', { x: 5.35, y: 1.3, w: 4.1, h: 0.4, fontSize: 13, color: C.white, bold: true });
    sl.addText('Python FastAPI', { x: 5.4, y: 1.9, w: 4.0, h: 0.35, fontSize: 12, color: C.teal, bold: true });
    
    const aiItems = ['TFT 딥러닝 수요 예측 엔진', 'Multi-Agent 발주 시스템', 'Gemini LLM 리스크 판단', 'SQLite: 격리된 로컬 엣지 연산', 'Scipy/Numpy 수치 최적화'];
    aiItems.forEach((item, i) => {
      sl.addShape(pres.shapes.OVAL, { x: 5.4, y: 2.38 + i * 0.48, w: 0.12, h: 0.12, fill: { color: C.teal } });
      sl.addText(item, { x: 5.62, y: 2.33 + i * 0.48, w: 3.7, h: 0.42, fontSize: 11, color: C.offWhite });
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 4.55, y: 2.55, w: 0.5, h: 0.08, fill: { color: C.gray } });
    sl.addText('⟷', { x: 4.53, y: 2.42, w: 0.55, h: 0.35, fontSize: 18, color: C.purple, align: 'center' });
    sl.addText('Cost\nOpt', { x: 4.5, y: 2.78, w: 0.6, h: 0.4, fontSize: 9, color: C.purple, align: 'center', bold: true });
    sl.addText('06', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 7: E2E Flow & Metrics
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };
    sl.addText('프로토타입 구현도', { x: 0.5, y: 0.3, w: 9, h: 0.65, fontSize: 30, color: C.white, bold: true });
    sl.addText('E2E 프로세스 플로우', { x: 0.5, y: 0.95, w: 4, h: 0.35, fontSize: 13, color: C.purpleL });
    
    const steps = [
      { num: '1', label: '다중 시트 엑셀 무인 자동 적재', color: C.purple },
      { num: '2', label: '가상 태풍 주입 → 외부 API 리스크 스코어 급상승', color: C.teal },
      { num: '3', label: '딥러닝 예측 변동 → 수리 필터로 강제 제어', color: C.purpleL },
      { num: '4', label: '예산 초과 감지 시 PENDING 강제 전환 + LLM 위험 진단', color: C.amber }
    ];
    steps.forEach((s, i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.45 + i * 0.75, w: 0.5, h: 0.5, fill: { color: s.color } });
      sl.addText(s.num, { x: 0.5, y: 1.45 + i * 0.75, w: 0.5, h: 0.5, fontSize: 16, color: C.white, bold: true, align: 'center' });
      sl.addText(s.label, { x: 1.15, y: 1.48 + i * 0.75, w: 5.5, h: 0.45, fontSize: 13, color: C.white });
      if (i < 3) {
        sl.addShape(pres.shapes.LINE, { x: 0.75, y: 1.97 + i * 0.75, w: 0, h: 0.21, line: { color: s.color, width: 1.5 } });
      }
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 1.3, w: 3.2, h: 3.9, fill: { color: '111D36' }, line: { color: C.purple, width: 1 } });
    sl.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 1.3, w: 3.2, h: 0.45, fill: { color: C.purple } });
    sl.addText('엔터프라이즈급 검증', { x: 6.6, y: 1.33, w: 2.9, h: 0.38, fontSize: 12, color: C.white, bold: true });
    
    const metrics = [['299개', '통합 테스트 스위트 통과'], ['84.5%', '코드 커버리지 달성'], ['100%', '멱등성 보장 (서킷 브레이커)']];
    metrics.forEach(([val, label], i) => {
      sl.addText(val, { x: 6.6, y: 1.95 + i * 1.08, w: 3.0, h: 0.55, fontSize: 32, color: C.teal, bold: true });
      sl.addText(label, { x: 6.6, y: 2.48 + i * 1.08, w: 3.0, h: 0.35, fontSize: 11, color: C.gray });
    });
    sl.addText('07', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 8: Business Impact 
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };
    sl.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.08, fill: { color: C.purple } });
    sl.addText('비즈니스 임팩트 및 확장성', { x: 0.5, y: 0.22, w: 9, h: 0.6, fontSize: 28, color: C.navy, bold: true });
    
    const kpis = [
      { num: '20%↑', label: '재고 보유 비용 감축', sub: '서비스 수준 95% 유지', color: C.purple },
      { num: '<1%', label: '품절 빈도 통제', sub: '효과적 재고 관리', color: C.teal },
      { num: '74%↓', label: 'API 비용 절감', sub: '수학적 가드레일 필터링', color: C.navy }
    ];
    kpis.forEach((k, i) => {
      const x = 0.5 + i * 3.17;
      sl.addShape(pres.shapes.RECTANGLE, { x, y: 1.0, w: 3.0, h: 2.2, fill: { color: k.color }, line: { color: k.color } });
      sl.addText(k.num, { x, y: 1.1, w: 3.0, h: 1.0, fontSize: 52, color: C.white, bold: true, align: 'center', fontFace: 'Arial Black' });
      sl.addText(k.label, { x, y: 2.1, w: 3.0, h: 0.38, fontSize: 13, color: C.white, bold: true, align: 'center' });
      sl.addText(k.sub, { x, y: 2.48, w: 3.0, h: 0.3, fontSize: 10, color: C.white, align: 'center', italic: true });
    });

    sl.addText('확장성', { x: 0.5, y: 3.4, w: 2, h: 0.4, fontSize: 15, color: C.navy, bold: true });
    sl.addShape(pres.shapes.LINE, { x: 0.5, y: 3.82, w: 9, h: 0, line: { color: C.grayL, width: 1 } });
    
    const expandItems = [
      ['☁️ B2B SaaS', 'SCM 클라우드 SaaS 모델 전환 가능'],
      ['🏭 중소·중견 기업', '낮은 진입 장벽으로 즉각 도입 가능'],
      ['🌐 Multi-tenant', '아키텍처 확장 준비 완료']
    ];
    expandItems.forEach(([icon, desc], i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: 0.5 + i * 3.17, y: 3.95, w: 3.0, h: 1.3, fill: { color: C.cardBg }, line: { color: C.grayL } });
      sl.addText(icon, { x: 0.65 + i * 3.17, y: 4.02, w: 0.5, h: 0.4, fontSize: 18 });
      sl.addText(desc, { x: 1.05 + i * 3.17, y: 4.02, w: 2.2, h: 1.0, fontSize: 11, color: C.darkText, valign: 'middle' });
    });
    sl.addText('08', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 9: Conclusion
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };
    sl.addText('결론 및 요약', { x: 0.6, y: 0.35, w: 9, h: 0.65, fontSize: 30, color: C.white, bold: true });
    
    const summaryPoints = [
      { tag: '비정형 업무 파편화', before: '엑셀 수기 + 경험 의존 의사결정', after: 'AI 기반 자동화 + 수리적 최적화', color: C.purple },
      { tag: '기술 차별점', before: 'AI 판단 위임 → 오류 및 환각 리스크', after: '판단 지원 XAI + 환각 차단 수리 필터', color: C.teal },
      { tag: '구현 완성도', before: '개념 수준 프로토타입', after: '299개 테스트 · 84.5% 커버리지 · E2E 실증', color: C.amber }
    ];
    summaryPoints.forEach((p, i) => {
      sl.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.18 + i * 1.1, w: 8.8, h: 0.85, fill: { color: '0D1B33' }, line: { color: p.color, width: 1 } });
      sl.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.18 + i * 1.1, w: 0.07, h: 0.85, fill: { color: p.color } });
      sl.addText(p.tag, { x: 0.82, y: 1.2 + i * 1.1, w: 2.0, h: 0.35, fontSize: 11, color: p.color, bold: true });
      sl.addText(p.before + ' → ' + p.after, { x: 0.82, y: 1.52 + i * 1.1, w: 8.2, h: 0.38, fontSize: 12, color: C.white });
    });

    sl.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.55, w: 8.8, h: 0.75, fill: { color: C.purple } });
    sl.addText('"산업 현장의 비정형 업무를 AI가 이해·표준화·자동화하여\n생산성과 의사결정 속도를 극대화하는 운영 지능화 플랫폼"', {
      x: 0.6, y: 4.55, w: 8.8, h: 0.75, fontSize: 12, color: C.white, italic: true, align: 'center', valign: 'middle'
    });
    sl.addText('09', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  // ─────────────────────────────────────────
  // Slide 10: APPENDIX - 구현 증빙 자료 (방어 3)
  // ─────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };
    sl.addText('APPENDIX: 구현 증빙 자료 (Implementation Evidence)', { x: 0.5, y: 0.3, w: 9, h: 0.6, fontSize: 26, color: C.teal, bold: true });
    sl.addText('※ 심사위원 검증용: 실제 구동되는 299개의 테스트 코드와 마이크로서비스 간의 로그 정합성 증명', { x: 0.5, y: 0.9, w: 9, h: 0.3, fontSize: 11, color: C.gray });
    
    // Placeholder boxes for screenshots
    const placeholders = [
      { x: 0.5, label: '[캡처 1: Pytest 실행 결과]\n\n터미널에 초록색으로\n"299 passed" 글씨가 보이는\n전체 화면 캡처 삽입' },
      { x: 3.65, label: '[캡처 2: Docker Compose]\n\n백엔드, AI서버, DB 컨테이너가\n"Up" 상태인 터미널 캡처 삽입' },
      { x: 6.8, label: '[캡처 3: Data Agent 로그]\n\n더러운 엑셀 파일이 파싱되어\nJSON으로 변환되는 로그 캡처 삽입' }
    ];
    
    placeholders.forEach(p => {
       sl.addShape(pres.shapes.RECTANGLE, { x: p.x, y: 1.5, w: 2.8, h: 3.3, fill: { color: '111D36' }, line: { color: C.teal, width: 2, dashType: 'dash' } });
       sl.addText(p.label, { x: p.x, y: 1.5, w: 2.8, h: 3.3, fontSize: 11, color: C.teal, align: 'center', valign: 'middle', bold: true });
    });
    
    sl.addText('🔗 GitHub Repo: github.com/realseok79/SCM_agent_system (코드 원본 및 README.md 구조 참조)', { x: 0.5, y: 5.0, w: 9, h: 0.3, fontSize: 11, color: C.purpleL, bold: true });
    sl.addText('10', { x: 9.4, y: 5.25, w: 0.5, h: 0.3, fontSize: 11, color: C.gray });
  }

  await pres.writeFile({ fileName: '/Users/leejinseok/Desktop/scm_agent_system/SCM_운영_지능화_포트폴리오_최종.pptx' });
  console.log('Done!');
}
main().catch(console.error);
