<template>
  <div class="page">
    <div class="page-narrow create-page">
      <div class="steps">
        <div :class="['step', { active: step === 1, done: step > 1 }]">1 填写案件信息</div>
        <div class="step-line"></div>
        <div :class="['step', { active: step === 2 }]">2 导入初始证据</div>
      </div>

      <section v-if="step === 1" class="panel form-section">
        <div>
          <h2 class="section-title">第一步：填写案件信息</h2>
          <p class="muted">请填写案件基础信息。后续证据导入、图谱构建、智能分析和信息画像都会围绕该案件展开。</p>
        </div>

        <div class="panel-soft">
          <h3>基本信息</h3>
          <div class="form-grid">
            <label class="form-field">案件名称 *
              <input v-model="form.title" class="field" maxlength="80" placeholder="请输入案件名称" />
            </label>
            <label class="form-field">案号 / 内部编号
              <input v-model="form.caseNo" class="field" placeholder="如：内部编号或案号" />
            </label>
            <label class="form-field">案件类型 / 罪名
              <select v-model="form.offenseId" class="select">
                <option value="">可后续补充</option>
                <option v-for="item in offenseTemplates" :key="item.offense_id" :value="item.offense_id">{{ item.name }}</option>
              </select>
            </label>
          </div>
        </div>

        <div class="panel-soft">
          <h3>承办信息</h3>
          <div class="form-grid">
            <label class="form-field">承办部门
              <input v-model="form.department" class="field" placeholder="请输入承办部门" />
            </label>
            <label class="form-field">承办人员
              <input v-model="form.owner" class="field" placeholder="请输入承办人员" />
            </label>
          </div>
        </div>

        <div class="panel-soft">
          <h3>案件说明</h3>
          <textarea v-model="form.description" class="textarea" placeholder="简要描述案件来源、背景、初步线索或说明"></textarea>
        </div>
        <p v-if="error" class="error-text">{{ error }}</p>
      </section>

      <section v-else class="panel form-section">
        <div>
          <h2 class="section-title">第二步：导入初始证据</h2>
          <p class="muted">可以导入案卷材料、文书、笔录、资金流水、通联记录等证据。也可以先创建空案件，稍后继续导入。</p>
        </div>

        <input ref="fileInput" class="hidden-input" type="file" multiple @change="onFilesSelected" />
        <input ref="folderInput" class="hidden-input" type="file" multiple webkitdirectory @change="onFilesSelected" />
        <input ref="zipInput" class="hidden-input" type="file" accept=".zip" @change="onArchiveSelected" />

        <div class="grid-3">
          <button class="upload-card" @click="fileInput?.click()">
            <strong>上传文件</strong>
            <span>适合少量单份材料</span>
            <b>选择文件</b>
          </button>
          <button class="upload-card" @click="folderInput?.click()">
            <strong>批量导入文件夹</strong>
            <span>适合完整案卷材料</span>
            <b>选择文件夹</b>
          </button>
          <button class="upload-card" @click="zipInput?.click()">
            <strong>上传压缩包</strong>
            <span>适合打包后的案卷材料</span>
            <b>选择压缩包</b>
          </button>
        </div>

        <div v-if="selectedFiles.length" class="panel-soft">
          <div class="row-between">
            <div>
              <h3>已选择 {{ selectedFiles.length }} 个文件</h3>
              <p class="muted">文件总大小 {{ totalSize }}</p>
            </div>
            <button class="btn" @click="clearFiles">清空</button>
          </div>
          <div class="file-table">
            <div class="file-row head"><span>文件名</span><span>类型</span><span>大小</span><span>状态</span></div>
            <div v-for="file in selectedFiles.slice(0, 12)" :key="file.name + file.size" class="file-row">
              <span>{{ file.webkitRelativePath || file.name }}</span>
              <span>{{ file.type || suffix(file.name) }}</span>
              <span>{{ formatSize(file.size) }}</span>
              <span>{{ importing ? '上传中' : '待上传' }}</span>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <h2>尚未选择证据材料</h2>
          <p class="muted">你可以先创建空案件，稍后在案件空间中继续导入证据。</p>
          <button class="btn" style="margin-top: 14px;" :disabled="creating" @click="createAndEnter">暂不导入，创建空案件</button>
        </div>

        <AsyncProgressBar v-if="creating || importing" :value="progressValue" :label="progressLabel" :detail="progressDetail" />
        <p v-if="error" class="error-text">{{ error }}</p>
      </section>

      <footer class="bottom-actions">
        <button class="btn" :disabled="creating || importing" @click="step === 1 ? router.push('/cases') : step = 1">{{ step === 1 ? '取消' : '上一步' }}</button>
        <button class="btn primary" :disabled="creating || importing" @click="step === 1 ? nextStep() : createAndEnter()">
          {{ step === 1 ? '下一步：导入证据' : '创建案件并进入' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { backendApi, type OffenseTemplateSummary } from '../api/backend';
import AsyncProgressBar from '../components/AsyncProgressBar.vue';

const router = useRouter();
const step = ref<1 | 2>(1);
const offenseTemplates = ref<OffenseTemplateSummary[]>([]);
const selectedFiles = ref<File[]>([]);
const archiveFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const folderInput = ref<HTMLInputElement | null>(null);
const zipInput = ref<HTMLInputElement | null>(null);
const creating = ref(false);
const importing = ref(false);
const error = ref('');

const form = ref({
  title: '',
  caseNo: '',
  offenseId: '',
  department: '',
  owner: '',
  description: '',
});

const progressValue = computed(() => importing.value ? 72 : 28);
const progressLabel = computed(() => importing.value ? '正在导入证据材料' : '正在创建案件');
const progressDetail = computed(() => importing.value ? '系统正在上传并解析初始证据，案件创建成功后会进入案件空间。' : '正在写入案件基础信息。');
const totalSize = computed(() => formatSize(selectedFiles.value.reduce((sum, file) => sum + file.size, 0)));

onMounted(async () => {
  try {
    offenseTemplates.value = await backendApi.listOffenseTemplates();
  } catch {
    offenseTemplates.value = [];
  }
});

function nextStep() {
  error.value = '';
  const title = form.value.title.trim();
  if (!title) {
    error.value = '案件名称不能为空。';
    return;
  }
  if (title.length > 80) {
    error.value = '案件名称过长，请控制在 80 个字符以内。';
    return;
  }
  step.value = 2;
}

function onFilesSelected(event: Event) {
  archiveFile.value = null;
  selectedFiles.value = Array.from((event.target as HTMLInputElement).files || []);
}

function onArchiveSelected(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] || null;
  archiveFile.value = file;
  selectedFiles.value = file ? [file] : [];
}

function clearFiles() {
  selectedFiles.value = [];
  archiveFile.value = null;
  if (fileInput.value) fileInput.value.value = '';
  if (folderInput.value) folderInput.value.value = '';
  if (zipInput.value) zipInput.value.value = '';
}

async function createAndEnter() {
  nextStep();
  if (error.value) return;
  creating.value = true;
  error.value = '';
  try {
    const selectedOffense = offenseTemplates.value.find((item) => item.offense_id === form.value.offenseId);
    const descriptionParts = [
      form.value.description.trim(),
      form.value.caseNo.trim() ? `案号 / 内部编号：${form.value.caseNo.trim()}` : '',
      form.value.department.trim() ? `承办部门：${form.value.department.trim()}` : '',
    ].filter(Boolean);
    const item = await backendApi.createCustomCase({
      title: form.value.title.trim(),
      description: descriptionParts.join('\n') || null,
      legal_basis: selectedOffense?.name || null,
      offense_id: form.value.offenseId || null,
      owner: form.value.owner.trim() || null,
    });
    localStorage.setItem('active_case_id', item.case_id);
    localStorage.setItem('active_workspace_id', item.case_id);
    if (selectedFiles.value.length) {
      importing.value = true;
      try {
        if (archiveFile.value) await backendApi.ingestArchive(item.case_id, archiveFile.value);
        else await backendApi.ingestBatch(item.case_id, selectedFiles.value);
      } catch {
        error.value = '部分证据导入失败，案件已创建。你可以进入案件空间后重新导入失败材料。';
      }
    }
    await router.push(`/cases/${item.case_id}`);
  } catch (err) {
    error.value = '案件创建失败，请检查网络连接或后端服务状态。';
    if (err instanceof Error && err.message) error.value = err.message;
  } finally {
    creating.value = false;
    importing.value = false;
  }
}

function suffix(name: string) {
  return name.includes('.') ? name.split('.').pop() || '-' : '-';
}

function formatSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<style scoped>
.create-page {
  padding-bottom: 86px;
}

.steps {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.step {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  padding: 9px 14px;
  color: var(--muted);
  font-weight: 900;
}

.step.active,
.step.done {
  border-color: var(--primary);
  background: var(--primary-soft);
  color: var(--primary-strong);
}

.step-line {
  height: 1px;
  flex: 1;
  background: var(--line);
}

.form-section {
  display: grid;
  gap: 14px;
}

.panel-soft h3 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 900;
}

.upload-card {
  min-height: 150px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 16px;
  display: grid;
  gap: 8px;
  text-align: left;
}

.upload-card:hover {
  border-color: var(--primary);
  background: var(--primary-soft);
}

.upload-card strong {
  font-size: 17px;
  font-weight: 900;
}

.upload-card span {
  color: var(--muted);
}

.upload-card b {
  color: var(--primary-strong);
}

.file-table {
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

.file-row {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(100px, 0.7fr) minmax(90px, 0.5fr) minmax(90px, 0.5fr);
  gap: 10px;
  padding: 10px 12px;
  border-top: 1px solid var(--line);
  font-size: 13px;
}

.file-row:first-child {
  border-top: 0;
}

.file-row.head {
  background: #f8fafc;
  color: var(--muted);
  font-weight: 900;
}

.bottom-actions {
  position: fixed;
  right: 20px;
  left: 316px;
  bottom: 0;
  z-index: 10;
  border-top: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.94);
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
}
</style>
