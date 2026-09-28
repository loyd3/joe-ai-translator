<template>
  <div class="story-panel">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">{{ data?.title || '故事结构' }}</h1>
      <el-tag v-if="data?.status" size="small">{{ statusText }}</el-tag>
      <div class="header-actions">
        <el-tooltip content="重新根据原文生成" placement="bottom">
          <el-button
            circle
            class="icon-btn"
            :loading="regenerating"
            :disabled="editMode || !data?.applicable"
            @click="regenerate"
          >
            <el-icon v-if="!regenerating"><RefreshRight /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip v-if="!editMode" content="编辑" placement="bottom">
          <el-button circle class="icon-btn" type="primary" plain @click="enterEdit">
            <el-icon><Edit /></el-icon>
          </el-button>
        </el-tooltip>
        <template v-else>
          <el-button size="small" @click="cancelEdit">取消</el-button>
          <el-button size="small" type="primary" :loading="saving" @click="save()">保存</el-button>
        </template>
      </div>
    </div>

    <div class="page-body" v-loading="loading">
      <el-empty v-if="data && !data.applicable" description="诗歌和专业文档不整理故事结构" />
      <template v-else-if="data">
        <p class="hint">
          {{ editMode
            ? '编辑模式：可增删改各项，完成后点保存。确认译名会写入词库。'
            : '阅读模式：点编辑图标修改；右上角刷新可按原文重新生成故事结构。' }}
        </p>

        <!-- 故事简介 -->
        <section class="block">
          <div class="block-head">
            <h2>故事简介</h2>
            <el-tooltip v-if="!editMode" content="编辑" placement="top">
              <el-button circle class="icon-btn" @click="enterEdit">
                <el-icon><Edit /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <div v-if="editMode" class="edit-stack">
            <el-input
              v-model="profile.synopsis"
              type="textarea"
              :rows="4"
              placeholder="故事主线与背景简介（勿写出版信息或书评）"
            />
            <el-button
              v-if="profile.synopsis"
              size="small"
              type="danger"
              plain
              @click="profile.synopsis = ''"
            >清空简介</el-button>
          </div>
          <div v-else class="read-card">
            <p v-if="profile.synopsis" class="synopsis-text">{{ profile.synopsis }}</p>
            <p v-else class="empty-line">暂无简介</p>
          </div>
        </section>

        <!-- 叙述 -->
        <section class="block">
          <div class="block-head">
            <h2>叙述</h2>
            <el-tooltip v-if="!editMode" content="编辑" placement="top">
              <el-button circle class="icon-btn" @click="enterEdit">
                <el-icon><Edit /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
          <div v-if="editMode" class="edit-stack">
            <el-input v-model="profile.narration.point_of_view" placeholder="人称 / 视角" />
            <el-input v-model="profile.narration.tone" placeholder="语气" />
            <el-input v-model="profile.narration.notes" type="textarea" :rows="2" placeholder="叙述说明" />
            <el-button size="small" type="danger" plain @click="clearNarration">清空叙述</el-button>
          </div>
          <div v-else class="read-card narrate-read">
            <div v-if="profile.narration.point_of_view || profile.narration.tone" class="meta-chips">
              <span v-if="profile.narration.point_of_view" class="chip">视角 · {{ profile.narration.point_of_view }}</span>
              <span v-if="profile.narration.tone" class="chip">语气 · {{ profile.narration.tone }}</span>
            </div>
            <p v-if="profile.narration.notes">{{ profile.narration.notes }}</p>
            <p v-else-if="!profile.narration.point_of_view && !profile.narration.tone" class="empty-line">暂无叙述信息</p>
          </div>
        </section>

        <!-- 人物 -->
        <section class="block">
          <div class="block-head">
            <h2>人物 <span class="count">{{ profile.characters.length }}</span></h2>
            <el-button size="small" type="primary" plain @click="addCharacter">
              <el-icon><Plus /></el-icon>
              添加人物
            </el-button>
          </div>
          <el-empty v-if="profile.characters.length === 0" description="还没有人物，可点击添加" :image-size="64" />
          <div v-for="(item, index) in profile.characters" :key="`c-${index}`" class="card character-card">
            <div class="card-title">
              <template v-if="editMode">
                <el-input v-model="item.name" placeholder="原名" class="title-input" />
                <el-input v-model="item.translation" placeholder="译名" class="title-input sm" />
              </template>
              <template v-else>
                <strong>{{ item.name || '未命名' }}</strong>
                <span v-if="item.translation" class="trans-name">{{ item.translation }}</span>
                <el-tag v-if="item.confirmed" size="small" type="success">译名已确认</el-tag>
              </template>
              <div class="item-actions">
                <el-tooltip v-if="!editMode" content="编辑" placement="top">
                  <el-button circle class="icon-btn" @click="enterEdit">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button circle class="icon-btn" type="danger" plain @click="removeCharacter(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>

            <template v-if="editMode">
              <div class="edit-stack">
                <el-input v-model="item.role" placeholder="身份 / 角色" />
                <el-input
                  :model-value="(item.aliases || []).join('、')"
                  placeholder="别称，用顿号分隔"
                  @update:model-value="(v: string) => { item.aliases = splitAliases(v) }"
                />
                <div class="portrait-block">
                  <div class="sub-label">人物画像</div>
                  <el-input
                    v-model="item.portrait"
                    type="textarea"
                    :rows="3"
                    placeholder="外貌、性格、身份背景、动机等"
                  />
                </div>
                <el-input
                  v-model="item.relations"
                  type="textarea"
                  :rows="2"
                  placeholder="关系摘要（自由描述）"
                />
                <div class="confirm-row">
                  <el-button size="small" type="primary" plain @click="confirmCharacter(item)">确认译名</el-button>
                </div>
              </div>
            </template>
            <template v-else>
              <span v-if="item.aliases?.length" class="muted">别称：{{ item.aliases.join('、') }}</span>
              <p v-if="item.role" class="role-line">{{ item.role }}</p>
              <div class="portrait-block">
                <div class="sub-label">人物画像</div>
                <p v-if="item.portrait" class="portrait-text">{{ item.portrait }}</p>
                <p v-else class="empty-line">暂无画像</p>
              </div>
              <p v-if="item.relations" class="muted">关系摘要：{{ item.relations }}</p>
              <div class="muted" v-if="item.paragraph_indexes?.length">依据段落：{{ formatIndexes(item.paragraph_indexes) }}</div>
            </template>
          </div>
        </section>

        <!-- 人物关系图 -->
        <section class="block">
          <div class="block-head">
            <h2>人物关系图 <span class="count">{{ profile.relationships.length }}</span></h2>
            <el-button size="small" type="primary" plain @click="addRelationship">
              <el-icon><Plus /></el-icon>
              添加关系
            </el-button>
          </div>
          <el-empty
            v-if="!graphEdges.length && !editMode"
            description="还没有人物关系，可点击添加"
            :image-size="64"
          />
          <div v-if="graphEdges.length || graphNodes.length" class="relation-graph">
            <svg
              class="graph-svg"
              :viewBox="`0 0 ${graphSize} ${graphSize}`"
              role="img"
              aria-label="人物关系图"
            >
              <line
                v-for="(edge, i) in graphLayout.edges"
                :key="`e-${i}`"
                :x1="edge.x1"
                :y1="edge.y1"
                :x2="edge.x2"
                :y2="edge.y2"
                class="graph-edge"
              />
              <text
                v-for="(edge, i) in graphLayout.edges"
                :key="`el-${i}`"
                :x="edge.mx"
                :y="edge.my"
                class="graph-edge-label"
              >{{ edge.label }}</text>
              <g v-for="(node, i) in graphLayout.nodes" :key="`n-${i}`">
                <circle :cx="node.x" :cy="node.y" r="28" class="graph-node" />
                <text :x="node.x" :y="node.y" class="graph-node-label">{{ node.label }}</text>
              </g>
            </svg>
          </div>

          <template v-if="!editMode">
            <ul v-if="graphEdges.length" class="relation-list">
              <li v-for="(edge, i) in graphEdges" :key="i">
                <strong>{{ edge.from }}</strong>
                <span class="rel-arrow">— {{ edge.relation }} →</span>
                <strong>{{ edge.to }}</strong>
                <span class="item-actions inline">
                  <el-tooltip content="编辑" placement="top">
                    <el-button circle class="icon-btn" @click="enterEdit">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="删除" placement="top">
                    <el-button circle class="icon-btn" type="danger" plain @click="removeRelationship(i)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-tooltip>
                </span>
              </li>
            </ul>
          </template>
          <div v-else class="edit-stack">
            <div v-for="(edge, index) in profile.relationships" :key="`r-${index}`" class="rel-edit-row">
              <el-input v-model="edge.from" placeholder="人物 A" />
              <el-input v-model="edge.relation" placeholder="关系" />
              <el-input v-model="edge.to" placeholder="人物 B" />
              <el-button link type="danger" @click="removeRelationship(index)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <el-empty v-if="profile.relationships.length === 0" description="暂无关系，点上方添加" :image-size="48" />
          </div>
        </section>

        <!-- 故事线 -->
        <section class="block">
          <div class="block-head">
            <h2>故事线 <span class="count">{{ profile.storylines.length }}</span></h2>
            <el-button size="small" type="primary" plain @click="addStoryline">
              <el-icon><Plus /></el-icon>
              添加故事线
            </el-button>
          </div>
          <el-empty v-if="profile.storylines.length === 0" description="还没有故事线，可点击添加" :image-size="64" />
          <div v-for="(item, index) in profile.storylines" :key="`s-${index}`" class="card">
            <div class="card-title">
              <template v-if="editMode">
                <el-input v-model="item.title" placeholder="故事线标题" class="title-input" />
                <el-input v-model="item.status" placeholder="状态" class="title-input sm" />
              </template>
              <template v-else>
                <strong>{{ item.title || '故事线' }}</strong>
                <el-tag v-if="item.status" size="small">{{ item.status }}</el-tag>
              </template>
              <div class="item-actions">
                <el-tooltip v-if="!editMode" content="编辑" placement="top">
                  <el-button circle class="icon-btn" @click="enterEdit">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button circle class="icon-btn" type="danger" plain @click="removeStoryline(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
            <el-input
              v-if="editMode"
              v-model="item.summary"
              type="textarea"
              :rows="3"
              placeholder="进展摘要"
            />
            <p v-else>{{ item.summary }}</p>
            <div class="muted" v-if="item.paragraph_indexes?.length">依据段落：{{ formatIndexes(item.paragraph_indexes) }}</div>
          </div>
        </section>

        <!-- 设定 -->
        <section class="block">
          <div class="block-head">
            <h2>设定 <span class="count">{{ profile.settings.length }}</span></h2>
            <el-button size="small" type="primary" plain @click="addSetting">
              <el-icon><Plus /></el-icon>
              添加设定
            </el-button>
          </div>
          <el-empty v-if="profile.settings.length === 0" description="还没有设定，可点击添加" :image-size="64" />
          <div v-for="(item, index) in profile.settings" :key="`set-${index}`" class="card">
            <div class="card-title">
              <el-input
                v-if="editMode"
                v-model="item.title"
                placeholder="设定标题"
                class="title-input"
              />
              <strong v-else>{{ item.title || '设定' }}</strong>
              <div class="item-actions">
                <el-tooltip v-if="!editMode" content="编辑" placement="top">
                  <el-button circle class="icon-btn" @click="enterEdit">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button circle class="icon-btn" type="danger" plain @click="removeSetting(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </div>
            <el-input
              v-if="editMode"
              v-model="item.detail"
              type="textarea"
              :rows="3"
              placeholder="设定详情（仅故事世界内事实）"
            />
            <p v-else>{{ item.detail }}</p>
            <div class="muted" v-if="item.paragraph_indexes?.length">依据段落：{{ formatIndexes(item.paragraph_indexes) }}</div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Plus, Delete, RefreshRight } from '@element-plus/icons-vue'
import { literaryApi } from '@/api'

const props = defineProps<{ translationId: number }>()
const emit = defineEmits<{ back: [] }>()

const loading = ref(false)
const saving = ref(false)
const regenerating = ref(false)
const editMode = ref(false)
const data = ref<any>(null)
const profile = ref<any>(emptyProfile())
const snapshot = ref('')
let timer: ReturnType<typeof setInterval> | null = null

const statusText = computed(() => ({
  pending: '待翻译',
  translating: '翻译中',
  verifying: '校验中',
  revising: '润色中',
  finalizing: '定稿中',
  completed: '已完成',
  failed: '失败',
} as Record<string, string>)[data.value?.status] || data.value?.status)

const graphSize = 420

function emptyProfile() {
  return {
    synopsis: '',
    characters: [],
    relationships: [],
    storylines: [],
    settings: [],
    narration: { point_of_view: '', tone: '', notes: '' },
    updated_through_index: -1,
  }
}

const formatIndexes = (indexes: number[]) => indexes.map((n) => `第${n}段`).join('、')

const splitAliases = (value: string) =>
  value.split(/[、,，;；]/).map((s) => s.trim()).filter(Boolean)

const graphEdges = computed(() =>
  (profile.value.relationships || []).filter((e: any) => e.from && e.to && e.relation)
)

const graphNodes = computed(() => {
  const names = new Set<string>()
  for (const c of profile.value.characters || []) {
    if (c.name) names.add(c.name)
  }
  for (const e of graphEdges.value) {
    names.add(e.from)
    names.add(e.to)
  }
  return [...names]
})

const graphLayout = computed(() => {
  const names = graphNodes.value
  const n = names.length
  const cx = graphSize / 2
  const cy = graphSize / 2
  const radius = n <= 1 ? 0 : Math.min(148, 40 + n * 12)
  const nodes = names.map((name, i) => {
    const angle = n === 0 ? 0 : (Math.PI * 2 * i) / n - Math.PI / 2
    return {
      name,
      label: name.length > 6 ? `${name.slice(0, 5)}…` : name,
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })
  const byName = Object.fromEntries(nodes.map((node) => [node.name, node]))
  const edges = graphEdges.value.map((e: any) => {
    const a = byName[e.from]
    const b = byName[e.to]
    if (!a || !b) return null
    return {
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      mx: (a.x + b.x) / 2,
      my: (a.y + b.y) / 2 - 6,
      label: e.relation,
    }
  }).filter(Boolean)
  return { nodes, edges }
})

const normalizeIncoming = (raw: any) => {
  const next = { ...emptyProfile(), ...(raw || {}) }
  next.synopsis = next.synopsis || ''
  next.characters = (next.characters || []).map((c: any) => ({
    name: c.name || '',
    aliases: c.aliases || [],
    role: c.role || '',
    portrait: c.portrait || '',
    relations: c.relations || '',
    translation: c.translation || '',
    confirmed: !!c.confirmed,
    paragraph_indexes: c.paragraph_indexes || [],
  }))
  next.relationships = (next.relationships || []).map((r: any) => ({
    from: r.from || r.source || '',
    to: r.to || r.target || '',
    relation: r.relation || r.type || '',
  }))
  next.storylines = (next.storylines || []).map((s: any) => ({
    title: s.title || '',
    summary: s.summary || '',
    status: s.status || '',
    paragraph_indexes: s.paragraph_indexes || [],
  }))
  next.settings = (next.settings || []).map((s: any) => ({
    title: s.title || '',
    detail: s.detail || '',
    paragraph_indexes: s.paragraph_indexes || [],
  }))
  next.narration = {
    point_of_view: next.narration?.point_of_view || '',
    tone: next.narration?.tone || '',
    notes: next.narration?.notes || '',
  }
  return next
}

const load = async () => {
  if (!props.translationId) return
  loading.value = true
  try {
    const res = await literaryApi.getStoryProfile(props.translationId)
    data.value = res.data
    profile.value = normalizeIncoming(res.data.profile)
    snapshot.value = JSON.stringify(profile.value)
  } catch {
    ElMessage.error('加载故事结构失败')
  } finally {
    loading.value = false
  }
}

const save = async (keepEdit = false) => {
  if (!props.translationId) return
  saving.value = true
  try {
    const res = await literaryApi.updateStoryProfile(props.translationId, profile.value)
    profile.value = normalizeIncoming(res.data.profile)
    snapshot.value = JSON.stringify(profile.value)
    if (!keepEdit) editMode.value = false
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const enterEdit = () => {
  editMode.value = true
}

const regenerate = async () => {
  if (!props.translationId || regenerating.value) return
  try {
    await ElMessageBox.confirm(
      '将按全部原文重新生成故事结构（简介、人物、关系、故事线、设定）。已确认的人物译名会保留，其余内容会被覆盖。是否继续？',
      '重新生成故事结构',
      { type: 'warning', confirmButtonText: '重新生成', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  regenerating.value = true
  editMode.value = false
  try {
    const res = await literaryApi.regenerateStoryProfile(props.translationId)
    data.value = res.data
    profile.value = normalizeIncoming(res.data.profile)
    snapshot.value = JSON.stringify(profile.value)
    ElMessage.success('故事结构已根据原文重新生成')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '重新生成失败')
  } finally {
    regenerating.value = false
  }
}

const cancelEdit = () => {
  try {
    profile.value = normalizeIncoming(JSON.parse(snapshot.value || '{}'))
  } catch {
    /* keep */
  }
  editMode.value = false
}

const clearNarration = () => {
  profile.value.narration = { point_of_view: '', tone: '', notes: '' }
}

const confirmRemove = async (label: string) => {
  try {
    await ElMessageBox.confirm(`确定删除该${label}？`, '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    return true
  } catch {
    return false
  }
}

const addCharacter = () => {
  editMode.value = true
  profile.value.characters.push({
    name: '',
    aliases: [],
    role: '',
    portrait: '',
    relations: '',
    translation: '',
    confirmed: false,
    paragraph_indexes: [],
  })
}

const removeCharacter = async (index: number) => {
  if (!(await confirmRemove('人物'))) return
  profile.value.characters.splice(index, 1)
  if (!editMode.value) await save()
}

const confirmCharacter = async (item: any) => {
  if (!item.translation?.trim()) {
    ElMessage.warning('请先填写译名')
    return
  }
  item.confirmed = true
  await save(true)
}

const addRelationship = () => {
  editMode.value = true
  profile.value.relationships.push({ from: '', to: '', relation: '' })
}

const removeRelationship = async (index: number) => {
  if (!(await confirmRemove('关系'))) return
  // read-mode list uses filtered graphEdges; map back to raw index when needed
  if (!editMode.value) {
    const edge = graphEdges.value[index]
    const rawIndex = profile.value.relationships.findIndex(
      (r: any) => r.from === edge.from && r.to === edge.to && r.relation === edge.relation
    )
    if (rawIndex >= 0) profile.value.relationships.splice(rawIndex, 1)
    await save()
    return
  }
  profile.value.relationships.splice(index, 1)
}

const addStoryline = () => {
  editMode.value = true
  profile.value.storylines.push({
    title: '',
    summary: '',
    status: '进行中',
    paragraph_indexes: [],
  })
}

const removeStoryline = async (index: number) => {
  if (!(await confirmRemove('故事线'))) return
  profile.value.storylines.splice(index, 1)
  if (!editMode.value) await save()
}

const addSetting = () => {
  editMode.value = true
  profile.value.settings.push({
    title: '',
    detail: '',
    paragraph_indexes: [],
  })
}

const removeSetting = async (index: number) => {
  if (!(await confirmRemove('设定'))) return
  profile.value.settings.splice(index, 1)
  if (!editMode.value) await save()
}

watch(() => props.translationId, () => {
  editMode.value = false
  load()
}, { immediate: true })

timer = setInterval(() => {
  if (editMode.value || regenerating.value) return
  const running = ['translating', 'verifying', 'revising', 'finalizing'].includes(data.value?.status)
  if (running) load()
}, 15000)

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped lang="scss">
.story-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  min-height: 0;
}

.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 920px;
  width: 100%;
  margin: 0 auto;
}

.hint {
  color: var(--ins-muted);
  font-size: 14px;
  margin: 0 0 20px;
}

.block {
  margin-bottom: 28px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;

  h2 {
    margin: 0;
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -0.02em;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.count {
  font-size: 12px;
  font-weight: 600;
  color: var(--ins-muted);
  background: var(--ins-bg);
  border-radius: 999px;
  padding: 2px 8px;
}

.edit-stack {
  display: grid;
  gap: 10px;
}

.read-card,
.card {
  background: var(--ins-surface);
  border: 1px solid var(--ins-line);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: var(--ins-shadow-sm);

  p {
    margin: 6px 0 0;
    line-height: 1.7;
    color: var(--ins-ink);
  }
}

.synopsis-text {
  font-size: 15px;
  line-height: 1.85;
  white-space: pre-wrap;
}

.meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 4px;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
}

.character-card .trans-name {
  color: var(--el-color-primary);
  font-weight: 600;
  font-size: 13px;
}

.role-line {
  font-size: 14px;
  color: var(--ins-ink-2);
}

.portrait-block {
  margin-top: 4px;
  padding: 12px;
  border-radius: 8px;
  background: var(--ins-bg);
  border: 1px dashed var(--ins-line-strong);
}

.sub-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ins-muted);
  margin-bottom: 8px;
}

.portrait-text {
  margin: 0 !important;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.75;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.item-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;

  &.inline {
    margin-left: 12px;
  }

  .icon-btn {
    width: 28px !important;
    height: 28px !important;
    min-height: 28px !important;
  }
}

.title-input {
  flex: 1;
  min-width: 140px;

  &.sm {
    flex: 0 0 140px;
  }
}

.confirm-row {
  display: flex;
  gap: 8px;
}

.muted {
  color: var(--ins-muted);
  font-size: 13px;
  margin-top: 6px;
  display: block;
}

.empty-line {
  color: var(--ins-muted) !important;
  font-size: 13px;
  margin: 0 !important;
}

.relation-graph {
  background: var(--ins-surface);
  border: 1px solid var(--ins-line);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
  box-shadow: var(--ins-shadow-sm);
}

.graph-svg {
  width: 100%;
  max-width: 480px;
  height: auto;
  display: block;
  margin: 0 auto;
}

.graph-edge {
  stroke: var(--ins-line-strong);
  stroke-width: 1.5;
}

.graph-edge-label {
  fill: var(--ins-muted);
  font-size: 11px;
  text-anchor: middle;
}

.graph-node {
  fill: var(--el-color-primary-light-9);
  stroke: var(--el-color-primary);
  stroke-width: 1.5;
}

.graph-node-label {
  fill: var(--ins-ink);
  font-size: 11px;
  font-weight: 700;
  text-anchor: middle;
  dominant-baseline: middle;
}

.relation-list {
  list-style: none;
  margin: 0 0 12px;
  padding: 0;

  li {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    padding: 8px 0;
    border-bottom: 1px dashed var(--ins-line);
    font-size: 14px;
    color: var(--ins-ink);
  }
}

.rel-arrow {
  margin: 0 6px;
  color: var(--ins-muted);
  font-size: 13px;
}

.rel-edit-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 8px;
  align-items: center;
}
</style>
