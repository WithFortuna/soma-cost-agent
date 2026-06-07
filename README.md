# Cost SOMA Policy Harness for Mac

Mac 팀 내부 배포용 Codex beta harness입니다. 팀원이 이 repo를 clone한 뒤 자기 Codex 프로젝트에 활성화하면, Cost SOMA 활동비 질문에서 동일한 문서, 스킬, hook, subagent, script 기반 흐름을 사용합니다.

## Install

```bash
git clone <internal-url> cost-soma-policy-harness-mac
cd cost-soma-policy-harness-mac
python3 install/activate.py --target /path/to/codex-project
```

Python 3.10 이상이 필요합니다. 부족하면 Homebrew Python을 설치한 뒤 다시 실행하세요.

```bash
brew install python
```

## Uninstall

```bash
python3 install/deactivate.py --target /path/to/codex-project
```

## Smoke Test

활성화 후 target 프로젝트를 대상으로 실행합니다.

```bash
python3 tests/smoke_mac.py --target /path/to/codex-project
```

## What Gets Installed

`activate.py`는 target 프로젝트에 아래 파일을 생성하거나 갱신합니다.

```text
.codex/hooks.json
.codex/hooks/*.py
.codex/agents/*.toml
.agents/skills/cost-soma-*
.codex/cost-soma-policy-harness.json
```

기존 `.codex/hooks.json`이 있으면 timestamp 백업을 만든 뒤 `UserPromptSubmit`, `Stop` hook에 Cost SOMA hook을 병합합니다. hook command는 활성화에 사용된 `sys.executable` 절대 경로를 사용합니다.

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

MCP runtime은 포함하지 않습니다. 정책 처리는 `scripts/policy_tool.py` -> `scripts/policy_core.py` -> `scripts/policy_engine.py` 경로로만 동작합니다.

## Policy CLI

```bash
python3 scripts/policy_tool.py classify --question "디자인 외주 맡기려고해"
python3 scripts/policy_tool.py form --question "맥북용 허브독 사려고함"
python3 scripts/policy_tool.py form-packet --question "구매대행 신청서 만들어줘" --category material_purchase --stage application
python3 scripts/policy_tool.py validate --question "디자인 외주 맡기려고해" --answer-file answer.md
```

모든 command는 JSON만 출력합니다.

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

## Smoke Prompts

```text
Aws사용하러는데 뭐해야함
맥북용 허브독 사려고함
디자인 외주주려고해
```
