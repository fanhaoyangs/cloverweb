import cloudbase from '@cloudbase/js-sdk'
const CLOUDBASE_ENV_ID = import.meta.env.VITE_CLOUDBASE_ENV_ID || 'cloudbase-9ge74hyu7143b967'

let initPromise = null

class CloudBaseSDK {
  constructor() {
    this.db = null
    this.app = null
    this.initialized = false
  }

  async init() {
    if (this.initialized) return
    if (initPromise) return initPromise

    initPromise = this._doInit()
    return initPromise
  }

  async _doInit() {
    try {
      console.log('开始加载CloudBase SDK...')

      this.app = cloudbase.init({
        env: CLOUDBASE_ENV_ID
      })
      console.log('CloudBase App初始化成功')

      const auth = this.app.auth()
      console.log('开始匿名登录...')
      await auth.signInAnonymously()
      console.log('匿名登录成功')

      this.db = this.app.database()
      this.initialized = true

      console.log('CloudBase 初始化完成')
    } catch (error) {
      console.error('CloudBase 初始化失败:', error)
      initPromise = null
      throw error
    }
  }

  getDatabase() {
    if (!this.initialized) {
      throw new Error('CloudBase 未初始化，请先调用 init()')
    }
    return this.db
  }

  getApp() {
    return this.app
  }

  async callFunction(options) {
    if (!this.initialized) {
      await this.init()
    }
    const adminFunctions = [
      'updateActivity', 'backupDatabase', 'updateSessionStatus',
      'manageBuddyCode', 'manageForm', 'updateRegistration', 'manageArticle'
    ]
    if (adminFunctions.includes(options.name)) {
      const adminToken = localStorage.getItem('adminToken')
      if (adminToken) {
        options.data = { ...options.data, adminToken }
      }
    }
    return this.app.callFunction(options)
  }
}

const cloudBaseInstance = new CloudBaseSDK()
window.cloudBase = cloudBaseInstance
export default cloudBaseInstance