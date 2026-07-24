"""감성 다이어리 - Streamlit 진입점 (3단계: UI 디자인).

기능 로직(AI 호출/DB 저장·조회/에러 처리 흐름)은 2단계와 동일하게 유지한다.
이번 단계에서는 "따뜻한 느낌의 일기장" 컨셉으로 화면을 스타일링하고, 문구 톤을
다듬는다. `.streamlit/config.toml`의 테마(색상/폰트/모서리 둥글기)와 이 파일의
커스텀 CSS(카드형 컨테이너, 포스트잇 카드, 최근 기록 카드, 은은한 등장 애니메이션)
를 함께 사용한다.
"""

import html
from datetime import datetime

import streamlit as st

import ai_chain
import db

st.set_page_config(page_title="감성 다이어리", page_icon="📔", layout="centered")

# 앱 시작 시 DB 스키마를 준비한다. (기능 로직 변경 없음)
db.init_db()

_WEEKDAY_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def _today_header_text() -> str:
    now = datetime.now()
    return f"{now.year}년 {now.month}월 {now.day}일 {_WEEKDAY_KO[now.weekday()]}"


# ---------------------------------------------------------------------------
# 커스텀 CSS: 종이 일기장을 펼친 듯한 카드 레이아웃 + 포스트잇 피드백 카드.
# 색상 대비는 WCAG AA(4.5:1) 이상을 확인한 값만 사용한다.
# ---------------------------------------------------------------------------
_DIARY_CSS = """
<style>
:root {
  --diary-bg-app: #FAF3E8;
  --diary-bg-card: #FFFDF7;
  --diary-bg-postit: #FFF3D6;
  --diary-bg-badge: #F6D9B8;
  --diary-text-main: #4A3428;
  --diary-text-sub: #75604F;
  --diary-badge-text: #6E4A28;
  --diary-accent: #F2A488;
  --diary-accent-deep: #B5482E;
  --diary-border: #E8C9A0;
}

/* 앱 전체 배경: 은은한 크림 톤의 "책상" 배경 */
[data-testid="stAppViewContainer"] {
  background: radial-gradient(circle at 50% 0%, #FFF8EC 0%, var(--diary-bg-app) 55%);
}
[data-testid="stHeader"] {
  background: transparent;
}

/* 메인 컨텐츠를 "일기장 페이지" 카드로 */
[data-testid="stMainBlockContainer"] {
  max-width: 46rem;
  margin: 1.5rem auto 3rem auto;
  background: var(--diary-bg-card);
  border-radius: 1.75rem;
  padding: 2.5rem clamp(1.25rem, 5vw, 3rem) 3rem clamp(1.25rem, 5vw, 3rem);
  box-shadow: 0 18px 40px rgba(74, 52, 40, 0.14), 0 2px 8px rgba(74, 52, 40, 0.08);
}

/* 다이어리 헤더 */
.diary-header {
  text-align: center;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
  border-bottom: 2px dashed var(--diary-border);
}
.diary-header__eyebrow {
  font-family: "Gaegu", sans-serif;
  color: var(--diary-accent-deep);
  font-size: 1.05rem;
  margin: 0 0 0.15rem 0;
  letter-spacing: 0.04em;
}
.diary-header__title {
  font-family: "Gaegu", sans-serif;
  color: var(--diary-text-main);
  font-size: 2.2rem;
  font-weight: 700;
  margin: 0;
}
.diary-header__date {
  color: var(--diary-text-sub);
  font-size: 0.95rem;
  margin: 0.35rem 0 0 0;
}

.diary-lead {
  color: var(--diary-text-sub);
  text-align: center;
  margin-bottom: 1.5rem;
  line-height: 1.6;
}

/* 한 줄 입력: 노트 라인 느낌 */
[data-testid="stTextInput"] label p {
  font-family: "Gaegu", sans-serif;
  color: var(--diary-text-main);
  font-size: 1.05rem;
}
[data-testid="stTextInput"] input {
  font-size: 1.05rem;
  color: var(--diary-text-main);
}
[data-testid="stTextInput"] input::placeholder {
  color: var(--diary-text-sub);
  opacity: 0.75;
}

/* 버튼: 둥근 코랄 알약 버튼 */
[data-testid="stBaseButton-secondary"] {
  color: var(--diary-accent-deep);
  border-color: var(--diary-accent-deep);
}

/* 포커스 표시(키보드 접근성): 색상만이 아니라 뚜렷한 윤곽선으로 항상 보이게 */
button:focus-visible,
input:focus-visible,
[data-testid="stTextInput"] input:focus {
  outline: 3px solid var(--diary-accent-deep) !important;
  outline-offset: 2px;
}

/* 알림(성공/에러) 카드: 모서리를 둥글게, 폰트를 통일 */
[data-testid="stAlertContainer"] {
  border-radius: 1rem;
  animation: diaryFadeInUp 0.5s ease both;
}

/* 결과 영역 소제목 */
.diary-section-title {
  font-family: "Gaegu", sans-serif;
  color: var(--diary-text-main);
  font-size: 1.4rem;
  font-weight: 700;
  margin: 1.75rem 0 0.75rem 0;
}

/* 포스트잇처럼 보이는 AI 답장 카드 */
.postit-card {
  position: relative;
  background: var(--diary-bg-postit);
  border-radius: 0.25rem 1.1rem 1.1rem 1.1rem;
  padding: 1.35rem 1.6rem;
  margin-top: 0.75rem;
  box-shadow: 4px 8px 18px rgba(74, 52, 40, 0.18);
  transform: rotate(-1deg);
  animation: diaryFadeInUp 0.6s ease both;
}
.postit-card::before {
  content: "";
  position: absolute;
  top: -12px;
  left: 1.75rem;
  width: 3.2rem;
  height: 1.35rem;
  background: rgba(242, 164, 136, 0.65);
  border-radius: 2px;
  transform: rotate(-5deg);
}
.postit-card__eyebrow {
  font-family: "Gaegu", sans-serif;
  color: var(--diary-accent-deep);
  font-size: 1rem;
  margin: 0 0 0.4rem 0;
}
.postit-card__feedback {
  color: var(--diary-text-main);
  font-size: 1.05rem;
  line-height: 1.65;
  margin: 0.35rem 0 0 0;
}

/* 감정 라벨 태그 */
.emotion-badge {
  display: inline-block;
  background: var(--diary-bg-badge);
  color: var(--diary-badge-text);
  border-radius: 999px;
  padding: 0.2rem 0.85rem;
  font-size: 0.85rem;
  font-weight: 700;
}

/* 최근 기록: 지나간 다이어리 페이지 느낌의 아코디언 */
[data-testid="stExpander"] {
  background: var(--diary-bg-card);
  border: 1px solid var(--diary-border);
  border-radius: 1rem;
  margin-bottom: 0.6rem;
  box-shadow: 0 4px 10px rgba(74, 52, 40, 0.06);
}
.diary-entry-body p {
  margin: 0.2rem 0;
  color: var(--diary-text-main);
}
.diary-entry-body .label {
  color: var(--diary-text-sub);
  font-weight: 700;
  margin-right: 0.3rem;
}

@keyframes diaryFadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.postit-card { animation-name: diaryFadeInUp; }
.postit-card:not(:hover) { transform: rotate(-1deg); }

/* 사용자의 모션 감소 설정을 존중한다 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.001ms !important;
    scroll-behavior: auto !important;
  }
}
</style>
"""

st.markdown(_DIARY_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 다이어리 헤더 (오늘 날짜를 다이어리 헤더처럼 표시)
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="diary-header">
        <p class="diary-header__eyebrow">오늘의 다이어리</p>
        <h1 class="diary-header__title">감성 다이어리</h1>
        <p class="diary-header__date">{html.escape(_today_header_text())}</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="diary-lead">오늘 있었던 일을, 짧게 한 줄로 적어보세요.<br/>제가 가만히 들어볼게요.</p>',
    unsafe_allow_html=True,
)

# C2: 입력 초기화를 위해 text_input을 session_state 키에 바인딩한다.
if "diary_input" not in st.session_state:
    st.session_state["diary_input"] = ""

# 중복 제출 방지: 입력값을 바꾸지 않은 채 같은 내용을 다시 제출(빠른 연속 클릭 등)하면
# AI를 다시 호출하거나 DB에 중복 저장하지 않고, 직전 결과를 그대로 재사용한다.
# (OpenAI 응답 지연 때문에 시간 기반 디바운스는 신뢰할 수 없어, 직전에 "처리 완료된
# 내용"과의 일치 여부로만 판단한다. 입력을 바꾸거나 초기화한 뒤 다시 제출하면 정상 처리된다.)
if "_last_submission" not in st.session_state:
    st.session_state["_last_submission"] = None


def _clear_input():
    st.session_state["diary_input"] = ""


# M1: 한 줄 입력창 (단일 라인 - st.text_input)
diary_input = st.text_input(
    "오늘의 한 줄",
    key="diary_input",
    placeholder="예: 오늘은 유독 힘든 하루였어요",
)

col_submit, col_clear = st.columns([1, 1])
with col_submit:
    submitted = st.button("제출", type="primary", width="stretch")
with col_clear:
    st.button(
        "입력 초기화",
        on_click=_clear_input,
        type="secondary",
        width="stretch",
    )

# 결과 표시 영역
st.markdown('<p class="diary-section-title">오늘의 답장</p>', unsafe_allow_html=True)
if submitted:
    stripped_input = diary_input.strip()
    # M1: 빈 문자열(공백만 있는 경우 포함) 제출은 막고 AI 호출로 넘어가지 않는다.
    if not stripped_input:
        st.error("오늘 있었던 일을 한 줄로 적어주시겠어요?")
    else:
        last = st.session_state["_last_submission"]
        is_duplicate = last is not None and last["content"] == stripped_input

        if is_duplicate:
            # 빠른 연속 클릭 등으로 동일 내용이 다시 제출된 경우: AI 재호출/중복 저장 없이
            # 방금 받은 결과를 그대로 다시 보여준다.
            result = last["result"]
        else:
            # M3: 로딩 상태 표시 (톤에 맞는 문구)
            with st.spinner("오늘 하루를 가만히 들여다보는 중이에요..."):
                try:
                    result = ai_chain.get_ai_feedback(diary_input)
                except Exception:
                    # M3: 실패 시 사용자 친화적 에러 메시지, 앱은 죽지 않음
                    st.error("지금은 마음을 전하기 어려워요. 잠시 후 다시 시도해주세요.")
                    result = None
                else:
                    # S1: AI 피드백 생성 성공 시 로컬 저장
                    now = datetime.now()
                    db.insert_entry(
                        date=now.strftime("%Y-%m-%d"),
                        content=diary_input,
                        emotion_summary=result.get("emotion_summary", ""),
                        ai_feedback=result.get("ai_feedback", ""),
                        created_at=now.isoformat(),
                        emotion_label=result.get("emotion_label", ""),
                    )
                    st.session_state["_last_submission"] = {
                        "content": stripped_input,
                        "result": result,
                    }

        if result is not None:
            # M3: 성공 시 감정 요약 + 공감 메시지 표시
            emotion_label = result.get("emotion_label", "")
            emotion_summary = result.get("emotion_summary", "")
            ai_feedback = result.get("ai_feedback", "")

            if emotion_label:
                # C1: 감정 라벨 태그 표시
                st.success(f"오늘의 감정: {emotion_label} · {emotion_summary}")
            else:
                st.success(emotion_summary or "당신의 하루를 잘 들었어요.")

            # 포스트잇/편지 카드 느낌의 AI 피드백
            st.markdown(
                f"""
                <div class="postit-card">
                    <p class="postit-card__eyebrow">당신에게 보내는 답장</p>
                    <p class="postit-card__feedback">{html.escape(ai_feedback)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    st.markdown(
        '<p class="diary-lead">아직 오늘의 이야기를 듣지 못했어요. 위에 한 줄을 적어보세요.</p>',
        unsafe_allow_html=True,
    )

# 최근 기록 표시 영역 (S2) — 지나간 일기장을 넘겨보는 듯한 아코디언 목록
st.markdown('<p class="diary-section-title">지나간 하루들</p>', unsafe_allow_html=True)
recent_entries = db.get_recent_entries(limit=5)
if not recent_entries:
    st.markdown(
        '<p class="diary-lead">아직 넘겨볼 페이지가 없어요.</p>',
        unsafe_allow_html=True,
    )
else:
    for entry in recent_entries:
        label = entry.get("emotion_label")
        tag = f" · {label}" if label else ""
        expander_title = f"{entry['date']}{tag} — {entry['content']}"
        with st.expander(expander_title):
            body_parts = ['<div class="diary-entry-body">']
            if label:
                body_parts.append(
                    f'<span class="emotion-badge">{html.escape(label)}</span>'
                )
            if entry.get("emotion_summary"):
                body_parts.append(
                    '<p><span class="label">감정 요약</span>'
                    f"{html.escape(entry['emotion_summary'])}</p>"
                )
            if entry.get("ai_feedback"):
                body_parts.append(
                    '<p><span class="label">AI 피드백</span>'
                    f"{html.escape(entry['ai_feedback'])}</p>"
                )
            body_parts.append("</div>")
            st.markdown("".join(body_parts), unsafe_allow_html=True)
