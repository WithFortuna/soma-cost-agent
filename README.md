# Cost SOMA Policy Harness for Mac

Mac 팀 내부 배포용 Codex beta harness입니다. 플러그인처럼 설치하고, Codex 안에서 한 번 활성화하면 해당 프로젝트에 hook, custom subagent, repo-scoped skills가 주입됩니다.

## Recommended Flow

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

활성화 스킬은 현재 프로젝트를 target으로 잡고, 내부적으로 `install/activate.py`를 실행합니다. smoke check도 자동 실행됩니다.

## Local Marketplace Test

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

## Deactivate

Codex에 아래처럼 말합니다.

```text
이 프로젝트에서 Cost SOMA 하네스 비활성화해줘.
```

또는 command가 노출되는 환경에서는:

```text
/deactivate-harness
```

## What Activation Installs

target 프로젝트에 아래 파일을 생성하거나 갱신합니다.

```text
.codex/hooks.json
.codex/hooks/cse-*.py
.codex/agents/cse-*.toml
.agents/skills/cost-soma-*
.codex/cse-policy-harness.json
```

기존 `.codex/hooks.json`이 있으면 timestamp 백업을 만든 뒤 `UserPromptSubmit`, `Stop` hook에 Cost SOMA hook을 병합합니다. hook/agent/state 파일명은 기존 설정과 겹치지 않도록 `cse-` 접두사를 사용합니다. 예전 버전에서 설치된 Cost SOMA runtime 파일과 hook entry는 재활성화 시 정리됩니다. hook command는 활성화에 사용된 Python 절대 경로를 사용합니다.

## Runtime State

target 프로젝트의 `.codex/cse-policy-harness.json`에는 설치 상태가 저장됩니다.

```json
{
  "plugin_root": "/Users/team/cost-soma-policy-harness-mac",
  "document_root": "/Users/team/cost-soma-policy-harness-mac/document",
  "policy_tool": "/Users/team/cost-soma-policy-harness-mac/scripts/policy_tool.py",
  "python": "/opt/homebrew/bin/python3"
}
```

hook과 subagent 지침은 이 state file을 통해 문서와 script 위치를 찾습니다.

## Manual Fallback

Codex 안에서 activator skill을 실행할 수 없는 환경에서는 직접 실행할 수 있습니다.

```bash
python3 install/activate.py --target /path/to/codex-project
python3 tests/smoke_mac.py --target /path/to/codex-project
python3 install/deactivate.py --target /path/to/codex-project
```

Python 3.10 이상이 필요합니다. 부족하면 Homebrew Python을 설치한 뒤 다시 실행하세요.

```bash
brew install python
```

## Evidence HTML Viewer

사용자가 근거 문서 원문을 보고 싶어하면 Codex에 아래처럼 말합니다.

```text
근거 문서를 HTML로 보여줘.
```

`cost-soma-evidence-viewer` skill은 관련 `document/*.md` 파일을 검색해 `outputs/cost-soma-evidence/<timestamp>/index.html`로 렌더링하고, 포함된 근거 파일과 로컬 HTML 링크를 보고합니다.

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

## Response Comparison Example

공통 질문:

```text
그래픽카드, 라즈베리파이, 독허브, supabase1년 구독하려고해
```

하네스 사용 응답은 복합 질문을 항목별로 분리해 `그래픽카드 온라인 렌탈`, `라즈베리파이`, `독허브/USB허브`, `Docker Hub 가능성`, `Supabase 구독`을 각각 다른 지원 항목과 리스크로 판단한다. 실물 그래픽카드는 불가, 온라인 GPU 렌탈은 기타 사용료, 라즈베리파이는 재료 구매비, USB/멀티허브는 재료 구매비 후보, Docker Hub나 Supabase 같은 서비스는 AI·SW 서비스 이용료 후보로 정리한다. `1년/연간 구독`은 불가하고 월 단위 또는 선불 충전 방식으로 바꿔야 한다는 제한도 명시한다.

하네스 미사용 응답도 큰 결론은 대체로 맞다. 실물 GPU 구매 불가, 온라인 GPU 렌탈 가능, 라즈베리파이 가능, 구독형 서비스의 연간 결제 불가, 승인 전 결제 금지는 제대로 잡는다. 다만 `독허브`를 Docker Hub로만 해석해 USB 허브/도킹스테이션 가능성을 놓치고, Supabase를 AWS 중심 클라우드 안내와 섞어 사무국 확인 권장 수준으로 낮춘다. 신청서 필드도 제목, 상세구분, 결제방식 정도만 제시되어 실제 글쓰기 화면에 바로 옮기기에는 정보가 부족하다.

| 비교 항목 | 하네스 사용 | 하네스 미사용 |
| --- | --- | --- |
| 복합 질문 분해 | 품목별로 지원 항목과 반려 리스크를 분리 | 대체로 묶어서 설명 |
| 모호한 표현 처리 | `독허브`를 USB/멀티허브, 도킹스테이션, Docker Hub 가능성으로 나눔 | Docker Hub로만 해석 |
| 신청서 작성 지원 | `구분`, `제목`, `상세구분`, `품목명`, `결제방식`, `세부사항`, `수량`, `금액`, `구매사유`, `첨부파일`까지 제시 | 일부 신청 흐름과 제목 예시만 제시 |
| 증빙/주의사항 | 증빙 내역서, 실제 개봉 제품 사진, 영수증 전달, 월 단위 결제 등 세부 조건 포함 | 승인 전 결제 금지와 월 단위 결제 중심 |
| 근거 노출 | 문서명과 evidence HTML viewer 경로까지 제공 | 근거 문서명만 나열 |

정리하면 하네스는 결론 자체보다 `항목 분리`, `모호성 처리`, `글쓰기 포맷`, `증빙`, `근거 확인`에서 차이가 난다. 미사용 응답은 빠른 요약으로는 쓸 수 있지만, 실제 신청 직전 안내로 쓰려면 하네스 응답처럼 품목별 신청 항목과 증빙 조건을 보강해야 한다.
