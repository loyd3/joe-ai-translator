<template>
  <div class="literary-view">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <div class="brand-wrap">
          <div class="logo-mark" aria-hidden="true">译</div>
          <div class="brand-text">
            <span class="brand">译智通</span>
            <span class="brand-sub">AI 智能翻译</span>
          </div>
        </div>
        <div class="header-btns">
          <el-button v-if="batchMode" text size="small" @click="exitBatchMode">取消</el-button>
          <el-button
            v-if="batchMode && selectedTaskIds.length > 0"
            type="primary"
            size="small"
            @click="startBatchWorkflow"
            :loading="batchStarting"
          >翻译 {{ selectedTaskIds.length }} 项</el-button>
          <el-tooltip v-if="!batchMode" content="批量翻译" placement="top">
            <el-button circle class="icon-btn" @click="enterBatchMode">
              <el-icon><List /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="新建任务" placement="top">
            <el-button type="primary" circle class="icon-btn" @click="createNewTask">
              <el-icon><Plus /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="批量上传文件" placement="top">
            <el-button circle class="icon-btn" @click="openBatchUpload">
              <el-icon><Upload /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <div class="category-filter">
        <el-radio-group v-model="categoryGroup" class="category-group">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="literary">文学</el-radio-button>
          <el-radio-button label="professional">专业</el-radio-button>
        </el-radio-group>
      </div>

      <div class="task-list" v-loading="loadingTasks">
        <div
          v-for="task in filteredTaskList"
          :key="task.id"
          :class="['task-item', { active: !batchMode && currentTask?.id === task.id, selected: batchMode && selectedTaskIds.includes(task.id) }]"
          @click="batchMode ? toggleTaskSelection(task.id) : selectTask(task)"
        >
          <el-checkbox
            v-if="batchMode"
            :model-value="selectedTaskIds.includes(task.id)"
            @click.stop
            @change="toggleTaskSelection(task.id)"
            class="task-checkbox"
            :disabled="isTaskRunning(task.status)"
          />
          <div class="task-info">
            <div class="task-title">{{ task.title || `任务 #${task.id}` }}</div>
            <div class="task-meta">
              <el-tag size="small" :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
              <el-tag size="small" :type="isLiteraryType(task.literary_type) ? '' : 'warning'" effect="plain" round>{{ getTypeName(task.literary_type) }}</el-tag>
            </div>
          </div>
          <div class="task-actions" v-if="!batchMode" @click.stop>
            <el-button link size="small" @click="openEditTaskDialog(task)"><el-icon><Edit /></el-icon></el-button>
            <el-button link type="danger" size="small" @click="confirmDeleteTask(task)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
        <el-empty v-if="filteredTaskList.length === 0" description="暂无任务" :image-size="60" />
      </div>

      <div class="sidebar-footer-row">
        <div class="sidebar-footer" @click="openThemeSettings">
          <el-icon><Sunny /></el-icon>
          <span>主题设置</span>
        </div>
        <div class="sidebar-footer" @click="goToStylePage">
          <el-icon><Brush /></el-icon>
          <span>文风设定</span>
        </div>
        <div class="sidebar-footer" @click="goToAIConfigPage">
          <el-icon><Setting /></el-icon>
          <span>大模型配置</span>
          <el-tag v-if="aiConfigInfo.provider" size="small" type="info" effect="plain" round>{{ aiConfigInfo.provider }}</el-tag>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <TermLibraryView
        v-if="panelMode === 'terms'"
        :translation-id="currentTask?.id"
        :literary-type="currentTask?.literary_type"
        :source-lang="currentTask?.source_lang"
        :target-lang="currentTask?.target_lang"
        @back="closePanel"
      />
      <StoryStructurePanel
        v-else-if="panelMode === 'story' && currentTask?.id"
        :translation-id="currentTask.id"
        @back="closePanel"
      />
      <StyleAgentsView
        v-else-if="panelMode === 'style'"
        @back="closePanel"
      />
      <AIConfigView
        v-else-if="panelMode === 'ai-config'"
        @back="closePanel"
        @saved="loadAIConfig"
      />
      <LiteraryResultView
        v-else-if="panelMode === 'result' && currentTask?.id"
        :translation-id="currentTask.id"
        @back="closePanel"
      />
      <template v-else>
      <!-- 空状态 -->
      <div v-if="!currentTask" class="empty-state" @click="createNewTask">
        <div class="empty-card">
          <div class="empty-orb">译</div>
          <h2>{{ categoryGroup === 'professional' ? '创建专业翻译任务' : '创建文学翻译任务' }}</h2>
          <p>{{ categoryGroup === 'professional' ? '科技、商业、贸易、法律、医学等专业领域精译' : '诗歌、散文、小说、戏剧等文学作品精译' }}</p>
          <span class="empty-cta">点击开始</span>
        </div>
      </div>

      <!-- 工作区 -->
      <template v-else>
        <div class="workspace" v-loading="workflowLoading">
          <!-- 顶栏 -->
          <div class="top-bar">
            <div class="bar-left">
              <el-select v-model="currentTask.source_lang" size="small" class="lang-sel">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
              <el-icon class="arrow"><ArrowRight /></el-icon>
              <el-select v-model="currentTask.target_lang" size="small" class="lang-sel">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>

              <el-tag
                size="small"
                :type="isLiteraryType(currentTask.literary_type) ? '' : 'warning'"
                effect="plain"
                round
                class="type-badge"
              >{{ getTypeName(currentTask.literary_type) }}</el-tag>

              <el-divider direction="vertical" />

              <div class="step-dots">
                <div v-for="(s, i) in stepItems" :key="i" :class="['dot-item', s.state]">
                  <span class="dot" />
                  <span class="dot-label">{{ s.label }}</span>
                </div>
              </div>

              <el-tooltip v-if="canStartWorkflow" :content="currentTask.status === 'failed' ? '重新翻译' : '开始翻译'" placement="bottom">
                <el-button type="primary" circle class="icon-btn" @click="startWorkflow" :loading="processing">
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip v-else-if="isWorkflowRunning" content="终止流程" placement="bottom">
                <el-button type="danger" circle class="icon-btn" @click="stopWorkflow" :loading="processing">
                  <el-icon><VideoPause /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tag v-if="isWorkflowRunning" type="warning" effect="plain" round>{{ getStatusText(currentTask.status) }}</el-tag>
              <el-tag v-else-if="currentTask.status === 'completed'" type="success" effect="plain" round>已完成</el-tag>
              <el-tag v-if="workflowLoading" type="info" effect="plain" round>加载中</el-tag>

              <el-tag v-if="isWorkflowRunning && paraProgress.total > 0" type="info" effect="plain" round>
                {{ paraProgress.done }}/{{ paraProgress.total }} 段
              </el-tag>
            </div>

            <div class="bar-right">
              <el-popover v-if="hasBeautyScores" placement="bottom" :width="200" trigger="hover">
                <template #reference>
                  <el-button circle class="icon-btn">
                    <el-icon><Trophy /></el-icon>
                  </el-button>
                </template>
                <div class="score-popover">
                  <template v-if="isLiteraryType(currentTask.literary_type)">
                    <div class="score-row"><span>音美</span><span>{{ beautyScores.sound.toFixed(1) }}</span></div>
                    <div class="score-row"><span>词美</span><span>{{ beautyScores.word.toFixed(1) }}</span></div>
                    <div class="score-row"><span>意美</span><span>{{ beautyScores.meaning.toFixed(1) }}</span></div>
                  </template>
                  <template v-else>
                    <div class="score-row"><span>术语</span><span>{{ beautyScores.sound.toFixed(1) }}</span></div>
                    <div class="score-row"><span>规范</span><span>{{ beautyScores.word.toFixed(1) }}</span></div>
                    <div class="score-row"><span>完整</span><span>{{ beautyScores.meaning.toFixed(1) }}</span></div>
                  </template>
                </div>
              </el-popover>
              <el-tooltip content="定稿" placement="bottom">
                <el-button circle class="icon-btn" @click="goToResultPage">
                  <el-icon><Document /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip v-if="isStoryType(currentTask.literary_type)" content="故事结构" placement="bottom">
                <el-button circle class="icon-btn" @click="goToStoryPage">
                  <el-icon><Memo /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="词库" placement="bottom">
                <el-button circle class="icon-btn" @click="goToTermLibrary">
                  <el-icon><Collection /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="翻译风格" placement="bottom">
                <el-button circle class="icon-btn" @click="goToStylePage">
                  <el-icon><Brush /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>

          <div class="compare-toolbar">
            <div class="icon-switch">
              <el-tooltip content="分段对照" placement="bottom">
                <el-button
                  circle
                  class="icon-btn"
                  :type="compareMode === 'segment' ? 'primary' : 'default'"
                  @click="setCompareMode('segment')"
                >
                  <el-icon><Grid /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="全文对照" placement="bottom">
                <el-button
                  circle
                  class="icon-btn"
                  :type="compareMode === 'full' ? 'primary' : 'default'"
                  @click="setCompareMode('full')"
                >
                  <el-icon><DocumentCopy /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
            <el-tabs
              v-if="compareMode === 'segment' && pageCount > 0"
              v-model="activePageTab"
              class="segment-tabs"
            >
              <el-tab-pane
                v-for="page in pageCount"
                :key="page"
                :label="pageTabLabel(page)"
                :name="String(page)"
              />
            </el-tabs>
          </div>

          <!-- 编辑区 -->
          <div class="edit-area" v-if="compareMode === 'segment'">
            <div class="panel source-panel">
              <div class="panel-header">
                <span>原文</span>
                <el-tag size="small" type="info">{{ currentTask.source_lang }}</el-tag>
              </div>
              <div class="panel-body" ref="sourceBodyRef" v-loading="loadingParagraphs">
                <div
                  v-for="para in paragraphs"
                  :key="para.id"
                  :class="['para-item', 'source-block', { active: para.id === selectedParagraphId }]"
                  @click="selectParagraph(para)"
                >
                  <div class="para-index">第 {{ para.paragraph_index + 1 }} 段</div>
                  <div class="para-source">{{ para.source_text }}</div>
                </div>
                <div v-if="!loadingParagraphs && paragraphs.length === 0" class="no-content">暂无原文</div>
              </div>
            </div>
            <div class="panel trans-panel">
              <div class="panel-header">
                <span>译文 · {{ pageTabLabel(paragraphPage) }}</span>
                <div class="icon-switch">
                  <el-tooltip content="阅读" placement="bottom">
                    <el-button
                      circle
                      class="icon-btn"
                      :type="rightMode === 'read' ? 'primary' : 'default'"
                      @click="setRightMode('read')"
                    >
                      <el-icon><View /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="编辑" placement="bottom">
                    <el-button
                      circle
                      class="icon-btn"
                      :type="rightMode === 'bulk' ? 'primary' : 'default'"
                      @click="setRightMode('bulk')"
                    >
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </div>
              <div class="panel-body" ref="transBodyRef" v-loading="loadingParagraphs">
                <div
                  v-for="para in paragraphs"
                  :key="para.id"
                  :id="`trans-para-${para.id}`"
                  :class="['version-block', { active: para.id === selectedParagraphId }]"
                >
                  <div class="version-label">
                    <span>第 {{ para.paragraph_index + 1 }} 段</span>
                    <div class="version-actions">
                      <el-tooltip content="AI 重译" placement="top">
                        <el-button
                          circle
                          class="icon-btn"
                          :loading="retranslatingId === para.id"
                          :disabled="!!retranslatingId && retranslatingId !== para.id"
                          @click.stop="retranslateParagraph(para)"
                        >
                          <el-icon v-if="retranslatingId !== para.id"><RefreshRight /></el-icon>
                        </el-button>
                      </el-tooltip>
                      <el-tooltip :content="miniEditId === para.id ? '完成' : '编辑'" placement="top">
                        <el-button
                          v-if="rightMode === 'read'"
                          circle
                          class="icon-btn"
                          :type="miniEditId === para.id ? 'primary' : 'default'"
                          :disabled="retranslatingId === para.id"
                          @click.stop="toggleMiniEdit(para)"
                        >
                          <el-icon>
                            <Select v-if="miniEditId === para.id" />
                            <Edit v-else />
                          </el-icon>
                        </el-button>
                      </el-tooltip>
                    </div>
                  </div>
                  <el-input
                    v-if="rightMode === 'bulk' || miniEditId === para.id"
                    v-model="para.editedText"
                    type="textarea"
                    :autosize="{ minRows: 3, maxRows: 16 }"
                    placeholder="该段译文"
                    @input="para.dirty = true"
                    @blur="saveParagraph(para)"
                  />
                  <pre v-else-if="para.editedText">{{ para.editedText }}</pre>
                  <div v-else class="version-empty">暂无译文</div>
                </div>
                <div v-if="!loadingParagraphs && paragraphs.length === 0" class="no-content">暂无译文</div>
              </div>
            </div>
          </div>
          <div class="edit-area" v-else v-loading="loadingFull">
            <div class="panel source-panel">
              <div class="panel-header">
                <span>原文</span>
                <el-tag size="small" type="info">{{ currentTask.source_lang }}</el-tag>
              </div>
              <div class="panel-body">
                <pre v-if="fullSource">{{ fullSource }}</pre>
                <div v-else-if="!loadingFull" class="no-content">暂无原文</div>
              </div>
            </div>
            <div class="panel trans-panel">
              <div class="panel-header">
                <span>译文</span>
                <el-tag size="small" type="success">{{ currentTask.target_lang }}</el-tag>
              </div>
              <div class="panel-body">
                <pre v-if="fullTranslation">{{ fullTranslation }}</pre>
                <div v-else-if="!loadingFull" class="no-content">暂无译文</div>
              </div>
            </div>
          </div>
        </div>
      </template>
      </template>
    </div>

    <el-dialog v-model="showExport" title="导出译文" width="440px">
      <el-form label-position="top">
        <el-form-item label="格式">
          <el-radio-group v-model="exportFormat">
            <el-radio-button label="txt">TXT</el-radio-button>
            <el-radio-button label="md">Markdown</el-radio-button>
            <el-radio-button label="html">HTML</el-radio-button>
            <el-radio-button label="json">JSON</el-radio-button>
            <el-radio-button label="csv">CSV</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportWithSource">包含原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" @click="exportTranslation" :loading="exporting">导出</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateDialog" :title="categoryGroup === 'professional' ? '新建专业翻译任务' : '新建文学翻译任务'" width="600px" destroy-on-close>
      <el-form :model="newTaskForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标题（选填）">
              <el-input v-model="newTaskForm.title" placeholder="如：第一章" maxlength="200" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="翻译类型">
              <el-select v-model="newTaskForm.literary_type" style="width: 100%;">
                <el-option-group label="文学">
                  <el-option label="一般" value="general" />
                  <el-option label="诗歌" value="poetry" />
                  <el-option label="散文" value="prose" />
                  <el-option label="小说" value="novel" />
                  <el-option label="戏剧" value="drama" />
                </el-option-group>
                <el-option-group label="专业">
                  <el-option label="科技" value="tech" />
                  <el-option label="商业" value="business" />
                  <el-option label="贸易" value="trade" />
                  <el-option label="法律" value="legal" />
                  <el-option label="医学" value="medical" />
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源语言">
              <el-select v-model="newTaskForm.source_lang" style="width: 100%;">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标语言">
              <el-select v-model="newTaskForm.target_lang" style="width: 100%;">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="文风设定">
          <StyleAgentPicker
            v-model="newTaskForm.style_agent_id"
            :label="''"
            default-label="系统默认"
            :reload-token="stylePickerReloadToken"
            @manage="openStyleFromCreate"
          />
          <p class="form-hint">先贴合原文风格，再叠加所选译者习惯（如多用成语、短句）。</p>
        </el-form-item>
        <el-form-item label="翻译需求（选填）">
          <el-input v-model="newTaskForm.user_requirements" type="textarea" :rows="2" placeholder="如：偏书面语、保留专有名词原文、统一某术语译法等" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="原文">
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :accept="uploadAccept"
            :limit="1"
            :on-change="onCreateFileSelect"
            :on-exceed="() => ElMessage.warning('仅支持一个文件')"
            class="inline-upload"
          >
            <el-button size="small" link type="primary">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
          </el-upload>
          <el-input v-model="newTaskForm.source_text" type="textarea" :rows="8" placeholder="粘贴要翻译的文本，或上传文件自动填入..." />
          <div class="text-stats" v-if="newTaskForm.source_text.length > 0">
            <span>{{ newTaskForm.source_text.length.toLocaleString() }} 字符</span>
            <span>·</span>
            <span>约 {{ estimatedParagraphs }} 段</span>
            <el-tag v-if="newTaskForm.source_text.length > 10000" size="small" type="info" effect="plain">大文本自动智能分段</el-tag>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 批量上传对话框 -->
    <el-dialog v-model="showBatchUploadDialog" title="批量上传文件" width="560px" destroy-on-close @close="batchFileList = []">
      <el-form :model="batchUploadForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源语言">
              <el-select v-model="batchUploadForm.source_lang" style="width: 100%;">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标语言">
              <el-select v-model="batchUploadForm.target_lang" style="width: 100%;">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="翻译类型">
          <el-select v-model="batchUploadForm.literary_type" style="width: 100%;">
            <el-option-group label="文学">
              <el-option label="一般" value="general" />
              <el-option label="诗歌" value="poetry" />
              <el-option label="散文" value="prose" />
              <el-option label="小说" value="novel" />
              <el-option label="戏剧" value="drama" />
            </el-option-group>
            <el-option-group label="专业">
              <el-option label="科技" value="tech" />
              <el-option label="商业" value="business" />
              <el-option label="贸易" value="trade" />
              <el-option label="法律" value="legal" />
              <el-option label="医学" value="medical" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="文风设定">
          <StyleAgentPicker
            v-model="batchUploadForm.style_agent_id"
            :label="''"
            default-label="系统默认"
            :show-manage-link="false"
            :reload-token="stylePickerReloadToken"
          />
          <p class="form-hint">先贴合原文风格，再叠加所选译者习惯。</p>
        </el-form-item>
        <el-form-item label="翻译需求（选填）">
          <el-input v-model="batchUploadForm.user_requirements" type="textarea" :rows="2" placeholder="如：偏书面语、保留专有名词原文" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="上传后自动执行四步流程">
          <el-switch v-model="batchUploadForm.auto_run" />
        </el-form-item>
        <el-form-item label="选择文件">
          <el-upload
            ref="batchUploadRef"
            :auto-upload="false"
            :file-list="batchFileList"
            :on-change="onBatchFileChange"
            :on-remove="onBatchFileRemove"
            :accept="uploadAccept"
            :limit="50"
            multiple
            drag
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 txt、docx、pdf、mobi、md 等，单文件最大 20MB，最多 50 个</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="submitBatchUpload" :loading="batchUploading" :disabled="batchFileList.length === 0">
          开始上传 ({{ batchFileList.length }} 个文件)
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditTask" title="修改任务" width="400px" destroy-on-close>
      <el-form v-if="editingTask" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" placeholder="选填" maxlength="200" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%;">
            <el-option label="待开始" value="pending" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditTask = false">取消</el-button>
        <el-button type="primary" @click="submitEditTask">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, inject } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Upload, Document, Plus, List, Setting, Collection, Memo, Brush, VideoPlay, VideoPause, Trophy, Grid, DocumentCopy, View, Select, Sunny, RefreshRight } from '@element-plus/icons-vue'
import { literaryApi, translateApi, systemApi } from '@/api'
import TermLibraryView from '@/views/TermLibraryView.vue'
import StoryStructurePanel from '@/components/StoryStructurePanel.vue'
import StyleAgentsView from '@/views/StyleAgentsView.vue'
import StyleAgentPicker from '@/components/StyleAgentPicker.vue'
import AIConfigView from '@/views/AIConfigView.vue'
import LiteraryResultView from '@/views/LiteraryResultView.vue'

const openThemeSettings = inject<() => void>('openThemeSettings', () => {})

const languages = ref<{ code: string; name: string }[]>([])
const taskList = ref<any[]>([])
const currentTask = ref<any>(null)
const paragraphs = ref<any[]>([])
const paragraphPage = ref(1)
const paragraphTotal = ref(0)
const loadingParagraphs = ref(false)
const compareMode = ref<'segment' | 'full'>('segment')
const selectedParagraphId = ref<number | null>(null)
const rightMode = ref<'read' | 'bulk'>('read')
const miniEditId = ref<number | null>(null)
const retranslatingId = ref<number | null>(null)
const panelMode = ref<'workspace' | 'terms' | 'story' | 'style' | 'ai-config' | 'result'>('workspace')
const stylePickerReloadToken = ref(0)
const fullSource = ref('')
const fullTranslation = ref('')
const loadingFull = ref(false)
const PAGE_SIZE = 20
const sourceBodyRef = ref<HTMLElement | null>(null)
const transBodyRef = ref<HTMLElement | null>(null)
const loadingTasks = ref(false)
const processing = ref(false)
const creating = ref(false)
const exporting = ref(false)
const showExport = ref(false)
const showCreateDialog = ref(false)
const showEditTask = ref(false)
const editingTask = ref<any>(null)
const editForm = ref({ title: '', status: '' })
const exportFormat = ref('txt')
const exportWithSource = ref(false)

const batchMode = ref(false)
const selectedTaskIds = ref<number[]>([])
const batchStarting = ref(false)

const LITERARY_TYPES = new Set(['poetry', 'prose', 'novel', 'drama', 'general'])
const STORY_TYPES = new Set(['novel', 'drama', 'prose', 'general'])
const categoryGroup = ref<string>('literary')

const showBatchUploadDialog = ref(false)
const batchUploading = ref(false)
const batchUploadRef = ref<any>(null)
const batchFileList = ref<any[]>([])
const batchUploadForm = ref({
  source_lang: 'auto',
  target_lang: 'en',
  literary_type: 'general' as string,
  user_requirements: '',
  style_agent_id: undefined as number | undefined,
  auto_run: true,
})
const aiConfigInfo = ref<any>({ provider: '', source: '', has_api_key: false, api_key_masked: '' })

async function loadAIConfig() {
  try {
    const res = await systemApi.getAIConfig()
    aiConfigInfo.value = res.data
  } catch { /* ignore */ }
}

function openBatchUpload() {
  batchUploadForm.value = {
    source_lang: 'auto',
    target_lang: 'en',
    literary_type: categoryGroup.value === 'professional' ? 'tech' : 'general',
    user_requirements: '',
    style_agent_id: undefined,
    auto_run: true,
  }
  batchFileList.value = []
  showBatchUploadDialog.value = true
}

function onBatchFileChange(_uploadFile: any, uploadFiles: any[]) {
  batchFileList.value = uploadFiles
}

function onBatchFileRemove(_uploadFile: any, uploadFiles: any[]) {
  batchFileList.value = uploadFiles
}

async function submitBatchUpload() {
  const files = batchFileList.value.map((f: any) => f.raw).filter(Boolean)
  if (files.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }
  batchUploading.value = true
  try {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    form.append('source_lang', batchUploadForm.value.source_lang)
    form.append('target_lang', batchUploadForm.value.target_lang)
    form.append('literary_type', batchUploadForm.value.literary_type)
    form.append('auto_run', String(batchUploadForm.value.auto_run))
    if (batchUploadForm.value.user_requirements?.trim()) {
      form.append('user_requirements', batchUploadForm.value.user_requirements.trim())
    }
    if (batchUploadForm.value.style_agent_id != null) {
      form.append('style_agent_id', String(batchUploadForm.value.style_agent_id))
    }
    const res = await literaryApi.uploadAndTranslateBatch(form)
    const data = res.data
    const ok = data.results?.filter((r: any) => r.translation_id).length ?? 0
    const err = data.results?.filter((r: any) => r.error).length ?? 0
    ElMessage.success(data.message || `成功 ${ok} 个${err ? `，失败 ${err} 个` : ''}`)
    showBatchUploadDialog.value = false
    batchFileList.value = []
    await loadTasks(true)
    const firstId = data.results?.find((r: any) => r.translation_id)?.translation_id
    if (firstId) await selectTask(taskList.value.find((t: any) => t.id === firstId))
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '批量上传失败')
  } finally {
    batchUploading.value = false
  }
}

const filteredTaskList = computed(() => {
  if (categoryGroup.value === 'all') return taskList.value
  if (categoryGroup.value === 'literary') return taskList.value.filter((t: any) => LITERARY_TYPES.has(t.literary_type || 'general'))
  return taskList.value.filter((t: any) => !LITERARY_TYPES.has(t.literary_type || 'general'))
})

const TYPE_LABELS: Record<string, string> = {
  poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般',
  tech: '科技', business: '商业', trade: '贸易', legal: '法律', medical: '医学',
}
const getTypeName = (type: string) => TYPE_LABELS[type] || type
const isLiteraryType = (type: string) => LITERARY_TYPES.has(type || 'general')
const isStoryType = (type: string) => STORY_TYPES.has(type || '')

const newTaskForm = ref({
  title: '',
  source_text: '',
  source_lang: 'en',
  target_lang: 'zh',
  literary_type: 'general' as string,
  user_requirements: '',
  style_agent_id: undefined as number | undefined,
})
const uploadAccept = '.txt,.md,.doc,.docx,.pdf,.mobi,.azw,.html,.htm,.xml,.json,.csv,.yaml,.yml,.rst,.tex,.srt,.vtt,.log,.ini,.cfg'
const MAX_FILE_SIZE = 10 * 1024 * 1024
const MAX_TEXT_CHARS = 1000000

const estimatedParagraphs = computed(() => {
  const text = newTaskForm.value.source_text
  if (!text) return 0
  const paras = text.split(/\n\n+/).filter((p: string) => p.trim())
  let count = 0
  for (const p of paras) {
    count += Math.max(1, Math.ceil(p.length / 2000))
  }
  return count || 1
})

const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))

const currentStep = computed(() => {
  const task = currentTask.value
  if (!task) return 0
  if (task.status === 'completed') return 4
  return Math.max(0, (task.current_step || 1) - 1)
})

const canStartWorkflow = computed(() => {
  const s = currentTask.value?.status
  return s === 'pending' || s === 'failed'
})

const isWorkflowRunning = computed(() =>
  ['translating', 'verifying', 'revising', 'finalizing'].includes(currentTask.value?.status)
)

const paraProgress = ref<{ total: number; done: number }>({ total: 0, done: 0 })
const workflowLoading = ref(false)

const stepItems = computed(() => {
  const labels = ['翻译', '校验', '润色', '定稿']
  const statusMap: Record<string, number> = { translating: 0, verifying: 1, revising: 2, finalizing: 3 }
  const active = currentStep.value
  const runningIdx = statusMap[currentTask.value?.status] ?? -1

  return labels.map((label, i) => {
    let state = 'pending'
    if (i < active) state = 'done'
    else if (i === runningIdx) state = 'running'
    else if (currentTask.value?.status === 'completed') state = 'done'
    else if (currentTask.value?.status === 'failed' && i <= runningIdx) state = 'failed'
    return { label, state }
  })
})

const goToResultPage = () => {
  if (!currentTask.value?.id) return
  panelMode.value = 'result'
}

const goToTermLibrary = () => {
  panelMode.value = 'terms'
}

const goToStoryPage = () => {
  if (!currentTask.value?.id) return
  panelMode.value = 'story'
}

const goToStylePage = () => {
  panelMode.value = 'style'
}

const goToAIConfigPage = () => {
  panelMode.value = 'ai-config'
}

const openStyleFromCreate = () => {
  showCreateDialog.value = false
  panelMode.value = 'style'
}

const closePanel = () => {
  if (panelMode.value === 'style') {
    stylePickerReloadToken.value += 1
  }
  panelMode.value = 'workspace'
}

const hasBeautyScores = computed(() => currentTask.value?.beauty_sound_score != null)
const beautyScores = computed(() => ({
  sound: (currentTask.value?.beauty_sound_score || 0) * 10,
  word: (currentTask.value?.beauty_word_score || 0) * 10,
  meaning: (currentTask.value?.beauty_meaning_score || 0) * 10
}))

const pageCount = computed(() => Math.ceil(paragraphTotal.value / PAGE_SIZE) || 0)

const pageTabLabel = (page: number) => {
  const start = (page - 1) * PAGE_SIZE + 1
  const end = Math.min(page * PAGE_SIZE, paragraphTotal.value)
  return `${start}–${end}`
}

const activePageTab = computed({
  get: () => String(paragraphPage.value),
  set: (name: string) => {
    const page = Number(name)
    if (page && page !== paragraphPage.value) onParagraphPageChange(page)
  },
})

const selectedParagraph = computed(() =>
  paragraphs.value.find((item: any) => item.id === selectedParagraphId.value) || null
)

const selectParagraph = (para: any) => {
  selectedParagraphId.value = para.id
  nextTick(() => {
    document.getElementById(`trans-para-${para.id}`)?.scrollIntoView({ block: 'nearest' })
  })
}

const onRightModeChange = async (mode: string) => {
  if (mode === 'bulk') {
    miniEditId.value = null
    return
  }
  const dirty = paragraphs.value.filter((item: any) => item.dirty)
  await Promise.all(dirty.map((item: any) => saveParagraph(item)))
}

const setRightMode = async (mode: 'read' | 'bulk') => {
  if (rightMode.value === mode) return
  rightMode.value = mode
  await onRightModeChange(mode)
}

const toggleMiniEdit = async (para: any) => {
  if (miniEditId.value === para.id) {
    await saveParagraph(para)
    miniEditId.value = null
    return
  }
  if (miniEditId.value) {
    const prev = paragraphs.value.find((item: any) => item.id === miniEditId.value)
    if (prev) await saveParagraph(prev)
  }
  miniEditId.value = para.id
  selectedParagraphId.value = para.id
}

onMounted(async () => {
  loadLanguages()
  loadAIConfig()
  await loadTasks()
  // 仅当仍有进行中的任务时恢复轮询，避免空闲进页误报「全部完成」
  if (taskList.value.some((t: any) => isTaskRunning(t.status))) {
    startBatchPolling()
  }
})

const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const loadTasks = async (autoSelect = false) => {
  loadingTasks.value = true
  try {
    const response = await literaryApi.listTranslations({ limit: 50 })
    taskList.value = response.data
    if (autoSelect && taskList.value.length > 0 && !currentTask.value) {
      await selectTask(taskList.value[0])
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loadingTasks.value = false
  }
}

const mapParagraph = (p: any, previous?: any) => ({
  ...p,
  editedText: previous?.dirty ? previous.editedText : (p.user_edited_text || p.translated_text || ''),
  dirty: previous?.dirty || false,
})

const loadParagraphPage = async (page = paragraphPage.value, silent = false) => {
  if (!currentTask.value) return
  if (!silent) loadingParagraphs.value = true
  try {
    const skip = (page - 1) * PAGE_SIZE
    const response = await literaryApi.getParagraphs(currentTask.value.id, { skip, limit: PAGE_SIZE })
    const previous = new Map(paragraphs.value.map((item: any) => [item.id, item]))
    paragraphPage.value = page
    paragraphTotal.value = response.data.total
    paragraphs.value = (response.data.items || []).map((item: any) => mapParagraph(item, previous.get(item.id)))
    if (!paragraphs.value.some((item: any) => item.id === selectedParagraphId.value)) {
      selectedParagraphId.value = paragraphs.value[0]?.id ?? null
    }
  } catch (error) {
    if (!silent) ElMessage.error('加载段落失败')
  } finally {
    if (!silent) loadingParagraphs.value = false
  }
}

const onParagraphPageChange = async (page: number) => {
  if (miniEditId.value) {
    const prev = paragraphs.value.find((item: any) => item.id === miniEditId.value)
    if (prev) await saveParagraph(prev)
    miniEditId.value = null
  }
  await loadParagraphPage(page)
  sourceBodyRef.value?.scrollTo({ top: 0 })
  transBodyRef.value?.scrollTo({ top: 0 })
}

const loadFullText = async () => {
  if (!currentTask.value) return
  loadingFull.value = true
  try {
    const items: any[] = []
    const chunk = 200
    let skip = 0
    let total = Infinity
    while (skip < total) {
      const response = await literaryApi.getParagraphs(currentTask.value.id, { skip, limit: chunk })
      const batch = response.data.items || []
      total = response.data.total
      items.push(...batch)
      if (!batch.length) break
      skip += batch.length
    }
    fullSource.value = items.map((item) => item.source_text || '').join('\n\n')
    fullTranslation.value = items.map((item) => item.user_edited_text || item.translated_text || '').join('\n\n')
  } catch (error) {
    ElMessage.error('加载全文失败')
  } finally {
    loadingFull.value = false
  }
}

const onCompareModeChange = async (mode: string) => {
  if (mode !== 'full') return
  const dirty = paragraphs.value.filter((item: any) => item.dirty)
  await Promise.all(dirty.map((item: any) => saveParagraph(item)))
  await loadFullText()
}

const setCompareMode = async (mode: 'segment' | 'full') => {
  if (compareMode.value === mode) return
  compareMode.value = mode
  await onCompareModeChange(mode)
}

const selectTask = async (task: any, options?: { keepPage?: boolean; silent?: boolean }) => {
  const silent = options?.silent
  // 从词库 / 文风 / 大模型等子页点选任务时，关闭子页并回到该任务的翻译工作区
  if (!silent && panelMode.value !== 'workspace') closePanel()
  if (!silent) stopPolling()
  if (!silent) workflowLoading.value = true
  try {
    const response = await literaryApi.getTranslation(task.id, false, false)
    currentTask.value = response.data
    if (!options?.keepPage) {
      compareMode.value = 'segment'
      fullSource.value = ''
      fullTranslation.value = ''
      selectedParagraphId.value = null
      rightMode.value = 'read'
      miniEditId.value = null
      paragraphPage.value = 1
    }
    await loadParagraphPage(paragraphPage.value, !!silent)
    if (compareMode.value === 'full') await loadFullText()
    if (!silent && isWorkflowRunning.value) startPolling()
  } catch (error) {
    ElMessage.error('加载任务失败')
  } finally {
    if (!silent) workflowLoading.value = false
  }
}

const createNewTask = () => {
  const defaultType = categoryGroup.value === 'professional' ? 'tech' : 'general'
  newTaskForm.value = {
    title: '',
    source_text: '',
    source_lang: 'en',
    target_lang: 'zh',
    literary_type: defaultType,
    user_requirements: '',
    style_agent_id: undefined,
  }
  showCreateDialog.value = true
}

const allowedUploadExtensions = new Set(['txt', 'md', 'markdown', 'text', 'doc', 'docx', 'pdf', 'mobi', 'azw', 'html', 'htm', 'xml', 'json', 'csv', 'log', 'rst', 'tex', 'srt', 'sub', 'vtt', 'yaml', 'yml', 'ini', 'cfg', 'properties'])
const binaryUploadExtensions = new Set(['doc', 'docx', 'pdf', 'mobi', 'azw'])
const onCreateFileSelect = async (opts: { raw: File }) => {
  const file = opts?.raw
  if (!file) return
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.warning(`文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB），最大支持 ${MAX_FILE_SIZE / 1024 / 1024}MB`)
    return
  }
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !allowedUploadExtensions.has(ext)) {
    ElMessage.warning('请选择支持的文件格式')
    return
  }
  if (binaryUploadExtensions.has(ext)) {
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await literaryApi.parseFile(form)
      const text = res.data?.text ?? ''
      if (text.length > MAX_TEXT_CHARS) {
        ElMessage.warning(`文件内容过长（${(text.length / 10000).toFixed(1)}万字），已截取前 ${MAX_TEXT_CHARS / 10000} 万字符`)
        newTaskForm.value.source_text = text.slice(0, MAX_TEXT_CHARS)
      } else {
        newTaskForm.value.source_text = text
      }
      if (!newTaskForm.value.title) newTaskForm.value.title = (file.name || '').replace(/\.[^.]+$/, '')
      if (newTaskForm.value.source_text) ElMessage.success('文件已解析')
    } catch (e) {
      ElMessage.error('文件解析失败')
    }
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    let text = (reader.result as string) || ''
    if (text.length > MAX_TEXT_CHARS) {
      ElMessage.warning(`文件内容过长（${(text.length / 10000).toFixed(1)}万字），已截取前 ${MAX_TEXT_CHARS / 10000} 万字符`)
      text = text.slice(0, MAX_TEXT_CHARS)
    }
    newTaskForm.value.source_text = text
    if (!newTaskForm.value.title) newTaskForm.value.title = file.name.replace(/\.[^.]+$/, '')
  }
  reader.readAsText(file, 'UTF-8')
}

const submitNewTask = async () => {
  if (!newTaskForm.value.source_text.trim()) {
    ElMessage.warning('请粘贴原文或上传文件')
    return
  }
  creating.value = true
  try {
    const payload = {
      title: newTaskForm.value.title || undefined,
      source_text: newTaskForm.value.source_text,
      source_lang: newTaskForm.value.source_lang,
      target_lang: newTaskForm.value.target_lang,
      literary_type: newTaskForm.value.literary_type,
      user_requirements: newTaskForm.value.user_requirements?.trim() || undefined,
      style_agent_id: newTaskForm.value.style_agent_id,
    }
    const response = await literaryApi.createTranslation(payload)
    ElMessage.success('任务创建成功')
    showCreateDialog.value = false
    await loadTasks()
    await selectTask(response.data)
  } catch (error) {
    ElMessage.error('创建任务失败')
  } finally {
    creating.value = false
  }
}

const openEditTaskDialog = (task: any) => {
  editingTask.value = task
  editForm.value = { title: task.title || '', status: task.status || 'pending' }
  showEditTask.value = true
}

const submitEditTask = async () => {
  if (!editingTask.value) return
  const id = editingTask.value.id
  try {
    await literaryApi.updateTranslation(id, { title: editForm.value.title || undefined, status: editForm.value.status || undefined })
    ElMessage.success('已保存')
    showEditTask.value = false
    editingTask.value = null
    await loadTasks()
    if (currentTask.value?.id === id) {
      const t = taskList.value.find((x: any) => x.id === id)
      if (t) await selectTask(t)
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const confirmDeleteTask = async (task: any) => {
  try {
    await ElMessageBox.confirm('确定删除该翻译任务？', '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await literaryApi.deleteTranslation(task.id)
    ElMessage.success('已删除')
    taskList.value = taskList.value.filter((t: any) => t.id !== task.id)
    if (currentTask.value?.id === task.id) {
      currentTask.value = null
      paragraphs.value = []
      paragraphTotal.value = 0
      paragraphPage.value = 1
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const isTaskRunning = (status: string) => ['translating', 'verifying', 'revising', 'finalizing'].includes(status)

const enterBatchMode = () => {
  batchMode.value = true
  selectedTaskIds.value = filteredTaskList.value
    .filter((t: any) => !isTaskRunning(t.status))
    .filter((t: any) => t.status === 'pending' || t.status === 'failed')
    .map((t: any) => t.id)
}

const exitBatchMode = () => {
  batchMode.value = false
  selectedTaskIds.value = []
}

const toggleTaskSelection = (id: number) => {
  const task = taskList.value.find((t: any) => t.id === id)
  if (task && isTaskRunning(task.status)) return
  const idx = selectedTaskIds.value.indexOf(id)
  if (idx >= 0) selectedTaskIds.value.splice(idx, 1)
  else selectedTaskIds.value.push(id)
}

const startBatchWorkflow = async () => {
  if (selectedTaskIds.value.length === 0) return
  batchStarting.value = true
  try {
    await literaryApi.startBatchWorkflow(selectedTaskIds.value)
    ElMessage.success(`已启动 ${selectedTaskIds.value.length} 个任务的翻译队列`)
    exitBatchMode()
    await loadTasks()
    startBatchPolling(true)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '批量启动失败')
  } finally {
    batchStarting.value = false
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastPolledStep = 0

const startWorkflow = async () => {
  processing.value = true
  try {
    await literaryApi.startWorkflow(currentTask.value.id)
    currentTask.value.status = 'translating'
    currentTask.value.current_step = 1
    workflowLoading.value = true
    startPolling()
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '启动翻译失败'
    ElMessage.error(msg)
  } finally {
    processing.value = false
  }
}

const stopWorkflow = async () => {
  processing.value = true
  try {
    await literaryApi.stopWorkflow(currentTask.value.id)
    stopPolling()
    paraProgress.value = { total: 0, done: 0 }
    await refreshTask()
    await loadTasks()
    ElMessage.success('已终止')
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '中止失败'
    ElMessage.error(msg)
  } finally {
    processing.value = false
  }
}

const startPolling = () => {
  stopPolling()
  lastPolledStep = currentTask.value?.current_step || 0
  pollTimer = setInterval(async () => {
    if (!currentTask.value) return stopPolling()
    try {
      const res = await literaryApi.getWorkflowStatus(currentTask.value.id)
      const data = res.data
      workflowLoading.value = false
      const prevStep = lastPolledStep
      currentTask.value.status = data.overall_status
      currentTask.value.current_step = data.current_step
      lastPolledStep = data.current_step

      const taskInList = taskList.value.find((t: any) => t.id === currentTask.value.id)
      if (taskInList) { taskInList.status = data.overall_status; taskInList.current_step = data.current_step }

      paraProgress.value = { total: data.paragraph_total || 0, done: data.paragraph_done || 0 }

      const finished = data.overall_status === 'completed' || data.overall_status === 'failed'
      if (finished) {
        stopPolling()
        paraProgress.value = { total: 0, done: 0 }
        await refreshTask()
        await loadTasks()
        ElMessage[data.overall_status === 'completed' ? 'success' : 'error'](
          data.overall_status === 'completed' ? '翻译流程已完成' : '翻译流程失败'
        )
      } else if (data.current_step !== prevStep) {
        await refreshTask()
      } else {
        await loadParagraphPage(paragraphPage.value, true)
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 12000)
}

const stopPolling = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

let batchPollTimer: ReturnType<typeof setInterval> | null = null
/** 是否曾观察到进行中任务；只有从「有运行」变为「全停」才提示完成 */
let batchSawRunning = false

const startBatchPolling = (expectCompletion = false) => {
  stopBatchPolling()
  batchSawRunning = expectCompletion || taskList.value.some((t: any) => isTaskRunning(t.status))
  batchPollTimer = setInterval(async () => {
    try {
      await loadTasks()
      const hasRunning = taskList.value.some((t: any) => isTaskRunning(t.status))
      if (hasRunning) batchSawRunning = true
      if (!hasRunning) {
        stopBatchPolling()
        if (batchSawRunning) {
          batchSawRunning = false
          ElMessage.success('批量翻译全部完成')
        }
      }
      if (currentTask.value) {
        const updated = taskList.value.find((t: any) => t.id === currentTask.value.id)
        if (updated && updated.status !== currentTask.value.status) await refreshTask()
      }
    } catch { /* ignore */ }
  }, 20000)
}

const stopBatchPolling = () => { if (batchPollTimer) { clearInterval(batchPollTimer); batchPollTimer = null } }

onUnmounted(() => { stopPolling(); stopBatchPolling() })

const refreshTask = async () => {
  if (currentTask.value) await selectTask(currentTask.value, { keepPage: true, silent: true })
}

const saveParagraph = async (para: any) => {
  if (!para.dirty) return
  try {
    await literaryApi.updateParagraph(para.id, { user_edited_text: para.editedText })
    para.dirty = false
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const applyRetranslatedParagraph = (para: any, data: any) => {
  Object.assign(para, data)
  para.editedText = data.user_edited_text || data.step4_finalization || data.translated_text || data.step3_revision || data.step2_verification || data.step1_translation || ''
  para.dirty = false
}

const retranslateParagraph = async (para: any) => {
  if (!para?.id || retranslatingId.value) return
  try {
    await ElMessageBox.confirm(
      `将对第 ${para.paragraph_index + 1} 段重新执行 AI 四步翻译，并覆盖该段现有译文。是否继续？`,
      'AI 重译',
      { type: 'warning', confirmButtonText: '重译', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  retranslatingId.value = para.id
  try {
    const res = await literaryApi.retranslateParagraph(para.id)
    applyRetranslatedParagraph(para, res.data)
    if (compareMode.value === 'full') await loadFullText()
    ElMessage.success(`第 ${para.paragraph_index + 1} 段重译完成`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '重译失败')
  } finally {
    retranslatingId.value = null
  }
}

const exportTranslation = async () => {
  exporting.value = true
  try {
    const response = await literaryApi.exportTranslation(currentTask.value.id, { format: exportFormat.value as any, include_source: exportWithSource.value })
    const blob = new Blob([response.data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = response.data.filename || `${currentTask.value?.title || `translation_${currentTask.value.id}`}.${exportFormat.value}`
    link.click()
    URL.revokeObjectURL(url)
    showExport.value = false
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const getStatusType = (status: string) => ({ pending: 'info', translating: 'warning', verifying: 'warning', revising: 'warning', finalizing: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[status] || 'info'
const getStatusText = (status: string) => ({ pending: '待开始', translating: '翻译中', verifying: '校验中', revising: '润色中', finalizing: '定稿中', completed: '已完成', failed: '失败' } as Record<string, string>)[status] || status
</script>

<style scoped lang="scss">
.literary-view {
  display: flex;
  height: 100vh;
  background: var(--ins-bg);
}

.sidebar {
  width: 280px;
  background: linear-gradient(180deg, var(--ins-bg) 0%, var(--ins-bg-deep) 100%);
  border-right: 1px solid var(--ins-line);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px 14px 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--ins-line);

  .brand-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  .logo-mark {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: var(--ins-grad);
    flex-shrink: 0;
    display: grid;
    place-items: center;
    color: #fff;
    font-size: 15px;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(var(--ins-primary-rgb), 0.28);
  }

  .brand-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .brand {
    font-size: 16px;
    font-weight: 700;
    color: var(--ins-ink);
    line-height: 1.2;
    letter-spacing: 0.04em;
  }

  .brand-sub {
    font-size: 11px;
    color: var(--ins-muted);
    font-weight: 500;
  }

  .header-btns {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.category-filter {
  padding: 12px 12px 8px;
  flex-shrink: 0;

  .category-group {
    width: 100%;
    display: flex;

    :deep(.el-radio-button) {
      flex: 1;
    }

    :deep(.el-radio-button__inner) {
      width: 100%;
      padding: 8px 0;
      background: var(--ins-surface);
      border-color: var(--ins-line-strong);
      color: var(--ins-muted);
      font-size: 13px;
    }

    :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
      background: var(--el-color-primary);
      border-color: var(--el-color-primary);
      color: #fff;
    }
  }
}

.sidebar-footer-row {
  flex-shrink: 0;
  border-top: 1px solid var(--ins-line);
  background: transparent;
}

.sidebar-footer {
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--ins-muted);
  transition: background 0.15s, color 0.15s;
  &:hover {
    background: rgba(var(--ins-primary-rgb), 0.06);
    color: var(--ins-ink);
  }
  .el-icon { font-size: 16px; }
  .el-tag { margin-left: auto; }
  & + .sidebar-footer {
    border-top: 1px solid var(--ins-line);
  }
}

.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 10px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;
  border: 1px solid transparent;

  &:hover { background: rgba(16, 18, 24, 0.04); }
  &.active {
    background: var(--ins-grad-soft);
    border-color: rgba(var(--ins-primary-rgb), 0.18);
  }
  &.selected { background: rgba(var(--ins-primary-rgb), 0.1); }

  .task-checkbox { margin-right: 4px; flex-shrink: 0; }
  .task-info { flex: 1; min-width: 0; }
  .task-title {
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .task-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 5px;
    font-size: 12px;
    color: var(--ins-muted);
  }
  .task-actions {
    opacity: 0;
    transition: opacity 0.15s;
    flex-shrink: 0;
    display: flex;
    gap: 2px;
  }
  &:hover .task-actions { opacity: 1; }
}

.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--ins-surface);
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--ins-bg);

  .empty-card {
    text-align: center;
    padding: 40px 48px;
    border-radius: 14px;
    border: 1px solid var(--ins-line);
    background: var(--ins-surface);
    box-shadow: var(--ins-shadow);
    transition: transform 0.15s, box-shadow 0.15s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 28px rgba(16, 18, 24, 0.08);
      .empty-cta { opacity: 1; }
    }

    .empty-orb {
      width: 48px;
      height: 48px;
      margin: 0 auto;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: var(--ins-grad);
      color: #fff;
      font-size: 20px;
      font-weight: 700;
      box-shadow: 0 4px 12px rgba(var(--ins-primary-rgb), 0.28);
    }

    h2 {
      margin: 16px 0 8px;
      font-size: 18px;
      font-weight: 700;
      color: var(--ins-ink);
    }
    p { margin: 0; font-size: 13px; color: var(--ins-muted); max-width: 300px; }
    .empty-cta {
      display: inline-block;
      margin-top: 14px;
      font-size: 13px;
      font-weight: 600;
      color: var(--el-color-primary);
    }
  }
}

.workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.top-bar {
  padding: 10px 16px;
  background: var(--ins-surface);
  border-bottom: 1px solid var(--ins-line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;

  .bar-left, .bar-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .lang-sel { width: 124px; }
  .arrow { color: var(--ins-muted); font-size: 16px; }
}

.icon-switch {
  display: flex;
  align-items: center;
  gap: 6px;
}

.step-dots {
  display: flex;
  align-items: center;
  gap: 2px;

  .dot-item {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s;

    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    &.pending {
      color: var(--ins-muted);
      .dot { background: #c8cad1; }
    }

    &.running {
      color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
      .dot {
        background: var(--el-color-primary);
        box-shadow: 0 0 0 3px rgba(var(--ins-primary-rgb), 0.18);
        animation: pulse 1.5s infinite;
      }
    }

    &.done {
      color: #2d7a58;
      .dot { background: #3d9a78; }
    }

    &.failed {
      color: #a34444;
      .dot { background: #c45c5c; }
    }
  }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(var(--ins-primary-rgb), 0.18); }
  50% { box-shadow: 0 0 0 6px rgba(var(--ins-primary-rgb), 0.06); }
}

.score-popover {
  .score-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    font-size: 13px;
    & + .score-row { border-top: 1px solid var(--ins-line); }
  }
}

.edit-area {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  padding: 10px 18px;
  border-bottom: 1px solid var(--ins-line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ins-muted);
  background: var(--ins-surface);
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px;

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.8;
    color: var(--ins-ink);
  }
}

.source-panel {
  background: var(--ins-bg);
  border-right: 1px solid var(--ins-line);
}

.trans-panel {
  background: var(--ins-surface);
}

.para-item {
  cursor: pointer;
  border-radius: 10px;
  padding: 10px 12px;
  margin: 0 -8px;
  border: 1px solid transparent;

  & + .para-item { margin-top: 4px; }
  &:hover { background: rgba(16, 18, 24, 0.03); }
  &.active {
    background: var(--ins-grad-soft);
    border-color: rgba(var(--ins-primary-rgb), 0.18);
  }

  .para-index {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ins-muted);
    margin-bottom: 6px;
  }

  .para-source {
    font-size: 15px;
    color: var(--ins-ink);
    line-height: 1.8;
    white-space: pre-wrap;
  }
}

.version-block {
  & + .version-block {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px dashed var(--ins-line-strong);
  }

  .version-label {
    font-size: 11px;
    font-weight: 700;
    color: var(--ins-muted);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .version-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.8;
    color: var(--ins-ink);
  }

  &.active {
    background: var(--ins-grad-soft);
    border-radius: 10px;
    padding: 10px 12px;
    margin: 0 -8px;
  }

  .version-empty {
    color: var(--ins-muted);
    font-size: 13px;
  }
}

.compare-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px 0;
  background: var(--ins-surface);
  border-bottom: 1px solid var(--ins-line);

  .segment-tabs {
    flex: 1;
    min-width: 0;

    :deep(.el-tabs__header) { margin: 0; }
    :deep(.el-tabs__content) { display: none; }
    :deep(.el-tabs__nav-wrap::after) { display: none; }
  }
}

.no-content {
  color: var(--ins-muted);
  text-align: center;
  padding: 48px 0;
  font-size: 14px;
}

.inline-upload { margin-bottom: 8px; }

.text-stats {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--ins-muted);
}

.form-hint {
  font-size: 12px;
  color: var(--ins-muted);
  margin-top: 2px;
  line-height: 1.4;
}

.config-source {
  margin-top: 8px;
  text-align: right;
}
</style>
