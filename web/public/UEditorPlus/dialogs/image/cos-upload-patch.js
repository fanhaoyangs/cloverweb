(function() {
  'use strict';

  console.log('[UEditor COS Patch] XHR拦截脚本加载');

  function getCloudBase() {
    var w = window;
    while (w) {
      if (w.cloudBase) return w.cloudBase;
      try {
        if (w.parent && w.parent !== w) {
          w = w.parent;
        } else {
          break;
        }
      } catch (e) {
        break;
      }
    }
    return null;
  }

  function arrayBufferToBase64(buffer) {
    var bytes = new Uint8Array(buffer);
    var binary = '';
    var chunkSize = 0x8000;
    for (var i = 0; i < bytes.length; i += chunkSize) {
      var chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length));
      binary += String.fromCharCode.apply(null, chunk);
    }
    return btoa(binary);
  }

  function generateKey(ext) {
    var now = new Date();
    var dateStr = '' + now.getFullYear() +
      ('0' + (now.getMonth() + 1)).slice(-2) +
      ('0' + now.getDate()).slice(-2);
    return 'ueditor/images/' + dateStr + '/' + Date.now() + '-' + Math.floor(Math.random() * 1000000) + '.' + ext;
  }

  function extractFileFromFormData(formData) {
    if (!(formData instanceof FormData)) return null;
    var file = null;
    try {
      var entries = formData.entries();
      var entry;
      while (!(entry = entries.next()).done) {
        var val = entry.value[1];
        if (val instanceof File || val instanceof Blob) {
          file = val;
          break;
        }
      }
    } catch (e) {}
    return file;
  }

  function isUploadUrl(url) {
    if (!url) return false;
    var lower = url.toLowerCase();
    return lower.indexOf('uploadimage') !== -1 ||
           lower.indexOf('ueditor/upload') !== -1 ||
           (lower.indexOf('upload') !== -1 && lower.indexOf('ueditor') !== -1);
  }

  function isListImageUrl(url) {
    if (!url) return false;
    var lower = url.toLowerCase();
    return lower.indexOf('listimage') !== -1 ||
           lower.indexOf('ueditor/listimage') !== -1;
  }

  function patchXHR(xhrProto, win) {
    if (xhrProto.__cosPatched) return;
    xhrProto.__cosPatched = true;

    var origOpen = xhrProto.open;
    var origSend = xhrProto.send;

    xhrProto.open = function(method, url) {
      this.__cosUrl = url;
      this.__cosMethod = method;
      return origOpen.apply(this, arguments);
    };

    xhrProto.send = function(data) {
      var url = this.__cosUrl || '';
      var self = this;

      if (isUploadUrl(url)) {
        console.log('[UEditor COS Patch] 拦截上传请求:', url);
        handleUpload(self, data, win);
        return;
      }

      return origSend.apply(this, arguments);
    };
  }

  patchXHR(XMLHttpRequest.prototype, window);

  function completeXHR(xhr, status, responseText) {
    try {
      Object.defineProperty(xhr, 'readyState', { writable: true, configurable: true, value: 4 });
    } catch (e) {}
    try {
      Object.defineProperty(xhr, 'status', { writable: true, configurable: true, value: status });
    } catch (e) {}
    try {
      Object.defineProperty(xhr, 'statusText', { writable: true, configurable: true, value: status === 200 ? 'OK' : 'Error' });
    } catch (e) {}
    try {
      Object.defineProperty(xhr, 'responseText', { writable: true, configurable: true, value: responseText });
    } catch (e) {}
    try {
      Object.defineProperty(xhr, 'response', { writable: true, configurable: true, value: responseText });
    } catch (e) {}
    try {
      Object.defineProperty(xhr, 'responseURL', { writable: true, configurable: true, value: xhr.__cosUrl || '' });
    } catch (e) {}

    var readystatechangeEvent;
    try {
      readystatechangeEvent = new Event('readystatechange');
    } catch (e) {
      readystatechangeEvent = document.createEvent('Event');
      readystatechangeEvent.initEvent('readystatechange', false, false);
    }

    var loadEvent;
    try {
      loadEvent = new ProgressEvent('load', { lengthComputable: false });
    } catch (e) {
      loadEvent = document.createEvent('Event');
      loadEvent.initEvent('load', false, false);
    }

    try {
      if (typeof xhr.onreadystatechange === 'function') {
        xhr.onreadystatechange(readystatechangeEvent);
      }
    } catch (e) {
      console.warn('[UEditor COS Patch] onreadystatechange回调异常:', e);
    }

    try {
      xhr.dispatchEvent(readystatechangeEvent);
    } catch (e) {}

    try {
      if (typeof xhr.onload === 'function') {
        xhr.onload(loadEvent);
      }
    } catch (e) {}

    try {
      xhr.dispatchEvent(loadEvent);
    } catch (e) {}
  }

  function errorXHR(xhr, message) {
    completeXHR(xhr, 200, JSON.stringify({
      state: message || '上传失败'
    }));
  }

  function handleUpload(xhr, formData, win) {
    var file = extractFileFromFormData(formData);
    var cloudBase = getCloudBase();

    if (!file) {
      console.warn('[UEditor COS Patch] 无法从FormData提取文件，回退原始请求');
      var origSend = XMLHttpRequest.prototype.send;
      return origSend.call(xhr, formData);
    }

    if (!cloudBase) {
      console.error('[UEditor COS Patch] CloudBase未找到');
      errorXHR(xhr, 'CloudBase未初始化');
      return;
    }

    var reader = new FileReader();
    reader.onload = function() {
      var base64 = arrayBufferToBase64(reader.result);
      var ext = (file.name || 'image.jpg').split('.').pop().toLowerCase();
      var mimeType = file.type || 'image/jpeg';
      var key = generateKey(ext);

      console.log('[UEditor COS Patch] 通过云函数上传:', key, '大小:', file.size);

      cloudBase.init().then(function() {
        return cloudBase.callFunction({
          name: 'getPresignedUrl',
          data: {
            action: 'directUpload',
            key: key,
            base64Data: base64,
            contentType: mimeType
          }
        });
      }).then(function(res) {
        var result = res.result;
        if (result && result.errCode === 0) {
          var fileUrl = result.fileUrl;
          if (fileUrl && !/^https?:\/\//.test(fileUrl)) {
            fileUrl = 'https://' + fileUrl;
          }
          console.log('[UEditor COS Patch] 上传成功:', fileUrl);
          completeXHR(xhr, 200, JSON.stringify({
            state: 'SUCCESS',
            url: fileUrl,
            title: file.name || key,
            original: file.name || key
          }));
        } else {
          var errMsg = (result && result.errMsg) || '上传失败';
          console.error('[UEditor COS Patch] 云函数返回错误:', errMsg);
          errorXHR(xhr, errMsg);
        }
      }).catch(function(err) {
        console.error('[UEditor COS Patch] 上传异常:', err);
        errorXHR(xhr, err.message || '上传异常');
      });
    };

    reader.onerror = function() {
      errorXHR(xhr, '读取文件失败');
    };

    reader.readAsArrayBuffer(file);
  }

  function handleListImageAjax(url, opts) {
    var cloudBase = getCloudBase();

    if (!cloudBase) {
      console.error('[UEditor COS Patch] CloudBase未找到');
      if (opts && opts.onerror) {
        opts.onerror({ responseText: JSON.stringify({ state: 'FAIL' }) });
      }
      return;
    }

    var size = 20;
    var start = 0;

    if (opts && opts.data) {
      if (opts.data.start !== undefined) start = parseInt(opts.data.start) || 0;
      if (opts.data.size !== undefined) size = parseInt(opts.data.size) || 20;
    }

    var sizeMatch = url.match(/[?&]size=(\d+)/);
    var startMatch = url.match(/[?&]start=(\d+)/);
    if (sizeMatch) size = parseInt(sizeMatch[1]);
    if (startMatch) start = parseInt(startMatch[1]);

    console.log('[UEditor COS Patch] 在线图片请求, start:', start, 'size:', size);

    cloudBase.init().then(function() {
      return cloudBase.callFunction({
        name: 'getPresignedUrl',
        data: {
          action: 'listImages',
          prefix: 'ueditor/images/',
          marker: '',
          limit: size
        }
      });
    }).then(function(res) {
      var result = res.result;
      if (result && result.errCode === 0) {
        var list = result.list || [];
        console.log('[UEditor COS Patch] 在线图片加载成功, 数量:', list.length);
        if (opts && opts.onsuccess) {
          opts.onsuccess({
            responseText: JSON.stringify({
              state: 'SUCCESS',
              list: list,
              start: start,
              total: list.length
            })
          });
        }
      } else {
        console.error('[UEditor COS Patch] 在线图片加载失败:', (result && result.errMsg) || '未知错误');
        if (opts && opts.onsuccess) {
          opts.onsuccess({
            responseText: JSON.stringify({
              state: 'SUCCESS',
              list: [],
              start: 0,
              total: 0
            })
          });
        }
      }
    }).catch(function(err) {
      console.error('[UEditor COS Patch] 在线图片加载异常:', err);
      if (opts && opts.onerror) {
        opts.onerror({ responseText: JSON.stringify({ state: 'FAIL' }) });
      }
    });
  }

  try {
    var UE = window.UE;
    if (UE && UE.ajax && UE.ajax.request) {
      var origAjaxRequest = UE.ajax.request;
      UE.ajax.request = function(url, opts) {
        var requestUrl = (typeof url === 'string') ? url : ((url && url.url) ? url.url : '');
        if (isListImageUrl(requestUrl)) {
          console.log('[UEditor COS Patch] 通过UE.ajax.request拦截在线图片请求:', requestUrl);
          handleListImageAjax(requestUrl, opts);
          return;
        }
        return origAjaxRequest.apply(this, arguments);
      };
      console.log('[UEditor COS Patch] 已覆盖UE.ajax.request');
    } else {
      console.warn('[UEditor COS Patch] UE.ajax.request未找到，尝试延迟覆盖');
      var tryCount = 0;
      var tryInterval = setInterval(function() {
        tryCount++;
        var UE = window.UE;
        if (UE && UE.ajax && UE.ajax.request) {
          clearInterval(tryInterval);
          var origAjaxRequest = UE.ajax.request;
          if (!origAjaxRequest.__cosPatched) {
            var wrappedRequest = function(url, opts) {
              var requestUrl = (typeof url === 'string') ? url : ((url && url.url) ? url.url : '');
              if (isListImageUrl(requestUrl)) {
                console.log('[UEditor COS Patch] 通过UE.ajax.request拦截在线图片请求(延迟):', requestUrl);
                handleListImageAjax(requestUrl, opts);
                return;
              }
              return origAjaxRequest.apply(this, arguments);
            };
            wrappedRequest.__cosPatched = true;
            UE.ajax.request = wrappedRequest;
            console.log('[UEditor COS Patch] 延迟覆盖UE.ajax.request成功');
          }
        } else if (tryCount >= 20) {
          clearInterval(tryInterval);
          console.warn('[UEditor COS Patch] 延迟覆盖UE.ajax.request超时');
        }
      }, 100);
    }
  } catch (e) {
    console.warn('[UEditor COS Patch] 覆盖UE.ajax.request失败:', e.message);
  }

  console.log('[UEditor COS Patch] XHR拦截已初始化');
})();
