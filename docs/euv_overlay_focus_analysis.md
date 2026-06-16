# EUV 리소그래피 — 피치별 Focus·Overlay 민감도 분석

> 본 문서는 EUV(13.5 nm) 스캐너 환경에서 **1.8 μm vs 66 nm 피치** 패턴의  
> CRA(Chief Ray Angle) 기반 Focus-Overlay(avg_y) 민감도 차이를 이론과 공식으로 정리한 내용입니다.

---

## 1. 배경 — EUV 스캐너의 CRA

현재 양산 EUV 스캐너(ASML NXE, 0.33 NA)에서 마스크 면의 최외각 광선(Chief Ray)은 수직이 아닌 **6° 기울어진 각도**로 입사합니다.

```
         공중 ↗↗↗ (반사광)
              /
             / ← EUV 빔 (CRA = 6°)
            /
   ┌────────────────┐
   │   EUV Mask     │  ← TaN 흡수체 h ≈ 70 nm, Ru 캡 h ≈ 19 nm
   └────────────────┘
   ←  Shadow  →
      (TaN 흡수체 그림자)
```

**왜 기울어져야 하나?**  
EUV는 모든 물질에 흡수되기 때문에 투과형 빔스플리터를 쓸 수 없습니다. 조명 광학계와 반사 마스크를 구분하려면 빔을 비스듬히 입사시켜야 합니다.

---

## 2. 회절각 공식과 Bragg 공식의 유사성

### 2-1. 회절격자 공식 (Grating Equation)

$$\sin\theta_m = \frac{m\lambda}{P}$$

- $P$: 피치(격자 주기)  
- $\lambda$: 파장  
- $m$: 회절 차수(0, ±1, ±2 …)  
- $\theta_m$: $m$차 회절각 (법선 기준)

### 2-2. Bragg 반사 공식

$$2d\sin\theta_B = n\lambda \quad\Rightarrow\quad \sin\theta_B = \frac{n\lambda}{2d}$$

- $d$: 격자면 간격  
- $\theta_B$: 입사각(면 기준)

### 2-3. 왜 같은 형태인가?

두 공식 모두 **경로차 = 정수 × 파장** 조건에서 유도됩니다.

```
회절격자 (투과형):
    ─────────────────────────────────
        │         │         │
        │    P    │         │
        ↓         ↓         ↓
   경로차 = P·sinθ = mλ

Bragg (반사형):
    ─────── d ───────
    ─────── d ───────   경로차 = 2d·sinθ = nλ
```

**차이점**: 회절격자는 인접 슬릿 간 경로차($P \sin\theta$), Bragg는 인접 격자면 간 왕복 경로차($2d\sin\theta$). 인자 2 차이만 있을 뿐 구조는 동일합니다.

---

## 3. 피치별 회절각 계산 (EUV λ = 13.5 nm)

### 3-1. 1.8 μm 피치

$$\theta_1 = \arcsin\!\left(\frac{13.5\,\text{nm}}{1800\,\text{nm}}\right) = \arcsin(0.0075) \approx 0.43°$$

→ ±1차 빔이 0차에서 겨우 0.43° 떨어짐 → **0차 + ±1차 → 3빔 간섭**

### 3-2. 66 nm 피치

$$\theta_1 = \arcsin\!\left(\frac{13.5\,\text{nm}}{66\,\text{nm}}\right) = \arcsin(0.2045) \approx 11.8°$$

→ ±1차가 0차에서 11.8° 떨어짐 → 렌즈 동공(NA=0.33 기준)을 고려하면 0차 차단 가능  
→ **±1차만 통과하는 2빔(dipole) 이미징**

---

## 4. TGSPI 공식과 피치 의존성

**TGSPI** = Through-pitch Geometric Shadow Position Induced (overlay)

$$\text{TGSPI} = \frac{h_\text{abs} \cdot \tan(\text{CRA})}{4} \times \left(1 - \frac{P_\text{min}}{P}\right)$$

| 기호 | 의미 | 값 |
|------|------|----|
| $h_\text{abs}$ | 흡수체 높이 | TaN ≈ 70 nm, Ru ≈ 19 nm |
| CRA | Chief Ray Angle | 6° |
| $P_\text{min}$ | 최소 피치 ($\lambda / 2\sin\text{CRA}$) | 64.6 nm |
| $P$ | 패턴 피치 | — |

### 4-1. P_min 계산

$$P_\text{min} = \frac{\lambda}{2\sin\text{CRA}} = \frac{13.5}{2 \times \sin 6°} = \frac{13.5}{0.2090} \approx 64.6\,\text{nm}$$

### 4-2. 그림자 기준값 (shadow_base)

$$\text{shadow\_base} = \frac{h_\text{abs} \cdot \tan(\text{CRA})}{4}$$

- TaN (h = 70 nm): $\frac{70 \times \tan 6°}{4} = \frac{70 \times 0.1051}{4} \approx 1.84\,\text{nm}$  
- Ru (h = 19 nm): $\frac{19 \times 0.1051}{4} \approx 0.50\,\text{nm}$

### 4-3. 피치별 TGSPI

| 피치 | $1 - P_\text{min}/P$ | TGSPI (TaN 기준) |
|------|----------------------|-----------------|
| 1.8 μm | ≈ 1.000 | ≈ **1.84 nm** (최대) |
| 200 nm | ≈ 0.677 | ≈ 1.25 nm |
| 100 nm | ≈ 0.354 | ≈ 0.65 nm |
| 66 nm | ≈ 0.020 | ≈ **0.04 nm** (≈ 0) |

```
TGSPI
 ↑
 2 │ ████████████████████████ (TaN)
   │
   │ ════════════════════════  shadow_base
   │
 0 │                               ←66nm
   └──────────────────────────────────→ Pitch
     P_min       100nm  200nm  1800nm
```

**핵심**: 피치가 클수록 TGSPI(→ focus 민감도)가 크다. 1.8 μm는 최대, 66 nm는 거의 0.

---

## 5. 극(Extreme) Dipole 조명계에서의 P_opt

### 5-1. 기본 dipole CRA 각도

6° CRA + dipole 조명 σ_c = 0.8 (반경 기준):

$$\theta_\text{pole} = \arcsin(\sigma_c \cdot \text{NA}) = \arcsin(0.8 \times 0.33) \approx 15.36°$$

하지만 마스크 면 기준으로는 축소율 4× 반영:

$$\theta_\text{mask} \approx \arcsin\!\left(\frac{\sigma_c \cdot \text{NA}}{4}\right) \approx \arcsin(0.066) \approx 3.78°$$

극 dipole의 두 광원 각도 (마스크 면):

$$\theta_+ = \text{CRA} + \theta_\text{pole} = 6° + 3.78° = 9.78°$$
$$\theta_- = \text{CRA} - \theta_\text{pole} = 6° - 3.78° = 2.22°$$

### 5-2. 각 광원의 P_min

$$P_{\min,+} = \frac{\lambda}{2\sin\theta_+} = \frac{13.5}{2\sin 9.78°} = \frac{13.5}{0.3397} \approx 39.7\,\text{nm}$$

$$P_{\min,-} = \frac{\lambda}{2\sin\theta_-} = \frac{13.5}{2\sin 2.22°} = \frac{13.5}{0.0774} \approx 174.4\,\text{nm}$$

### 5-3. 그림자 가중 P_opt

각 광원의 그림자 크기는 $\tan\theta$에 비례하므로:

$$w_+ = \tan 9.78° \approx 0.172, \quad w_- = \tan 2.22° \approx 0.0388$$

가중 평균:

$$P_\text{opt} = \frac{w_+ \cdot P_{\min,+} + w_- \cdot P_{\min,-}}{w_+ + w_-}$$
$$= \frac{0.172 \times 39.7 + 0.0388 \times 174.4}{0.172 + 0.0388}$$
$$= \frac{6.83 + 6.77}{0.2108} \approx \frac{13.6}{0.2108} \approx 64.5\,\text{nm}$$

→ **극 dipole σ_c=0.8 에서도 P_opt ≈ 64 nm** (일반 CRA=6° P_min과 거의 동일)

---

## 6. 3빔 vs 2빔 이미징 — 어린이도 이해하는 설명

### 6-1. 비유: 시소와 손전등

```
         태양(0차광, CRA 기울어짐)
              \
               \  ↘  (CRA=6°)
    ─────────────────────────── ← 마스크
                │
    ───────────시소────────────
         왼쪽    ↕    오른쪽
       (−1차)  중심  (+1차)
```

**1.8 μm (3빔)**: 시소 중심(0차)이 기울어진 채로 서 있음 → 시소가 한쪽으로 내려앉음 → **위치 오류(overlay)**

**66 nm (2빔)**: 0차 광이 렌즈 밖으로 나가고, ±1차만 들어옴 → 시소 중심이 없음 → 두 팔이 균형을 맞추려 함 → **기울기 효과 상쇄**

### 6-2. 그림자 비유

```
        손전등 ↗↗↗ (기울어진 CRA)
               /
              /
   ┌─────────┐
   │  흡수체  │ h=70nm
   └─────────┘
      ←그림자→
```

피치가 크면(1.8 μm) → 그림자가 패턴 폭의 큰 비율 차지 → **평균 위치(avg_y) 크게 이동**  
피치가 작으면(66 nm) → 그림자가 패턴 폭과 비슷 → **평균 위치 거의 안 변함**

---

## 7. Focus 변화에 따른 avg_y 동작

### 7-1. 1.8 μm 피치 (3빔, P >> P_min)

- 0차 광이 **CRA 방향으로 기울어진 채로** 이미지에 기여
- Focus 변화 시 0차 광의 위상이 달라짐 → 패턴 중심 위치(avg_y)가 **선형으로 크게 변함**

```
avg_y ↑
  +2nm│         /
      │        /
   0  │───────/──────── Focus=0
      │      /
  −2nm│     /
      └─────────────→ Focus (nm)
         -100    +100
```

### 7-2. 66 nm 피치 (2빔 dipole, P ≈ P_min)

- ±1차 광만 존재, 두 빔이 대칭으로 간섭
- Focus 변화 → 두 빔의 위상이 **같은 비율로** 변함 → 패턴 중심 이동이 **거의 없음**

```
avg_y ↑
  +0.1│  ─ ─ ─ ─ ─ ─ ─
      │
   0  │─────────────────── Focus=0
      │
  −0.1│─ ─ ─ ─ ─ ─ ─ ─
      └─────────────→ Focus (nm)
         -100    +100
```

---

## 8. Bragg 회절 편광(P-파 vs S-파) 효과

### 8-1. 질문 배경

66 nm 피치에서 Bragg 조건($\theta = 11.8°$)이 충족되면, 반사 시 **S편광 반사율 > P편광 반사율** → P편광(CRA 기울기 방향) 성분 감소 → "CRA 효과를 상쇄하는 telecentricity 보정?"

### 8-2. 정량 평가

Fresnel 방정식에서 $\theta_i = 11.8°$ (공기↔TaN, n ≈ 0.97+0.01i):

$$R_s \approx 0.006, \quad R_p \approx 0.0059$$

$$\frac{R_s - R_p}{R_s} \approx 1.7\%$$

→ P/S 반사율 차이가 **< 2%** → Focus-overlay 차이의 주원인으로 볼 수 없음.

### 8-3. 결론

| 메커니즘 | 기여도 |
|---------|--------|
| TGSPI (P vs P_min) | **주원인** ★★★ |
| 2빔 vs 3빔 (dipole) | **주원인** ★★★ |
| Bragg 편광 (P/S 분리) | 부가 효과 ★ (< 2%) |

Bragg 편광이 일부 CRA-tilt 성분을 줄이는 방향으로 작용하는 것은 이론적으로 옳지만,  
그 크기가 매우 작아 1.8 μm vs 66 nm의 큰 focus 민감도 차이를 설명하지는 못합니다.

---

## 9. 참고 문헌

| 번호 | 제목 | 저자 / 연도 | DOI |
|------|------|-------------|-----|
| 1 | "Mask 3D effects and compensation for EUV lithography" | Wood et al., SPIE 10450 (2017) | [10.1117/12.2280371](https://doi.org/10.1117/12.2280371) |
| 2 | "Printing verification of the improved performance of low-n mask…" | SPIE 13979 (2025) | [10.1117/12.3091543](https://doi.org/10.1117/12.3091543) |

---

## 10. 핵심 요약

```
┌──────────────────────────────────────────────────────────────┐
│              1.8 μm 피치           │         66 nm 피치       │
├──────────────────────────────────────────────────────────────┤
│ 이미징 모드    3빔 (0차 + ±1차)    │    2빔 dipole (±1차만)   │
│ P vs P_min   P >> P_min (≈1800x)  │    P ≈ P_min (≈64nm)    │
│ TGSPI         ≈ shadow_base(최대) │    ≈ 0 (최소)            │
│ Focus 민감도   높음 ★★★           │    낮음 ★               │
│ avg_y/100nm   수 nm 변화          │    < 0.1 nm 변화         │
└──────────────────────────────────────────────────────────────┘
```

> **결론**: Focus 민감도 차이의 주원인은 TGSPI 공식의 $(1 - P_\text{min}/P)$ 항과  
> 2빔(dipole) vs 3빔(conventional) 이미징 차이이며, Bragg 편광 효과는 부차적입니다.
