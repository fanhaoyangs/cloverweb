import fs from 'fs'
import path from 'path'

// CloudBase 配置 - 从环境变量读取
const CLOUDBASE_ENV_ID = process.env.VITE_CLOUDBASE_ENV_ID || 'cloudbase-9ge74hyu7143b967'

// 模拟文件解析
function parseMultipartFormData(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', chunk => {
      body += chunk.toString()
    })
    req.on('end', () => {
      const files = {}
      // 简化的文件解析
      files.upfile = {
        name: 'test.jpg',
        data: Buffer.from('mock image data'),
        mimetype: 'image/jpeg',
        size: 1024
      }
      resolve({ files })
    })
    req.on('error', reject)
  })
}

// 下载远程图片
async function downloadRemoteImage(url) {
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to download image: ${response.status}`)
    }
    const buffer = await response.arrayBuffer()
    return Buffer.from(buffer)
  } catch (error) {
    console.error('Download remote image error:', error)
    throw error
  }
}

// 上传到COS - 使用CloudBase HTTP API
async function uploadToCos(buffer, filename, ext) {
  try {
    // 生成文件路径
    const date = new Date()
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const time = date.getTime()
    const rand = Math.floor(Math.random() * 1000000)
    const cloudPath = `ueditor/images/${year}${month}${day}/${time}${rand}.${ext}`

    // 调用CloudBase云函数获取预签名URL
    const functionUrl = `https://${CLOUDBASE_ENV_ID}.service.tcloudbase.com/getPresignedUrl`
    
    const response = await fetch(functionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        key: cloudPath,
        contentType: `image/${ext === 'jpg' ? 'jpeg' : ext}`
      })
    })

    if (!response.ok) {
      throw new Error(`获取预签名URL失败: ${response.status}`)
    }

    const result = await response.json()
    
    if (result.errCode !== 0) {
      throw new Error(result.errMsg || '获取预签名URL失败')
    }

    const { uploadUrl, fileUrl } = result

    // 使用预签名URL上传文件到COS
    const uploadResponse = await fetch(uploadUrl, {
      method: 'PUT',
      body: buffer,
      headers: {
        'Content-Type': `image/${ext === 'jpg' ? 'jpeg' : ext}`
      }
    })

    if (!uploadResponse.ok) {
      throw new Error(`上传失败: ${uploadResponse.status}`)
    }

    return fileUrl
  } catch (error) {
    console.error('上传到COS失败:', error)
    throw error
  }
}

// UEditor 配置
const UEDITOR_CONFIG = {
  imageActionName: 'uploadimage',
  imageFieldName: 'upfile',
  imageMaxSize: 20 * 1024 * 1024,
  imageAllowFiles: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  imageCompressEnable: true,
  imageCompressBorder: 1600,
  imageInsertAlign: 'none',
  imageUrlPrefix: '',
  imagePathFormat: 'ueditor/images/{yyyy}{mm}{dd}/{time}{rand:6}',
  // 远程图片抓取配置
  catchRemoteImageEnable: true,
  catchRemoteImageFormat: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  catchRemoteImageTimeout: 30000
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

// UEditor 上传处理
async function handleUEditorUpload(req, res) {
  try {
    const url = new URL(req.url, 'http://localhost')
    const action = url.searchParams.get('action')
    
    // 处理 config 请求
    if (action === 'config') {
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify(UEDITOR_CONFIG))
      return
    }
    
    // 处理图片上传
    if (action === UEDITOR_CONFIG.imageActionName) {
      // 处理远程图片抓取（秀米图片）
      const source = url.searchParams.get('source')
      if (source === 'remote') {
        const remoteUrl = url.searchParams.get('url')
        if (!remoteUrl) {
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({
            state: 'FAIL',
            message: '没有提供远程图片URL'
          }))
          return
        }
        
        try {
          console.log('[UEditor Middleware] 开始下载远程图片:', remoteUrl)
          
          // 下载远程图片
          const imageBuffer = await downloadRemoteImage(remoteUrl)
          
          // 提取文件名和扩展名
          const filename = remoteUrl.split('/').pop().split('?')[0]
          const ext = filename.split('.').pop().toLowerCase()
          
          console.log('[UEditor Middleware] 开始上传到COS:', filename)
          
          // 实际上传到COS
          const fileUrl = await uploadToCos(imageBuffer, filename, ext)
          
          console.log('[UEditor Middleware] 上传成功:', fileUrl)
          
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({
            state: 'SUCCESS',
            url: fileUrl,
            title: filename,
            original: filename
          }))
          return
        } catch (error) {
          console.error('[UEditor Middleware] 远程图片处理失败:', error)
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({
            state: 'FAIL',
            message: `远程图片抓取失败: ${error.message}`
          }))
          return
        }
      }
      
      // 处理本地文件上传
      const { files } = await parseMultipartFormData(req)
      const file = files[UEDITOR_CONFIG.imageFieldName]
      
      if (!file) {
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({
          state: 'FAIL',
          message: '没有上传文件'
        }))
        return
      }
      
      try {
        console.log('[UEditor Middleware] 开始上传本地文件:', file.name)
        
        // 实际上传到COS
        const ext = file.name.split('.').pop().toLowerCase()
        const fileUrl = await uploadToCos(file.data, file.name, ext)
        
        console.log('[UEditor Middleware] 上传成功:', fileUrl)
        
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({
          state: 'SUCCESS',
          url: fileUrl,
          title: file.name,
          original: file.name
        }))
        return
      } catch (error) {
        console.error('[UEditor Middleware] 本地文件上传失败:', error)
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({
          state: 'FAIL',
          message: `上传失败: ${error.message}`
        }))
        return
      }
    }
    
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({
      state: 'FAIL',
      message: '不支持的操作'
    }))
  } catch (error) {
    console.error('[UEditor Middleware] 上传错误:', error)
    res.setHeader('Content-Type', 'application/json')
    res.end(JSON.stringify({
      state: 'FAIL',
      message: error.message || '上传失败'
    }))
  }
}

// Vite 中间件
function ueditorMiddleware() {
  return {
    name: 'ueditor-middleware',
    configureServer(server) {
      server.middlewares.use('/api/ueditor/upload', handleUEditorUpload)
    }
  }
}

export default ueditorMiddleware
