<template>
  <footer>
    <div class="footer-content">
      <div class="footer-logos">
        <img src="https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png" alt="四叶草堂">
        <img src="https://images.communitygarden.org.cn/communitygarden/同济实验室logo.png" alt="同济实验中心">
      </div>
      <div class="footer-info">
        <p>四叶草堂社区规划设计营造促进中心 | 同济大学社区花园与社区营造实验中心</p>
        <p>重塑家园 共生发展</p>
      </div>
      <div class="footer-contact">
        <p>联系邮箱：siyecaotang2014@163.com</p>
        <p>办公地址：上海市杨浦区大学路248号702室</p>
      </div>
      <div class="footer-social">
        <!-- 微信 -->
        <div class="social-group">
          <div class="social-toggle" data-target="wechat-qr" @click.stop="toggleQR('wechat')">
            <img src="https://images.communitygarden.org.cn/communitygarden/微信图标.png" alt="微信">
          </div>
          <div class="social-qr-container" id="wechat-qr" :class="{ active: activeQR === 'wechat' }">
            <div class="footer-qr-item">
              <img src="https://images.communitygarden.org.cn/communitygarden/四叶草堂联系人.png" alt="微信联系人">
              <p>微信联系人</p>
            </div>
            <div class="footer-qr-item">
              <img src="https://images.communitygarden.org.cn/communitygarden/四叶草堂公众号.png" alt="四叶草堂公众号">
              <p>微信公众号<br>（四叶草堂）</p>
            </div>
            <div class="footer-qr-item">
              <img src="https://images.communitygarden.org.cn/communitygarden/社区花园公众号.png" alt="社区花园公众号">
              <p>微信公众号<br>（社区花园）</p>
            </div>
          </div>
        </div>
        
        <!-- 小红书 -->
        <div class="social-group">
          <div class="social-toggle" data-target="xiaohongshu-qr" @click.stop="toggleQR('xiaohongshu')">
            <img src="https://images.communitygarden.org.cn/communitygarden/小红书图标.png" alt="小红书">
          </div>
          <div class="social-qr-container" id="xiaohongshu-qr" :class="{ active: activeQR === 'xiaohongshu' }">
            <div class="footer-qr-item">
              <a href="https://www.xiaohongshu.com/user/profile/6295bf6600000000210275df" target="_blank">
                <img src="https://images.communitygarden.org.cn/communitygarden/四叶草堂小红书.png" alt="四叶草堂小红书">
              </a>
              <p>小红书<br>（四叶草堂）</p>
            </div>
            <div class="footer-qr-item">
              <a href="https://xhslink.com/m/AlTqnYg854E" target="_blank">
                <img src="https://images.communitygarden.org.cn/communitygarden/社区花园小红书.png" alt="社区花园小红书">
              </a>
              <p>小红书<br>（社区花园与社区营造）</p>
            </div>
          </div>
        </div>
        
        <!-- 小程序 -->
        <div class="social-group">
          <div class="social-toggle" data-target="applet-qr" @click.stop="toggleQR('applet')">
            <img src="https://images.communitygarden.org.cn/communitygarden/小程序图标.png" alt="小程序">
          </div>
          <div class="social-qr-container" id="applet-qr" :class="{ active: activeQR === 'applet' }">
            <div class="footer-qr-item">
              <img src="https://images.communitygarden.org.cn/communitygarden/CloverHub.jpg" alt="CloverHub小程序">
              <p>CloverHub<br>活动报名小程序</p>
            </div>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>©2025 上海市杨浦四叶草堂社区规划设计营造促进中心 | <a href="https://beian.miit.gov.cn/" target="_blank">沪ICP备2023004347号-1</a></p>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const activeQR = ref(null)

const toggleQR = (type) => {
  if (activeQR.value === type) {
    activeQR.value = null
  } else {
    activeQR.value = type
  }
}

const closeAllQR = () => {
  activeQR.value = null
}

const handleClickOutside = (e) => {
  if (!e.target.closest('.social-group')) {
    closeAllQR()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
footer {
  background: var(--primary-green-dark);
  color: var(--white);
  padding: 60px 60px 30px;
}

.footer-content {
  max-width: 1100px;
  margin: 0 auto;
  text-align: center;
}

.footer-logos {
  display: flex;
  justify-content: center;
  gap: 35px;
  margin-bottom: 35px;
}

.footer-logos img {
  height: 68px;
  object-fit: contain;
  filter: brightness(0) invert(1);
  opacity: 0.9;
}

.footer-info {
  margin-bottom: 35px;
}

.footer-info p {
  font-size: 13px;
  line-height: 2;
  opacity: 0.9;
}

.footer-contact {
  margin-bottom: 35px;
  font-size: 13px;
  line-height: 2;
  color: rgba(255,255,255,0.8);
}

.footer-social {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
  margin-bottom: 35px;
}

.social-group {
  position: relative;
  text-align: center;
}

.social-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-width: 60px;
}

.social-toggle img {
  width: auto;
  height: 25px;
  object-fit: contain;
}

.social-qr-container {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: var(--white);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 15px;
  display: flex;
  gap: 20px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
  z-index: 100;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  max-width: 90vw;
  white-space: nowrap;
}

/* 调整二维码容器位置 */
.social-group:first-child .social-qr-container {
  left: 50%;
  transform: translateX(-50%);
}

.social-group:last-child .social-qr-container {
  left: 50%;
  transform: translateX(-50%);
}

.social-qr-container::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border-width: 8px;
  border-style: solid;
  border-color: var(--white) transparent transparent transparent;
}

.social-qr-container.active {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) translateY(-10px);
}

.footer-qr-item {
  text-align: center;
  min-width: 100px;
}

.footer-qr-item img {
  width: 90px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.footer-qr-item p {
  font-size: 12px;
  color: var(--text-dark);
  opacity: 0.8;
  line-height: 1.5;
}

.footer-bottom {
  padding-top: 30px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 11px;
  opacity: 0.7;
}

.footer-bottom a {
  color: var(--white);
  text-decoration: none;
}

/* 响应式 */
@media (max-width: 1100px) {
  footer {
    padding: 60px 40px 30px;
  }
}

@media (max-width: 768px) {
  footer {
    padding: 60px 20px 30px;
  }

  .footer-social {
    gap: 5px;
  }

  .social-qr-container {
    left: 50% !important;
    transform: translateX(-50%) !important;
    padding: 15px;
    gap: 15px;
    max-width: 90vw;
  }

  .footer-qr-item {
    min-width: 70px;
  }

  .footer-qr-item img {
    width: 70px;
    border-radius: 6px;
    margin-bottom: 6px;
  }

  .footer-qr-item p {
    font-size: 11px;
    line-height: 1.3;
  }
}
</style>
