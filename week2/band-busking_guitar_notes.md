# Band Busking 포스터 — 거꾸로 선 기타

## 디자인 철학: Upside-down Serenade (거꾸로 세레나데)

진짜 사진 한 장이 화면의 중심이다. 기타를 거꾸로 세우면 둥근 몸통은 사탕처럼, 긴 넥은 사탕 막대처럼 보인다. 익숙한 악기를 낯설게 놓아, 거리에서 갑자기 들려오는 연주처럼 눈을 멈추게 한다.

사진은 두 가지 잉크의 망점(하프톤)으로 다시 찍는다. 마젠타 망점이 중간 톤을, 그 위에 겹친 검정 망점이 그림자를 맡는다. 넥은 아래로 갈수록 망점이 작아지며 종이 속으로 사라진다. 기타가 덮는 자리는 글자를 비워 두어(녹아웃) 망점 사이로도 기타가 앞에 있는 것처럼 보인다.

글자는 1920~30년대 아르데코 포스터를 닮은 가는 글꼴이다. 무거운 망점 사진 옆에서 가늘고 우아한 획이 대비를 만든다. 큰 BAND가 위를 받치고, BUSKING과 날짜는 같은 기준선에 나란히 놓여 아래를 닫는다. 몸통을 감싸는 가는 궤도선은 기타 뒤로만 지나가 깊이를 만든다.

종이결과 작은 티끌, 살짝 닳은 잉크 가장자리까지 손으로 찍은 인쇄물의 흔적을 남겨, 컴퓨터로 매끈하게 만든 느낌을 덜어낸다.

## 구성

- 크기: A3 세로 비율, 3564×5040px (A3로 인쇄하면 304.8dpi)
- 색: 종이 흰색, 마젠타 #BE0876, 검정 #181418
- 글꼴: Poiret One (canvas-design 스킬의 canvas-fonts, 오픈 폰트 라이선스)
- 글자: BAND, BUSKING, 2026/ 11.04 (그 외 글자 없음)
- 여백: 위·왼쪽·오른쪽 모두 196px(약 16mm). 글자의 실제 잉크 끝을 여백선에 맞춤
- 사진: 2색 하프톤, 망점 간격 20px(약 1.7mm), 마젠타 75°, 검정 45°

## 사진 출처

- 사진: Apolo Photographer, Unsplash — https://unsplash.com/photos/xmksM4em7a0
- 라이선스: Unsplash License (무료로 수정·사용 가능, 출처 표기 의무 없음)
- 원본: `photos/guitar.jpg` (2400×3600), 배경을 지운 사진: `photos/guitar_cutout.png`

## 다시 만들기

이 폴더의 상위 폴더(C:\design-class)에서 PowerShell로 실행:

```
$env:UV_PYTHON_INSTALL_DIR = 'C:\design-class\.claude\uv\python'
$env:UV_CACHE_DIR = 'C:\design-class\.claude\uv\cache'
uv run --with pillow week2/make_guitar_poster.py
```
