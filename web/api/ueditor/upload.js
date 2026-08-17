// UEditor 后端接口 - 处理图片上传到 COS
// 接口路径: /api/ueditor/upload

const cloudBase = require('@cloudbase/node-sdk')

// 初始化 CloudBase
const app = cloudBase.init({
  env: process.env.CLOUDBASE_ENV_ID
})

// UEditor 配置
const UEDITOR_CONFIG = {
  imageActionName: 'uploadimage',
  imageFieldName: 'upfile',
  imageMaxSize: 20 * 1024 * 1024, // 20MB
  imageAllowFiles: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  imageCompressEnable: true,
  imageCompressBorder: 1600,
  imageInsertAlign: 'none',
  imageUrlPrefix: '',
  imagePathFormat: 'ueditor/images/{yyyy}{mm}{dd}/{time}{rand:6}'
}

// 生成文件路径
function generateFilePath(originalName) {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const time = date.getTime()
  const rand = Math.floor(Math.random() * 1000000)
  const ext = originalName.split('.').pop()
  return `ueditor/images/${year}${month}${day}/${time}${rand}.${ext}`
}

// 处理 UEditor 上传请求
async function handleUEditorUpload(req, res) {
  try {
    const action = req.query.action
    
    // 处理 config 请求
    if (action === 'config') {
      return res.json(UEDITOR_CONFIG)
    }
    
    // 处理图片上传
    if (action === UEDITOR_CONFIG.imageActionName) {
      const file = req.files[UEDITOR_CONFIG.imageFieldName]
      
      if (!file) {
        return res.json({
          state: 'FAIL',
          message: '没有上传文件'
        })
      }
      
      // 检查文件类型
      const ext = file.name.split('.').pop().toLowerCase()
      if (!UEDITOR_CONFIG.imageAllowFiles.includes(`.${ext}`)) {
        return res.json({
          state: 'FAIL',
          message: '不支持的文件类型'
        })
      }
      
      // 检查文件大小
      if (file.size > UEDITOR_CONFIG.imageMaxSize) {
        return res.json({
          state: 'FAIL',
          message: '文件大小超过限制'
        })
      }
      
      // 生成文件路径
      const cloudPath = generateFilePath(file.name)
      
      // 调用云函数获取预签名URL
      const { result } = await app.callFunction({
        name: 'getPresignedUrl',
        data: { key: cloudPath }
      })
      
      if (result.errCode !== 0) {
        return res.json({
          state: 'FAIL',
          message: result.errMsg || '获取上传URL失败'
        })
      }
      
      const { uploadUrl, fileUrl } = result
      
      // 上传文件到 COS
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        body: file.data,
        headers: {
          'Content-Type': file.mimetype
        }
      })
      
      if (!response.ok) {
        return res.json({
          state: 'FAIL',
          message: `上传失败: ${response.status}`
        })
      }
      
      // 返回 UEditor 格式的响应
      return res.json({
        state: 'SUCCESS',
        url: fileUrl,
        title: file.name,
        original: file.name
      })
    }
    
    return res.json({
      state: 'FAIL',
      message: '不支持的操作'
    })
  } catch (error) {
    console.error('UEditor上传错误:', error)
    return res.json({
      state: 'FAIL',
      message: error.message || '上传失败'
    })
  }
}

// 导出接口
module.exports = handleUEditorUpload