    <template>
      <div class="ecg-container">
        <header class="ecg-header">
          <img src="/cardio_sight_logo.png" alt="CardioSight 로고" class="logo-image" />
          <h1 class="slogan-text">See the unseen. <span class="highlight">Through multiple eyes.</span></h1>
        </header>

        <!-- 대기 상태 오버레이 -->
        <div v-if="isLoading" class="loading-overlay">
          <div class="spinner"></div>
          <div v-if="modelLoading" class="loading-text">🧠 AI 분석중{{ loadingDots }}</div>
          <div v-if="dataLoading" class="loading-text">🗂️ 데이터 로드중{{ loadingDots }}</div>
        </div>

        <!-- 메인 입력 폼 -->
        <section class="ecg-main-form">
          <h2 class="section-title">❤️ 환자 ECG 데이터 입력</h2>

          <div class="form-row">
            <label class="form-label">🏥 환자 데이터베이스</label>
            <input
              ref="dirInput"
              type="file"
              webkitdirectory
              style="display:none"
              @change="onDirSelect"
            />
            <button type="button" class="action-btn" @click="triggerDirInput">데이터 로드</button>
          </div>

          <div class="form-row">
            <label class="form-label">🧑‍⚕️ 환자 선택</label>
            <select v-model="selectedPatient" class="dropdown-select" @change="onPatientChange">
              <option disabled value="">선택하세요</option>
              <option v-for="name in dbList" :key="name" :value="name">
                {{ name }}
              </option>
            </select>
          </div>
          <!-- ▼ 이후 폼/입력 UI 그대로 유지 (아래는 생략 없음) -->
          <div class="form-row">
            <label class="form-label">☑️ 환자 구분</label>
            <select v-model="patientType" class="dropdown-select">
              <option value="기존">기존</option>
              <option value="신규">신규</option>
            </select>
          </div>
          <div class="form-row">
            <label class="form-label">🪪 이름</label>
            <input
              type="text"
              v-model="patientName"
              class="input-text"
              placeholder="환자 이름"
            />
          </div>
          <div class="form-row">
            <label class="form-label">🏷️ 등록 번호</label>
            <input
              type="text"
              v-model="patientId"
              class="input-text"
              placeholder="환자 번호"
            />
          </div>

          <div v-if="imageUrl" class="form-row image-preview-row">
            <label class="form-label">📈ECG 검사지</label>
            <div>
              <img :src="imageUrl" alt="ECG 이미지" class="fit-image" />
            </div>
          </div>

          <div class="form-row">
            <label class="form-label">📎개별 파일 첨부</label>
            <input
              ref="fileInput"
              type="file"
              accept="image/*,.hea,.dat"
              style="display:none"
              multiple
              @change="onFileAttach"
            />
            <button
              type="button"
              class="action-btn"
              @click="triggerFileInput"
              :disabled="!!selectedPatient"
            >파일 업로드</button>

          </div>

          <div>
            <span class="attached-file-list" v-if="imageFile || heaFile || datFile">
              <span style="display: block;">📄 파일 목록:</span>
              <span v-if="imageFile" style="display: block;">📈 [{{ imageFile.name }}]</span>
              <span v-if="heaFile" style="display: block;">📑 [{{ heaFile.name }}]</span>
              <span v-if="datFile">📊 [{{ datFile.name }}]</span>
            </span>
          </div>

          <div class="form-row center">
            <button type="button" class="action-btn primary big" @click="onRun">✨ AI 진단 실행</button>
            <button v-if="showReset" type="button" class="action-btn reset" @click="onReset">♻️초기화</button>
          </div>
        </section>
        <!-- 분석 결과 등 이하 생략 없이 기존 코드 그대로 -->
        <section class="ecg-analysis" v-if="showResult">
          <h2 class="section-title result-title">🧾 AI 진단 결과</h2>
          <div class="ecg-result">
            <strong>진단명</strong>
            <span class="result-value">{{ disease || '—' }}</span>
          </div>
          <div class="ecg-description">
            <p v-if="info">{{ info }}</p>
            <p v-else class="placeholder-text">🔬 분석 결과가 여기에 표시됩니다.</p>
          </div>
          <h2 class="section-title result-title">🔍 AI 기반 ECG 신호 해석</h2>
          <p class="xai-guide">
            📌 하이라이트된 영역은 AI 모델이 진단 근거로 판단한 주요 구간입니다.
          </p>
          <div class="ecg-xai-description">
            <div v-if="xaiResults.length" class="xai-highlight-placeholder multi">
              <div
                v-for="(xai, idx) in xaiResults"
                :key="idx"
                class="xai-image-wrapper"
              >
                <h3 class="xai-title">
                  {{ idx === 0 ? '🖼️ Image XAI' : '📈 Signal XAI' }}
                </h3>
                <img
                  :src="xai"
                  :alt="'XAI 해석 이미지 ' + (idx+1)"
                  class="fit-image"
                />
              </div>
            </div>
            <div v-else class="xai-highlight-placeholder">
              <span class="placeholder-text">🔄 XAI 하이라이트를 준비 중입니다.</span>
            </div>
          </div>
        </section>
      </div>
    </template>


    <script setup>
    import { ref, computed, onUnmounted } from 'vue';
    const allFolders = ref([]);
    const checkedFolders = ref([]);
    const dbList = ref([]);
  const selectedPatient = ref('');
  const selectedPatientFiles = ref([]); // 이 환자 폴더의 파일 리스트

    // refs
    const fileInput = ref(null);

    const imageUrl = ref('');
    const heaFileName = ref('');
    const datFileName = ref('');
    const imageFile = ref(null);
    const heaFile = ref(null);
    const datFile = ref(null);
    const disease = ref('');
    const info = ref('');
    const xaiResults = ref([]);

    const isLoading = ref(false);
    const modelLoading = ref(false);
    const dataLoading = ref(false);
    const loadingDots = ref('.');
    let loadingInterval = null;
    const showReset = ref(false);
    const showResult = ref(false);

    // 목록 관련 변수 완전 삭제
    const allFiles = ref([]);
    const patientType = ref('기존');
    const patientName = ref('');
    const patientId = ref('');

    const isDropdownOpen = ref(false);
    const selectedFolder = ref(null); // {folder, files}

    function openDropdown() { isDropdownOpen.value = true; }
    function closeDropdown() { setTimeout(() => { isDropdownOpen.value = false; }, 150); }


    async function onPatientChange() {
  // 이미 dbList 에서 폴더-파일 구조를 받을 수 있게 포맷 변경 필요 (기존 배열 말고 [{folder, files}] 내역 사용)
  const entry = allFolders.value.find(x => x.folder === selectedPatient.value);
  if (!entry) {
    selectedPatientFiles.value = [];
    imageUrl.value = '';
    imageFile.value = null;
    heaFile.value = null;
    datFile.value = null;
    return;
  }
  selectedPatientFiles.value = entry.files;

  // 파일 목록에서 이미지/hea/dat 파일 자동 로드 및 미리보기
  const patientFolder = entry.folder;
  const img = entry.files.find(f => /\.(png|jpg|jpeg)$/i.test(f));
  const hea = entry.files.find(f => /\.hea$/i.test(f));
  const dat = entry.files.find(f => /\.dat$/i.test(f));

  if (img) {
    imageUrl.value = `/media/patients_data/${encodeURIComponent(patientFolder)}/${encodeURIComponent(img)}`;
    imageFile.value = await fetchFileAsFile(imageUrl.value, img);
  } else {
    imageUrl.value = '';
    imageFile.value = null;
  }
  if (hea) {
    const heaUrl = `/media/patients_data/${encodeURIComponent(patientFolder)}/${encodeURIComponent(hea)}`;
    heaFile.value = await fetchFileAsFile(heaUrl, hea);
    heaFileName.value = hea;
  } else {
    heaFile.value = null;
    heaFileName.value = '';
  }
  if (dat) {
    const datUrl = `/media/patients_data/${encodeURIComponent(patientFolder)}/${encodeURIComponent(dat)}`;
    datFile.value = await fetchFileAsFile(datUrl, dat);
    datFileName.value = dat;
  } else {
    datFile.value = null;
    datFileName.value = '';
  }
  showReset.value = true;

  if (selectedPatient.value && selectedPatient.value.includes('_')) {
  const [code, name] = selectedPatient.value.split('_', 2);
  patientId.value = code;
  patientName.value = name;
} else {
  patientId.value = '';
  patientName.value = '';
}
}

    async function selectFolder(item) {
      selectedFolder.value = item;
      isDropdownOpen.value = false;

      // 이미지 파일 탐색(예시: png/jpg)
      const imgFile = item.files.find(f => /\.(png|jpg|jpeg)$/i.test(f));
      if (imgFile) {
        const url = `/media/patients_data/${encodeURIComponent(item.folder)}/${encodeURIComponent(imgFile)}`;
        imageUrl.value = url;
        // File 객체로 실제 업로드 보내려면:
        try {
          imageFile.value = await fetchFileAsFile(url, imgFile);
        } catch (e) {
          imageFile.value = null;
        }
      } else {
        imageUrl.value = '';
        imageFile.value = null;
      }

      // hea, dat 파일도 필요하면 아래처럼 준비
      const hea = item.files.find(f => /\.hea$/i.test(f));
      const dat = item.files.find(f => /\.dat$/i.test(f));
      if (hea) {
        const heaUrl = `/media/patients_data/${encodeURIComponent(item.folder)}/${encodeURIComponent(hea)}`;
        heaFile.value = await fetchFileAsFile(heaUrl, hea);
        heaFileName.value = hea;
      } else {
        heaFile.value = null;
        heaFileName.value = '';
      }
      if (dat) {
        const datUrl = `/media/patients_data/${encodeURIComponent(item.folder)}/${encodeURIComponent(dat)}`;
        datFile.value = await fetchFileAsFile(datUrl, dat);
        datFileName.value = dat;
      } else {
        datFile.value = null;
        datFileName.value = '';
      }
    }

    async function fetchFileAsFile(url, name, contentType) {
      const res = await fetch(url);
      if (!res.ok) throw new Error("파일 다운로드 실패");
      const blob = await res.blob();
      return new File([blob], name, { type: contentType || blob.type });
    }



    // === 드롭다운 변수/메서드 완전 삭제 ===

    async function triggerDirInput() {
      try {
        isLoading.value = true;
        dataLoading.value = true;
        const res = await fetch('/cardiosight/patients_data/');
        if (!res.ok) throw new Error('폴더 조회 실패');
        const result = await res.json();
        // 폴더명만 배열로 추출 (풀 리스트 쓰려면 result를 그대로 dbList에 할당)
        dbList.value = result.map(item => item.folder); // <== 드롭다운 표시에 쓸 배열
        allFolders.value = result; // [{folder, files}, ...] 전체 데이터(위에서 
        // 만약 폴더명 및 파일명 모두 보이게 하려면 아래처럼:
        // dbList.value = result;
      } catch (err) {
        alert(err.message || '목록 로드 실패');
        dbList.value = [];
      } finally {
        isLoading.value = false;
        modelLoading.value = false;
        dataLoading.value = false;
      }
    }

    // 기존 파일 업로드
    function triggerFileInput() {
      fileInput.value && fileInput.value.click();
    }

    // 파일 첨부 처리
    function onFileAttach(e) {
      const files = e.target.files;
      if (files.length > 3) {
        alert('파일은 최대 3개까지 첨부할 수 있습니다.');
        e.target.value = '';
        return;
      }
      imageUrl.value = '';
      heaFile.value = '';
      datFile.value = '';
      imageFile.value = null;
      heaFileName.value = null;
      datFileName.value = null;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const ext = file.name.split('.').pop().toLowerCase();
        if (['png', 'jpg', 'jpeg', 'gif', 'bmp'].includes(ext)) {
          imageUrl.value = URL.createObjectURL(file);
          imageFile.value = file;
        } else if (ext === 'hea') {
          heaFileName.value = file.name;
          heaFile.value = file;
        } else if (ext === 'dat') {
          datFileName.value = file.name;
          datFile.value = file;
        } else {
          alert('지원하지 않는 파일 형식입니다: ' + file.name);
          e.target.value = '';
          return;
        }
      }
      if (imageFile.value) {
        const match = imageFile.value.name.match(/^[A-Za-z0-9-]+_(.+?)\./);
        if (match) {
          patientId.value = match[1];
          patientName.value = match[2];
        }
      }
      e.target.value = '';
      showReset.value = true;
    }

    // 리셋
    function onReset() {
      imageUrl.value = '';
      imageFile.value = null;
      heaFileName.value = '';
      datFileName.value = '';
      heaFile.value = null;
      datFile.value = null;
      patientName.value = '';
      patientId.value = '';
      showReset.value = false;
      showResult.value = false;
    }

    // 로딩 애니
    function startLoading() {
      isLoading.value = true;
      let dotsArr = ['.', '..', '...', '..', '.'];
      let idx = 0;
      loadingDots.value = dotsArr[0];
      loadingInterval = setInterval(() => {
        idx = (idx + 1) % dotsArr.length;
        loadingDots.value = dotsArr[idx];
      }, 400);
    }

    function stopLoading() {
      isLoading.value = false;
      loadingDots.value = '.';
      if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
      }
    }

    // 분석 실행
    async function onRun() {
      if (!imageFile.value && !heaFile.value) {
        alert('이미지 또는 신호 파일 중 하나 이상 첨부하세요.');
        return;
      }
      modelLoading.value = true;
      dataLoading.value = false;
      startLoading();

      const formData = new FormData();
      if (imageFile.value) formData.append('image', imageFile.value);
      if (heaFile.value) formData.append('hea', heaFile.value);
      if (datFile.value) formData.append('dat', datFile.value);
      if (heaFileName.value) formData.append('hea_name', heaFileName.value);
      if (datFileName.value) formData.append('dat_name', datFileName.value);
      try {
        const res = await fetch('/cardiosight/upload', {
          method: 'POST',
          body: formData,
        });
        if (res.ok) {
          const data = await res.json();
          disease.value = data.disease || '';
          info.value = data.info || '';
          const now = Date.now();
          xaiResults.value = Array.isArray(data.xai_results)
            ? data.xai_results.map(url => url ? `${url}?t=${now}` : null)
            : [];
          showReset.value = true;
          showResult.value = true;
          alert('업로드 및 분석 성공');
        } else {
          const err = await res.json();
          alert('업로드 실패: ' + (err.error || ''));
        }
      } catch (err) {
        alert('네트워크 오류');
      } finally {
        stopLoading();
      }
    }

    onUnmounted(() => {
      stopLoading();
    });
    </script>


    <style scoped>
    .ecg-container {
      /* width: 100vw; */
      min-width: 320px;
      min-height: 100vh;
      margin: 0;
      padding: 0;
      background: transparent;
      font-family: 'Noto Sans KR', 'Roboto', Arial, sans-serif;
      box-sizing: border-box;
    }

    /* 헤더, 로고 */
    .ecg-header { text-align: center; margin-bottom: 5px; }
    .logo-image {
      display: block;
      margin: 0 auto;
      max-width: 300px;
      height: auto;
      padding: 1px 0 6px 0;
      filter: drop-shadow(0 2px 8px rgba(0,0,0,0.08));
    }

    /* 메인 입력 폼 */
    .ecg-main-form {
      max-width: 1000px;
      margin: 0 auto 32px auto;
      background: #fff;
      border-radius: 14px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.04);
      padding: 32px 24px;
      box-sizing: border-box;
    }

    /* 폼 행 및 입력 스타일 */
    .form-row {
      display: flex;
      align-items: center;        /* 모든 항목을 수직 중앙 정렬 */
      gap: 16px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }
    .form-row.center { justify-content: center; margin-top: 28px; }
    .form-label {
      min-width: 110px;
      font-weight: 500;
      color: #23395d;
      font-size: 1.07em;
      padding-top: 0;             /* 높이 이슈 있을 때 0 */
      flex-shrink: 0;
      line-height: 1.4;
      display: flex;
      align-items: center;
    }
    .input-text, .dropdown-select {
      flex: 1 1 0;
      width: 100%;
      padding: 10px 16px;
      border: 1.5px solid #b5c1d1;
      border-radius: 24px;
      font-size: 1.07em;
      background: #f0f4f8;
      outline: none;
      transition: border 0.18s;
      height: 50px;               /* 버튼과 높이 통일 */
      box-sizing: border-box;
    }
    .input-text:focus, .dropdown-select:focus { border: 2px solid #4a90e2; }

    /* 드롭다운(검색) */
    .dropdown-search-wrapper { position: relative; width: 100%; max-width: 260px; }
    .dropdown-search-input {
      padding: 12px 18px; border: 1.5px solid #b5c1d1; border-radius: 24px;
      font-size: 1.09em; outline: none; background: #f0f4f8; width: 100%;
      transition: border 0.18s; margin-bottom: 0;
    }
    .dropdown-search-input:focus { border: 2px solid #4a90e2; }
    .dropdown-menu {
      position: absolute; top: 44px; left: 0; width: 100%; background: #fff;
      border: 1.5px solid #b5c1d1; border-radius: 18px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08);
      z-index: 10; max-height: 220px; overflow-y: auto; margin-top: 2px;
    }
    .dropdown-item {
      padding: 11px 18px; font-size: 1.07em; color: #23395d; cursor: pointer;
      border-bottom: 1px solid #f0f4f8;
      background: #fff; transition: background 0.14s;
    }
    .dropdown-item:last-child { border-bottom: none; }
    .dropdown-item.selected, .dropdown-item:hover { background: #e6eaf2; }
    .dropdown-item.empty {
      color: #b0b8c1; cursor: default; background: #fff;
    }
    .attached-file-list {
      color: #4a90e2; font-size: 0.97em; margin-left: 110px; margin-top: -6px; line-height: 1.6;
    }

    /* 버튼 */
    .action-btn {
      background: #e6eaf2;
      color: #23395d;
      border: none;
      border-radius: 24px;
      padding: 14px 34px;
      font-size: 1.12em;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.20s, color 0.20s, box-shadow 0.13s;
      box-shadow: 0 2px 10px rgba(74,144,226,0.07), 0 1px 3px rgba(0,0,0,0.03);
      margin-right: 10px; outline: none; letter-spacing: -0.5px;
      display: inline-block; min-width: 110px;
    }
    .action-btn:last-child { margin-right: 0; }
    .action-btn.primary {
      background: #4a90e2; color: #fff; box-shadow: 0 4px 22px rgba(74,144,226,0.13);
    }
    .action-btn.primary:hover {
      background: #357ab7; color: #fff;
    }
    .action-btn.big {
      font-size: 1.20em;
      padding: 17px 48px;
      border-radius: 30px;
      min-width: 170px;
    }
    .action-btn:hover { background: #d4dbe7; }
    .action-btn:active { background: #bfc8da; color: #23395d; }
    .action-btn.reset {
      background: #b0b8c1; color: #fff; font-weight: 600; box-shadow: none;
    }
    .action-btn.reset:hover { background: #8e99a7; color: #fff; }
    .action-btn:disabled,
    .action-btn[disabled] {
      background: #e1e3e8; color: #b0b8c1;
      cursor: not-allowed; border: none; box-shadow: none;
    }

    /* === XAI 해석 섹션: 흰색 라운드+좌우 여백/이미지 확장 스타일 */
    .ecg-xai-description {
      background: #fff;
      border-radius: 14px;
      padding: 5px 5%;
      box-sizing: border-box;
      max-width: 90%;
      margin: 0 auto;
    }
    .xai-guide {
      color: #5b6a91; font-size: 0.98em; margin-bottom: 10px;
    }
    .xai-highlight-placeholder.multi {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-start;
      gap: 40px;
      width: 100%;
      box-sizing: border-box;
    }
    .xai-image-wrapper {
      flex: 1 1 48%;
      min-width: 300px;
      max-width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      box-sizing: border-box;
      margin-bottom: 0;
    }
    .fit-image {
      width: 100%;
      height: auto;
      object-fit: contain;
      border-radius: 6px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.04);
      border: 1px solid #e3e7ed;
      background: #fff;
      display: block;
      max-width: none;
    }

    /* === 분석 결과/AI 결과 박스 === */
    .ecg-analysis {
      max-width: 90%;
      min-width: 320px;
      margin: 0 auto;
      background: #fff;
      border-radius: 14px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.04);
      padding: 5px 5% 5px 5%;
      box-sizing: border-box;
    }
    .ecg-result {
      font-size: 1.13em;
      margin-bottom: 8px;
      color: #23395d;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .result-value { color: #e74c3c; font-weight: 700; font-size: 1.07em; }
    .ecg-description, .ecg-xai-description {
      font-size: 1.01em; color: #2d3547; margin-top: 8px; line-height: 1.6;
    }

    /* === 반응형 미디어쿼리 === */
    @media (max-width: 1200px) {
      .xai-highlight-placeholder.multi { gap: 24px; }
      .xai-image-wrapper { flex: 1 1 100%; max-width: 100%; }
      .fit-image { max-width: 100%; }
    }
    @media (max-width: 960px) {
      .ecg-xai-description { padding-left: 10%; padding-right: 10%; }
      .xai-image-wrapper { max-width: 100%; }
    }
    @media (max-width: 600px) {
      .ecg-container,
      .ecg-analysis,
      .ecg-main-form,
      .ecg-xai-description { padding-left: 8px; padding-right: 8px; }
      .ecg-xai-description { padding-top: 20px; padding-bottom: 20px; }
      .xai-highlight-placeholder.multi { gap: 14px; }
      .xai-image-wrapper { width: 100%; max-width: 100%; }
      .fit-image { max-width: 100%; }
    }

    /* === 로딩 오버레이 === */
    .loading-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(255,255,255,0.7);
      z-index: 9999;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .spinner {
      border: 6px solid #e3e7ed;
      border-top: 6px solid #4a90e2;
      border-radius: 50%;
      width: 48px; height: 48px;
      animation: spin 1s linear infinite;
      margin-bottom: 18px;
    }
    @keyframes spin {
      100% { transform: rotate(360deg); }
    }
    .loading-text {
      font-size: 1.12em;
      color: #23395d;
      font-weight: 500;
      letter-spacing: -0.5px;
      margin-top: 4px;
    }

    .slogan-text {
      margin-top: 0px;
      font-size: 1.18em;
      font-weight: 500;
      color: #5b6a91;
      letter-spacing: -0.3px;
    }

    .slogan-text .highlight {
      font-weight: 600;
      color: #4a90e2;
    }

    .section-title {
      font-size: 1.3em;
      font-weight: 600;
      margin-bottom: 24px;
      padding-bottom: 6px;
      border-bottom: 2px solid #dbe2ec;
      color: #2b3a4d;
    }

    .result-title {
      margin-top: 48px;
    }

    .placeholder-text {
      color: #a0a6b3;
      font-style: italic;
    }

    .ecg-result strong {
      font-weight: 600;
      font-size: 1.1em;
    }

    .result-value {
      color: #e74c3c;
      font-weight: 700;
      font-size: 1.15em;
    }

    .xai-title {
      color: #31405a;
      font-weight: 600;
      margin-bottom: 12px;
      font-size: 1.08em;
    }
    </style>

    <style>
    html, body {
      height: 100%;
      min-height: 100vh;
      margin: 0;
      padding: 0;
      background: #f6f8fa;
    }
    </style>