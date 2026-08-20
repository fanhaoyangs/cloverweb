/**
 * 飞书文档导入按钮（UEditorPlus 工具栏，位于秀米按钮旁）
 *
 * 按钮仅作触发器：点击后调用 window.__UE_FEISHU_IMPORT__(editor)，
 * 由 Vue 层（UEditor.vue 注入）打开 Element Plus 导入对话框，
 * 导入完成后通过 editor.execCommand('insertHtml', html) 注入内容。
 *
 * 文案与样式对齐秀米按钮：工具栏直接显示「飞书」文字（12px，飞书蓝）。
 */
(function () {
  // 注入按钮文字样式（与 xiumi-ue-v5.css 的「秀米」同规格）
  if (!document.getElementById('feishu-import-btn-style')) {
    var style = document.createElement('style')
    style.id = 'feishu-import-btn-style'
    style.textContent = [
      '.edui-button.edui-for-feishu-import .edui-button-wrap .edui-button-body {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: center;',
      '}',
      '.edui-button.edui-for-feishu-import .edui-button-wrap .edui-button-body .edui-icon {',
      '  background-image: none !important;',
      '  width: auto !important;',
      '  height: auto !important;',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: center;',
      '  padding: 0 4px;',
      '}',
      '.edui-button.edui-for-feishu-import .edui-button-wrap .edui-button-body .edui-icon::before {',
      '  content: "飞书";',
      '  font-size: 12px;',
      '  color: #3370ff;',
      '  white-space: nowrap;',
      '}'
    ].join('\n')
    document.head.appendChild(style)
  }

  UE.registerUI('feishuimport', function (editor) {
    var btn = new UE.ui.Button({
      name: 'feishu-import',
      title: '飞书文档导入',
      onclick: function () {
        if (typeof window.__UE_FEISHU_IMPORT__ === 'function') {
          window.__UE_FEISHU_IMPORT__(editor)
        } else {
          console.warn('[UEditor] 飞书导入回调未注册（window.__UE_FEISHU_IMPORT__）')
        }
      }
    })
    return btn
  })
})()
