# 소마 프로젝트 활동비 관리 플러그인

Mac 팀 내부 배포용 플러그인입니다. 설치하고 Codex 안에서 한 번 활성화하면 해당 프로젝트에 hook, custom subagent, repo-scoped skills가 주입됩니다.

## 권장 설치법
1. GitHub repo를 Codex marketplace로 등록합니다.

```bash
codex plugin marketplace add WithFortuna/soma-cost-agent --ref main
codex plugin add cost-soma-policy-harness-mac@soma-cost-agent
```

2. Codex에서 새 thread를 엽니다.
3. Cost SOMA를 사용할 Codex 프로젝트를 엽니다.
4. Codex에 아래처럼 말합니다.

```text
이 프로젝트에 Cost SOMA 하네스 활성화해줘.
```

또는 command가 노출되는 환경에서는:

```text
/activate-harness
```

| 수동 활성화는 우측을 참고. ## 수동 플러그인 활성화
| 활성화 시에 변경사항이 궁금한 경우는 우측을 참고. ## 플러그인 활성화 시 변경 파일

활성화 스킬은 현재 프로젝트를 target으로 잡고, 내부적으로 `install/activate.py`를 실행합니다. smoke check도 자동 실행됩니다.


## [대안] 깃 클론을 이용한 설치

로컬에서 GitHub 경로 대신 현재 repo를 marketplace로 등록하려면:

```bash
codex plugin marketplace add .
codex plugin add cost-soma-policy-harness-mac@soma-cost-agent
```

플러그인 파일을 수정한 뒤 배포하려면 `.codex-plugin/plugin.json`의 `version`을 올리고 push한 다음 GitHub marketplace snapshot을 갱신합니다.

```bash
codex plugin marketplace upgrade soma-cost-agent
codex plugin add cost-soma-policy-harness-mac@soma-cost-agent
```

설치 또는 재설치 후에는 새 thread에서 테스트해야 Codex가 갱신된 plugin skills를 읽습니다.

기존에 0.3.2 이하로 프로젝트를 활성화한 사용자는 marketplace upgrade 후 해당 프로젝트에서 다시 활성화하면 됩니다. 재활성화 과정에서 예전 `policy-*` agent 파일, `user_prompt_submit.py`/`stop_policy_review.py` hook 파일, 예전 state 파일은 `cse-` 접두사 runtime으로 교체됩니다.

## 설치 제거

Codex에 아래처럼 말합니다.

```text
이 프로젝트에서 Cost SOMA 하네스 비활성화해줘.
```

또는 command가 노출되는 환경에서는:

```text
/deactivate-harness
```

## 플러그인 활성화 시 변경 파일

target 프로젝트에 아래 파일을 생성하거나 갱신합니다.

```text
.codex/hooks.json
.codex/hooks/cse-*.py
.codex/agents/cse-*.toml
.agents/skills/cost-soma-*
.codex/cse-policy-harness.json
```

기존 `.codex/hooks.json`이 있으면 timestamp 백업을 만든 뒤 `UserPromptSubmit`, `Stop` hook에 Cost SOMA hook을 병합합니다. hook/agent/state 파일명은 기존 설정과 겹치지 않도록 `cse-` 접두사를 사용합니다. 예전 버전에서 설치된 Cost SOMA runtime 파일과 hook entry는 재활성화 시 정리됩니다. hook command는 활성화에 사용된 Python 절대 경로를 사용합니다.

## 수동 플러그인 활성화

Codex 안에서 activator skill을 실행할 수 없는 환경에서는 직접 실행할 수 있습니다.

```bash
python3 install/activate.py --target /path/to/codex-project --model gpt-5.5
python3 tests/smoke_mac.py --target /path/to/codex-project
python3 install/deactivate.py --target /path/to/codex-project
```

Python 3.10 이상이 필요합니다. 부족하면 Homebrew Python을 설치한 뒤 다시 실행하세요.

```bash
brew install python
```
## Answer Shape

Cost SOMA 정책 답변은 항상 아래 섹션을 포함해야 합니다.

```text
결론
신청방법
글쓰기 포맷
유의사항
근거
```

`글쓰기 포맷`은 `policy_tool.py form`이 반환하는 `writing_format_text`를 우선 사용합니다. 확정이 필요한 항목만 선택지로 묻고, 문서와 질문에서 작성 가능한 항목은 Codex가 초안까지 씁니다.

## 제공하는 기능

1. 지원가능/불가능 여부 파악
2. 게시글 초안
3. 증빙서류,신청 서류 작성 기능
4. 원본 문서 html 뷰로 보기 기능
  사용자가 근거 문서 원문을 보고 싶어하면 Codex에 아래처럼 말합니다.
```text
근거 문서를 HTML로 보여줘.
```

  `cost-soma-evidence-viewer` skill은 관련 `document/*.md` 파일을 검색해 `outputs/cost-soma-evidence/<timestamp>/index.html`로 렌더링하고, 포함된 근거 파일과 로컬 HTML 링크를 보고합니다.

## 플러그인 사용 vs 미사용 응답 비교

```text
공통 질문: 그래픽카드, 라즈베리파이, 독허브, supabase1년 구독하려고해
```

### 1. 플러그인 사용시 응답
```text
  - 그래픽카드: 실물 그래픽카드 구매는 지원 불가. 온라인 GPU 렌탈, 예: Vast.ai류, 만 기타 사용료로 신청 가능.
  - 라즈베리파이: 재료 구매비로 신청 가능. 문서에 지원 가능 예시로 직접 나옵니다.
  - 독허브: USB/멀티허브 성격이면 재료 구매비 가능 후보. 다만 개인 노트북용 도킹스테이션/컴퓨터 부속품이면 반려 리스크가 큽니다. Docker Hub 구독을 뜻한 거라면 AI·SW 서비스 이용료 쪽으로
    따로 봐야 하고, 연간 구독은 불가합니다.

  - Supabase 1년 구독: “1년/연간 구독” 그대로는 지원 불가. 월 단위 구독 또는 선불 충전 방식으로 바꾸면 AI·SW 서비스 이용료 후보입니다.

  신청방법

  그래픽카드 온라인 렌탈: [마이페이지] → [신청/접수] → [프로젝트 활동비] → [글쓰기]에서 기타 사용료로 신청. 구매 사이트 결제 금액 화면 캡처를 첨부하고, 승인 후 결제/사용해야 합니다.

  라즈베리파이: 재료 구매비로 신청. 디바이스마트 구매 가능하면 일반구매, 디바이스마트에서 구매 불가하면 구매대행 신청서 엑셀 첨부 후 사무국 견적 확인 절차로 진행합니다.

  독허브: USB/멀티허브로 프로젝트 장치 연결·시제품 검증에 쓰는 경우 재료 구매비로 신청. 디바이스마트 일반구매 또는 구매대행 중 선택합니다.

  Supabase: 월 단위 구독 또는 선불 충전 방식으로 바꿔 AI·SW 서비스 이용료로 신청. 승인 후 개인 카드로 선결제하고 사후정산하며, 결제 직후 업체 영수증을 웹엑스로 전달해야 합니다.

  글쓰기 포맷

  그래픽카드 온라인 렌탈:
  구분: 프로젝트 활동비 → 제목: 기타 사용료(신청일) → 상세구분: 기타 → 품목명: 온라인 그래픽카드/GPU 렌탈 → 결제방식: 카드결제 또는 세금계산서 → 세부사항: 이용처, 사용 목적, 활용 내역 →
  수량 → 금액 → 구매사유: 팀 프로젝트의 모델 학습/추론 검증에 필요한 온라인 GPU 리소스 사용을 위해 신청합니다. → 첨부파일: 구매 사이트 결제 금액 화면 캡쳐 사진

  라즈베리파이:
  구분: 프로젝트 활동비 → 제목: 재료 일반구매(신청일) 또는 재료 구매대행(신청일) → 상세구분: 재료 구매비 → 품목명: 라즈베리파이 → 결제방식: 디바이스마트 → 세부사항: 디바이스마트의 정확
  한 모델명/규격 → 수량 → 금액: VAT 10% 포함 총액, 구매대행은 최초 0원 → 구매사유: 팀 프로젝트의 시제품 제작 및 기능 검증에 필요한 라즈베리파이 개발보드 구매를 신청합니다. → 첨부파일:
  구매대행인 경우 구매대행 신청서

  독허브:
  구분: 프로젝트 활동비 → 제목: 재료 일반구매(신청일) 또는 재료 구매대행(신청일) → 상세구분: 재료 구매비 → 품목명: 독허브/USB허브 → 결제방식: 디바이스마트 → 세부사항: 디바이스마트의 정
  확한 모델명/규격 → 수량 → 금액: VAT 10% 포함 총액, 구매대행은 최초 0원 → 구매사유: 팀 프로젝트 시제품 장치 연결 및 데이터 전송 테스트에 필요한 허브 구매를 신청합니다. → 첨부파일: 구매
  대행인 경우 구매대행 신청서

  Supabase 월 단위로 변경 시:
  구분: 프로젝트 활동비 → 제목: AI·SW 서비스 이용료(신청일) → 상세구분: AI·SW 서비스 이용료 → 품목명: Supabase → 결제방식: 사후정산 → 세부사항: 서비스명, 요금제, 1개월 이용 범위 → 수량
  → 금액: 1개월 단위 금액 → 달러: 해외 화폐 결제 시 달러 금액 → 구매사유: 팀 프로젝트의 데이터베이스/API 인증 및 배포 검증에 필요한 Supabase 서비스를 1개월 단위로 사용하기 위해 신청합니
  다. → 첨부파일: 구매 사이트 결제 금액 화면 캡쳐 사진

  유의사항

  승인 전 결제·주문·사용은 반려 사유입니다. 구매사유는 프로젝트 관련성이 보이게 공백 제외 30자 이상 작성해야 합니다.

  허브는 팀원당 1개, 개당 200,000원 이내(VAT 포함) 제한이 있습니다. 독허브가 개인 노트북 편의용 도킹스테이션이면 컴퓨터 및 부속품으로 판단될 수 있습니다.

  재료 구매비 증빙은 재료 구매비 증빙 내역서, 거래명세서, 제품명과 팀명이 적힌 메모가 함께 나온 실제 개봉 제품 사진이 필요합니다. 박스 사진은 불인정입니다.

  AI·SW 서비스 이용료는 공식 제공처/정식 판매처 구매만 가능하고, 증빙 내역서를 제출하지 않으면 해당 기간 개인 결제 건은 지원 대상에서 제외됩니다.

  근거

  근거 문서 시각화도 생성했습니다.

  - 라즈베리파이/허브 재료 구매비: outputs/cost-soma-evidence/material_purchase_hardware/index.html
  - 온라인 그래픽카드 렌탈: outputs/cost-soma-evidence/online_gpu_other_fee/index.html
  - Supabase 연간 구독 제한: outputs/cost-soma-evidence/ai_sw_supabase_annual/index.html

  주요 출처는 04-board-support-items.md, 03-board-activity-plan.md, 05-board-payment-methods.md, 06-board-evidence-documents.md, rules.json입니다. 문서상 라즈베리파이와 허브는 재료 구매
  비 지원 가능 예시에 있고, 그래픽카드는 온라인 렌탈만 지원되며 재료 구매비 신청은 불가합니다. AI·SW 서비스 이용료는 월 단위 구독/선불 충전 방식만 가능하고 연간 단위 구독형 서비스는 지
  원 불가로 되어 있습니다.
```


### 2. 플러그인 미사용시 응답
```text
문서 기준 결론은 이겁니다. 1년치 선결제는 하지 마세요. 특히 Docker Hub, Supabase 같은 구독형 서비스는 연간 단위 구독형
  서비스 지원 불가라서, 월 단위 결제로 신청해야 합니다.

  해야 할 일

  1. 오늘 2026년 6월 7일까지 프로젝트 활동비 활용계획서에 이 항목들을 예산 계획으로 넣어 제출하세요. 1차 사용 신청은
     2026년 6월 10일 ~ 6월 14일에 해야 하고, 그 전에 신청하면 반려됩니다.

  2. 그래픽카드
      - 실물 GPU 구매는 불가입니다. 컴퓨터 부품 GPU는 지원 불가.
      - 대신 온라인 GPU 렌탈만 가능하고, 항목은 기타 사용료입니다.
      - 예: Vast.ai 같은 온라인 GPU 렌탈.
      - 신청서: 기타 사용료(6/10), 상세구분 기타, 결제방식 카드결제 또는 세금계산서.

  3. 라즈베리파이
      - 가능. 항목은 재료 구매비.
      - 디바이스마트에서 가격 확인 후 신청하세요.
      - 디바이스마트에 없으면 재료 구매대행으로 신청.
      - 신청서: 재료 일반구매(6/10) 또는 재료 구매대행(6/10), 결제방식 디바이스마트.

  4. Docker Hub
      - 문서에 이름이 직접 나오진 않지만, 월 단위 SW 서비스로 보면 AI·SW 서비스 이용료로 신청하는 흐름이 맞습니다.
      - 1년 구독 결제는 불가, 월 단위 결제만 가능.
      - 승인 후 개인 카드로 결제하고 사후정산 받는 방식입니다.

  5. Supabase
      - 1년 구독은 불가.
      - 월 단위면 AI·SW 서비스 이용료로 신청 가능성이 있지만, Supabase는 클라우드/백엔드 서비스 성격이 있어서 사무국 확
        인을 권장합니다. 문서상 클라우드 서비스는 AWS 중심으로 안내되어 있습니다.

      - 승인받는다면 Docker Hub와 같은 방식: 승인 후 개인 결제, 매월 증빙 제출.

  정리하면 신청서는 보통 3개로 나누면 됩니다: 재료 구매비 라즈베리파이, 기타 사용료 온라인 GPU 렌탈, AI·SW 서비스 이용료
  Docker Hub/Supabase 월 구독. 모든 항목은 승인 전 결제 금지입니다.

  근거: document/00-ai-guide.md, document/02-process-and-deadlines.md, document/04-board-support-items.md, document/05-
  board-payment-methods.md, document/06-board-evidence-documents.md.
```
