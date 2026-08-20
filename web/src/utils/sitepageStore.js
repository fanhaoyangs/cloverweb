/**
 * 静态页管理共享状态（CmsLayout 侧边栏选择器 ↔ SitePageEdit 编辑器 之间协调）
 * - pages: 页面列表（CmsLayout 拉取一次缓存，SitePageEdit 不再重复拉列表）
 * - dirty: 当前页面是否有未保存修改（SitePageEdit 计算后回写，CmsLayout 切换前确认）
 */
import { reactive } from 'vue'

export const sitepageStore = reactive({
  pages: [],
  dirty: false
})
