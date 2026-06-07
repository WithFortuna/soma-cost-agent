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
.codex/hooks/*.py
.codex/agents/*.toml
.agents/skills/cost-soma-*
.codex/cost-soma-policy-harness.json
```

기존 `.codex/hooks.json`이 있으면 timestamp 백업을 만든 뒤 `UserPromptSubmit`, `Stop` hook에 Cost SOMA hook을 병합합니다. hook command는 활성화에 사용된 Python 절대 경로를 사용합니다.

## Runtime State

target 프로젝트의 `.codex/cost-soma-policy-harness.json`에는 설치 상태가 저장됩니다.

```json
{
  "plugin_root": "/Users/team/cost-soma-policy-harness-mac",
  "document_root": "/Users/team/cost-soma-policy-harness-mac/document",
  "policy_tool": "/Users/team/cost-soma-policy-harness-mac/scripts/policy_tool.py",
  "python": "/opt/homebrew/bin/python3"
}
```

hook과 subagent 지침은 이 state file을 통해 문서와 script 위치를 찾습니다.

## Included Components

```text
.codex-plugin/plugin.json
.agents/plugins/marketplace.json
plugins/cost-soma-policy-harness-mac -> ..
skills/
scripts/
document/
hooks/
agents/
commands/
install/
tests/
README.md
WORKFLOW.md
```

MCP runtime은 포함하지 않습니다. `hooks/hooks.json`도 포함하지 않습니다. Hook은 플러그인 설치 시 전역으로 돌지 않고, activation 후 target 프로젝트의 `.codex/hooks.json`에만 기록됩니다. 정책 처리는 `scripts/policy_tool.py` -> `scripts/policy_core.py` -> `scripts/policy_engine.py` 경로로만 동작합니다.

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

## Policy CLI

```bash
python3 scripts/policy_tool.py classify --question "디자인 외주 맡기려고해"
python3 scripts/policy_tool.py form --question "맥북용 허브독 사려고함"
python3 scripts/policy_tool.py form-packet --question "구매대행 신청서 만들어줘" --category material_purchase --stage application
python3 scripts/policy_tool.py validate --question "디자인 외주 맡기려고해" --answer-file answer.md
python3 scripts/render_evidence_view.py --question "라즈베리파이와 허브 구매 가능해?"
```

모든 command는 JSON만 출력합니다.

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
