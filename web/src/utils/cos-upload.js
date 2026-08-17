import cloudBase from '@/cloud'

export async function uploadImageToCos(file, prefix = 'activities/images') {
  const timestamp = Date.now()
  const randomStr = Math.random().toString(36).substr(2, 9)
  const ext = file.name.split('.').pop()
  const cloudPath = `${prefix}/${timestamp}-${randomStr}.${ext}`

  try {
    await cloudBase.init()

    const res = await cloudBase.getApp().callFunction({
      name: 'getPresignedUrl',
      data: { key: cloudPath }
    })

    if (res.result.errCode !== 0) {
      throw new Error(res.result.errMsg || '获取上传URL失败')
    }

    const { uploadUrl, fileUrl } = res.result

    const uploadRes = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type
      }
    })

    if (!uploadRes.ok) {
      throw new Error(`上传失败: ${uploadRes.status}`)
    }

    // 确保fileUrl包含协议头
    let processedFileUrl = fileUrl
    if (processedFileUrl && !processedFileUrl.startsWith('http://') && !processedFileUrl.startsWith('https://')) {
      processedFileUrl = `https://${processedFileUrl}`
    }

    return processedFileUrl
  } catch (error) {
    console.error('图片上传失败:', error)
    throw error
  }
}

export async function uploadBase64Image(base64Data, prefix = 'activities/images') {
  const response = await fetch(base64Data)
  const blob = await response.blob()
  const timestamp = Date.now()
  const randomStr = Math.random().toString(36).substr(2, 9)
  const file = new File([blob], `image-${timestamp}-${randomStr}.jpg`, { type: 'image/jpeg' })
  return await uploadImageToCos(file, prefix)
}

export function generateCosKey(prefix = 'activities/images') {
  const timestamp = Date.now()
  const randomStr = Math.random().toString(36).substr(2, 9)
  return `${prefix}/${timestamp}-${randomStr}`
}