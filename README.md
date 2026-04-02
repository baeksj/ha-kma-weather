# KMA Weather for Home Assistant

`KMA Weather`는 대한민국 기상청(KMA) 단기예보 OpenAPI를 이용해 Home Assistant에 현재 날씨, 시간별 예보, 일별 예보를 제공하는 custom integration입니다.  
HACS Custom Repository로 설치할 수 있도록 구성되어 있습니다.

## 주요 기능

- 기상청 초단기실황 `getUltraSrtNcst` 조회
- 기상청 초단기예보 `getUltraSrtFcst` 조회
- 기상청 단기예보 `getVilageFcst` 조회
- 위도/경도를 기상청 DFS 격자(`nx`, `ny`)로 자동 변환
- Home Assistant `zone` 엔티티를 이용한 설정
- 시간별 예보 / 일별 예보 제공
- 일시적 API 장애 시 마지막 정상 데이터를 유지하는 실패 허용 로직
- HACS 설치를 위한 `brand/` 자산 포함

## 설치 전 준비

이 integration을 사용하려면 먼저 `data.go.kr`에서 기상청 OpenAPI 활용 신청을 하고 서비스 키를 발급받아야 합니다.

준비물:

- `data.go.kr` 계정
- Home Assistant 설정에서 생성한 지역(`zone`)
- 발급받은 기상청 API 서비스 키

기본으로 필요한 API:

- `기상청_단기예보 조회서비스`

환경 구성에서 선택적으로 확장할 수 있는 추가 API:

- `기상청_생활기상지수 조회서비스(3.0)`
- `한국환경공단_에어코리아_대기오염정보`
- `기상청_꽃가루농도위험지수 조회서비스(3.0)`
- `기상청_중기예보 조회서비스`

## data.go.kr API 신청 및 발급 절차

아래 절차는 `공공데이터포털(data.go.kr)`에서 기본 API인 `기상청_단기예보 조회서비스`를 처음 신청하는 기준으로 정리했습니다.

1. `https://www.data.go.kr`에 로그인합니다.
2. 검색창에서 `기상청 단기예보 조회서비스` 또는 `VilageFcstInfoService_2.0` 관련 API를 찾습니다.
3. 상세 페이지에서 제공 형식이 `OpenAPI`인지 확인합니다.
4. 활용 목적과 애플리케이션 정보를 입력해 `활용신청`을 진행합니다.
5. 신청이 승인되면 마이페이지 또는 해당 API 상세 화면에서 `일반 인증키(Encoding)` / `일반 인증키(Decoding)`를 확인할 수 있습니다.
6. Home Assistant 설정 화면에는 보통 `Decoding` 키를 넣는 것이 가장 덜 헷갈립니다.

실제로 많이 막히는 지점:

- 신청 직후 바로 호출되지 않을 수 있습니다.
승인까지 약간의 시간이 걸릴 수 있으니, 호출이 실패하면 잠시 후 다시 확인하는 편이 좋습니다.

- 같은 API 이름처럼 보여도 세부 서비스가 다를 수 있습니다.
이 integration은 기상청 단기예보 계열 API를 전제로 작성되어 있으므로, 초단기실황/초단기예보/단기예보를 포함하는 서비스인지 확인해야 합니다.

- `Encoding` 키를 그대로 붙여 넣으면 호출 URL에서 다시 인코딩되며 실패하는 경우가 있습니다.
설정값으로는 `Decoding` 키를 사용하는 편이 안전합니다.

권장 확인 순서:

1. API 상세 페이지에서 `활용신청` 완료 여부를 확인합니다.
2. `일반 인증키(Decoding)`를 복사합니다.
3. data.go.kr 제공 테스트 화면이나 샘플 호출에서 응답이 정상인지 확인합니다.
4. 그다음 Home Assistant integration 설정에 같은 키를 입력합니다.

추가 API를 쓰고 싶다면:

- 같은 `data.go.kr` 서비스 키를 재사용합니다.
- 대신 사용하려는 각 OpenAPI 서비스는 별도로 `활용신청`해야 할 수 있습니다.
- 즉, 키를 새로 발급받는 개념보다 `원하는 API 서비스에 대한 사용 승인`이 되었는지가 중요합니다.

## Home Assistant 사전 준비

이 integration은 Home Assistant에 등록된 지역(`zone`) 정보를 사용합니다.

권장 방식은 Home Assistant 설정 화면에서 지역을 생성하고, 해당 지역에 정확한 위도/경도를 입력하는 것입니다.

일반적인 흐름:

1. Home Assistant `설정`에서 지역(`zone`)을 생성합니다.
2. 지역 이름을 정하고, 사용할 위치의 정확한 위도/경도를 입력합니다.
3. 이 integration 설정 시 해당 지역을 선택합니다.
4. 선택한 좌표를 기준으로 기상청 DFS 격자(`nx`, `ny`)를 계산합니다.
5. 같은 좌표를 기준으로 공공데이터에서 제공하는 위치/행정구역 후보를 매핑합니다.
6. 매핑된 후보 중 가장 적절한 지역을 선택해 생활기상지수 등 부가 데이터를 연결합니다.

즉, 사용자는 Home Assistant 안에서 위치를 관리하고, integration은 그 위치 좌표를 기준으로 기상청 예보 격자와 공공데이터 행정구역을 연결하는 방식입니다.

## HACS 설치 방법

1. HACS에서 `Integrations`로 이동합니다.
2. 우측 상단 메뉴에서 `Custom repositories`를 엽니다.
3. 저장소 URL에 `https://github.com/baeksj/ha-kma-weather`를 입력합니다.
4. Category는 `Integration`으로 선택합니다.
5. `KMA Weather`를 검색해 설치합니다.
6. Home Assistant를 재시작합니다.
7. `설정 → 기기 및 서비스 → 통합 추가`에서 `KMA Weather`를 추가합니다.

설정 시 입력값:

- API key: `data.go.kr`에서 발급받은 서비스 키
- Location name: Home Assistant에 표시할 이름, 비워두면 기본 이름 사용
- Zone: 설정에서 생성한 Home Assistant 지역(`zone`)

## 환경 구성으로 추가 API 확장

기본 설치가 끝나면 `설정 > 기기 및 서비스 > KMA Weather > 구성`에서 추가 API를 선택적으로 연결할 수 있습니다.

환경 구성 화면의 `select` 항목은 다음 용도로 사용됩니다.

- 어떤 공공데이터 API를 추가로 사용할지 선택
- 해당 API를 사용하려면 `data.go.kr`에서 어떤 서비스를 활용신청해야 하는지 안내
- 적용 후 어떤 센서가 새로 생성되는지 안내

즉, 최초 설치는 기본 날씨 기능 중심으로 끝내고, 이후 환경 구성에서 필요한 기능만 켜는 구조입니다.

추가 API 목록:

- `기상청_생활기상지수 조회서비스(3.0)`
  - 안내 내용: 자외선지수, 대기확산지수용 API라는 점을 표시
  - 추가 센서 예시: `KMA UV Index`, `KMA Air Diffusion Index`
- `한국환경공단_에어코리아_대기오염정보`
  - 안내 내용: 대기질 관련 API라는 점을 표시
  - 추가 센서 예시: 미세먼지, 초미세먼지, 통합대기환경지수 계열
- `기상청_꽃가루농도위험지수 조회서비스(3.0)`
  - 안내 내용: 꽃가루 위험도 관련 API라는 점을 표시
  - 추가 센서 예시: `KMA Pine Pollen Risk`, `KMA Oak Pollen Risk`, `KMA Weed Pollen Risk`
- `기상청_중기예보 조회서비스`
  - 안내 내용: 중기예보 확장용 API라는 점을 표시
  - 추가 센서 예시: `KMA Mid-term Forecast Summary`, `KMA Mid-term Min Temperature`, `KMA Mid-term Max Temperature`

현재 구현 기준:

- 기본 API `기상청_단기예보 조회서비스`는 설치 시 사용됩니다.
- 추가 API 중 현재 환경 구성에 실제 연결된 항목은 아래 4개입니다.
- `기상청_생활기상지수 조회서비스(3.0)` → `KMA UV Index`, `KMA Air Diffusion Index`
- `한국환경공단_에어코리아_대기오염정보` → `AirKorea Station`, `AirKorea PM10`, `AirKorea PM2.5`, `AirKorea O3`, `AirKorea NO2`, `AirKorea CO`, `AirKorea SO2`, `AirKorea Integrated Air Quality Index`
- `기상청_꽃가루농도위험지수 조회서비스(3.0)` → `KMA Pine Pollen Risk`, `KMA Oak Pollen Risk`, `KMA Weed Pollen Risk`
- `기상청_중기예보 조회서비스` → `KMA Mid-term Forecast Summary`, `KMA Mid-term Min Temperature`, `KMA Mid-term Max Temperature`

## 수동 설치 방법

1. 이 저장소의 `custom_components/kma_weather` 디렉터리를 Home Assistant 설정 디렉터리의 `custom_components` 아래로 복사합니다.
2. Home Assistant를 재시작합니다.
3. `설정 → 기기 및 서비스 → 통합 추가`에서 `KMA Weather`를 추가합니다.

## 동작 방식

- 설정에서 선택한 지역(`zone`)의 위도/경도를 읽습니다.
- 해당 좌표를 기상청 DFS 격자로 변환합니다.
- 같은 좌표를 기반으로 공공데이터 위치/행정구역 코드를 가장 가깝게 매핑합니다.
- 초단기실황, 초단기예보, 단기예보 API를 순차 호출합니다.
- 현재 날씨와 시간별/일별 예보를 weather 엔티티로 노출합니다.

## 장애 처리

API가 일시적으로 실패해도 바로 엔티티를 unavailable로 바꾸지 않고, 마지막 정상 데이터를 일정 횟수까지 유지합니다.

- 기본 연속 실패 허용 횟수: `3`
- 옵션에서 변경 가능
- 허용 횟수 미만이면 마지막 정상 데이터 유지
- 허용 횟수 이상이면 coordinator 갱신 실패로 처리

관련 속성:

- `consecutive_failures`
- `failure_tolerance`
- `data_stale`

## 현재 제약 사항

- 설정 시 Home Assistant 지역(`zone`)이 반드시 필요합니다.
- 선택한 지역의 좌표를 나중에 변경해도 기존 config entry에 즉시 자동 반영되지는 않을 수 있습니다.
- 주소 검색 기반 설정 UX는 아직 포함되어 있지 않습니다.
- 기상청 응답값의 일부 세부 카테고리 매핑은 계속 보강할 수 있습니다.

## 개발 확인

저장소 루트에서 아래 명령으로 간단한 문법 확인을 할 수 있습니다.

```bash
python3 -m compileall custom_components/kma_weather
```

## 배포 체크리스트

- `custom_components/kma_weather/manifest.json`의 `version`을 새 태그와 맞춥니다.
- Git 태그와 GitHub Release 버전을 동일하게 맞춥니다.
- GitHub 저장소 description과 topics를 설정합니다.
- HACS에서 읽는 `hacs.json`의 Home Assistant 최소 버전을 실제 지원 범위와 맞춥니다.

권장 GitHub topics:

- `home-assistant`
- `hacs`
- `custom-integration`
- `weather`
- `kma`
- `korea`

## 참고

- 공공데이터포털: `https://www.data.go.kr`
- 기상청 단기예보 계열 API는 발표 시각과 실제 조회 가능 시각 사이에 지연이 있을 수 있습니다.
- 실제 운영 시에는 테스트 키보다 운영에 사용할 키를 별도로 관리하는 편이 안전합니다.
