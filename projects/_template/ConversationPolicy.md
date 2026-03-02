# AI 상담/대화 권한 (Marketing Team)

이 문서는 “마케팅 팀이 단독으로 운영”하는 자동화에서 **AI가 어디까지 말/행동할 수 있는지**를 정의합니다.
모든 자동화는 이 문서를 기준으로 제한됩니다.

## 정책 (Machine-readable)
아래 블록은 콘솔/잡러너가 읽어서 강제합니다.

```justsell-policy
{
  "policy_version": 1,
  "team": "marketing",
  "mode": "DRAFT_ONLY",
  "allowed_channels": ["threads", "instagram"],
  "auto_reply": {
    "enabled": false,
    "requires_human_confirm": true
  },
  "always_escalate": [
    "환불/취소/분쟁/사기/법적 조치/고소/약관",
    "개인정보 삭제 요청, 계정/결제/인증/보안 사고",
    "가격/할인/일정/계약 조건의 확정 요구",
    "욕설/괴롭힘/혐오, 자해 암시, 성적/미성년 관련"
  ],
  "data_handling": {
    "never_request": ["주민번호", "카드번호", "비밀번호", "OTP"],
    "ok_to_request": ["회사명", "직무", "팀 규모", "사용 목적"]
  },
  "disclaimer_short": "자동 응답일 수 있어요. 가격/계약/환불 같은 확정 안내는 담당자가 확인 후 답드립니다."
}
```

## 운영 규칙 (Human)
### 1) 모드 정의
- `AUTO_REPLY_OK`: 자동 답장 허용(단, 금지/에스컬레이션 트리거 제외)
- `DRAFT_ONLY`: 초안만 생성, 발송은 사람 클릭/확인 후
- `NO_AI`: AI는 요약/분류만, 답장 문구 생성/발송 금지

현재 프로젝트 기본값은 `DRAFT_ONLY`입니다.

### 2) 허용 범위(마케팅 팀)
- SalesInfo.md 범위 내의 기능/절차/가치 설명
- FAQ 수준의 안내 + 낮은 마찰 CTA(데모/자료/링크)
- 질문 1~2개로 자격 확인(ICP) 후 담당자 연결

### 3) 금지/주의
- 없는 성과/고객/후기/인증을 만들어내지 않음
- 확정 약속(가격/할인/환불/일정/SLA/보안 보장) 금지
- 민감정보 수집 금지(필요 시 안전한 채널로 유도)
