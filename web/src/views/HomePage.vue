<template>
  <div class="home-page">
    <!-- Hero Section -->
    <section class="hero" id="home">
      <div class="hero-bg"></div>
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <h1 class="hero-title">花开中国</h1>
        <p class="hero-subtitle">每个人都有改变社区的力量</p>
      </div>
    </section>

    <!-- 简洁介绍区块 -->
    <section class="intro-plain-section">
      <div class="intro-plain-container">
        <div class="special-message">
          <p>“花开中国”由四叶草堂团队发起，是聚焦社区花园行动的知识平台与实践支持网络。社区花园是民众共建共享的开放空间，从专业发起到居民主导，从单一花园走向街区共生，推动城市社区治理创新，社区花园的理念与实践价值日益受到社会关注，越来越多的行动伙伴参与其中。</p>
          <p>本网站致力于梳理与传播社区花园和社区营造相关的实践经验，为城市与社区提供可复制的路径与工具。</p>
        </div>
      </div>
      
      <div class="map-content">
        <div class="map-img" style="display: flex; justify-content: center; align-items: center;margin:60px auto; width: 100%;">
          <img src="https://images.communitygarden.org.cn/communitygarden/全国社区花园地图.jpg" alt="全国社区花园地图" style="display: block; width: 100%; max-width: 1200px; height: auto; border-radius: 12px;">
        </div>
        <div class="intro-buttons">
          <a href="https://y1f9d2c3dwo.feishu.cn/wiki/DfLfw0XHeifoHmkJQWUc00rAnzf" target="_blank" class="intro-button">我要提供社区花园信息</a>
        </div>
      </div>
    </section>

    <!-- 竞赛区块 -->
    <section class="competition-section" id="competition">
      <div class="section-header">
        <h2 class="section-title">全国社区花园设计营造竞赛与社区参与行动</h2>
      </div>

      <div class="competition-content">
        <div class="competition-intro">
          <p style="max-width:800px; margin: 0 auto;">
            全国社区花园竞赛行动始于2021年，至今已经举办5届。活动在中国风景园林学会、上海市风景园林学会的指导下，同济大学景观学系协同《中国园林》杂志社和全国风景园林院校联合举办，旨在响应国家“人民城市”“健康中国”战略与城市更新行动，推动公众参与城市公共性生产。
          </p>
          <br>
          <p style="max-width:800px; margin: 0 auto;">
            2021～2024年间，共有来自 177 所高校及中小学的上千名参赛学生（横跨 42 个学科）、上万名居民参与，在 67 座城市成功营造 280 余个落地花园，组织居民工作坊 1000 余场。
          </p>
        </div>

        <div class="edition-2026-card">
          <div class="edition-2026-badge">第六届 · 报名进行中</div>
          <h3 class="edition-2026-title">共同关切</h3>
          <p class="edition-2026-subtitle">2026年全国社区花园设计营造竞赛与社区参与行动</p>
          <p class="edition-2026-desc">以「共同关切」为主题，回应现代社会 "附近消失" 的困境，重建人与人、人与社区的真实联结。聚焦城乡各类开放公共空间中的小微绿地、闲置边角地等改造设计。</p>
          <div class="edition-2026-meta">
            <div class="edition-2026-meta-item">
              <span class="meta-icon">📅</span>
              <span>即日起 ~ 2026年10月28日</span>
            </div>
            <div class="edition-2026-meta-item">
              <span class="meta-icon">🏆</span>
              <span>一等奖1组 / 二等奖3组 / 三等奖5组 + 特别奖项</span>
            </div>
            <div class="edition-2026-meta-item">
              <span class="meta-icon">👥</span>
              <span>场地使用者≥1人 + 专业者0-7人 + 指导教师0-3人</span>
            </div>
            <div class="edition-2026-meta-item">
              <span class="meta-icon">📍</span>
              <span>面向全国城乡开放公共空间</span>
            </div>
          </div>
          <div class="edition-2026-actions">
            <button class="edition-2026-btn edition-2026-btn-primary" @click="showCompetitionModal = true">查看竞赛详情</button>
            <a href="https://landscape-caup.tongji.edu.cn/c3/7b/c10586a377723/page.htm" target="_blank" class="edition-2026-btn edition-2026-btn-outline">前往官方页面</a>
          </div>
        </div>

        <div class="data-visualization">
          <img src="https://images.communitygarden.org.cn/communitygarden/1至5海报数据.png" alt="历届数据对比">
        </div>

        <div class="winners-grid">
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2024-东风花园.jpg" alt="东风花园">
            </div>
            <div class="winner-content">
              <h4>东风花园</h4>
              <p>2024年第四届一等奖</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2023-疗愈花园.jpg" alt="徐虹北生活盒子疗愈花园">
            </div>
            <div class="winner-content">
              <h4>徐虹北生活盒子疗愈花园</h4>
              <p>2023年第三届一等奖</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2022-嗨老朋友.jpg" alt="嗨！老朋友">
            </div>
            <div class="winner-content">
              <h4>嗨！老朋友</h4>
              <p>2022年第二届一等奖</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2021-西西花园.jpg" alt="西西花园">
            </div>
            <div class="winner-content">
              <h4>西西花园</h4>
              <p>2021年首届一等奖</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 第五届区块 -->
    <section class="fifth-edition-section" id="fifth-edition">
      <div class="fifth-edition-flex" style="display: flex; align-items: center; justify-content: center; max-width:800px; margin: 40px auto;">
        <div style="flex:0 0 40%; text-align:center;">
          <div class="section-header" style="text-align:center; margin-bottom:0;">
            <h2 class="section-title" style="margin-bottom:0; line-height:1.3;">
              百姓园林<br>共生发展
            </h2>
          </div>
        </div>
        <div style="flex:0 0 60%; text-align:center;">
          <img src="https://images.communitygarden.org.cn/communitygarden/全国竞赛LOGO.png" alt="第五届全国社区花园设计营造竞赛" style="max-width:80%; height:auto; margin-bottom:10px; display:block;">
        </div>
      </div>
      
      <div class="fifth-edition-content">
        <div class="edition-theme" style="max-width:800px; margin:0 auto; text-align:left;">
          <p>2025年第5届竞赛以“百姓园林，共生发展”为主题，选取待改造的城乡绿地开展社区参与式花园设计。竞赛组织大学生与社区居民、商户结成共创团队，将“园林即生活”的愿景转化为具体行动。此举不仅在于优化空间环境，更在于通过发动基层力量参与，增强社区凝聚力，探索人与自然、社区与城市的和谐共生之道，将行业倡议切实落地为人才培养与社会参与的关键实践。</p>
        </div>
        <br>
        <div class="edition-theme" style="max-width:800px; margin:0 auto; text-align:left;">
          <p>本届行动覆盖全国36个城市，合计93所院校的115个小组参与落地了86个社区花园，总参与人数近千人，共累计开展上千场活动。其中以上海、北京、石河子、阿拉尔、南京等城市报名最多。花园主题多以共建共享、儿童友好、自然疗愈为主。</p>
        </div>

        <div class="data-visualization">
          <img src="https://images.communitygarden.org.cn/communitygarden/第5届海报.png" alt="第五届海报">
        </div>

        <div class="edition-philosophy" style="max-width:800px; margin: 0 auto;">
          <p>"百姓园林"理念强调园林建设应回归人民主体，让园林成为百姓可参与、可享受的日常生活空间。行动鼓励居民从设计、营造到运维全程参与，在协作中增进理解、凝聚共识，构建富有生命力的社区共同体。</p>
          <br>
          <p>对风景园林学科而言，这是实践路径的转型探索，也是对传统教育模式的一次革新。学生们在实践中学习、在合作中成长，为社区带来改变的同时，也为个人发展开拓了新路径。</p>
        </div>

        <div class="awards-table" style="margin-top: 40px; text-align: center;">
          <a href="https://mp.weixin.qq.com/s/x_PaFR9sVJmIOb7LsvJkPg" target="_blank">
            <img src="https://images.communitygarden.org.cn/communitygarden/第5届得奖名单一览表.png" alt="第5届得奖名单一览表" style="width: 100%; max-width: 100%; height: auto; border-radius: 12px;">
          </a>
        </div>
 
        
        <div class="winners-grid">
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2025-1-味来花园.webp" alt="南宁｜共生·味来花园">
            </div>
            <div class="winner-content">
              <h4>共生·"味"来花园</h4>
              <p>一等奖（华南-04组·南宁）</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2025-2-成长花园.webp" alt="北京｜成长花园">
            </div>
            <div class="winner-content">
              <h4>成长花园</h4>
              <p>二等奖（华北-03组·北京）</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2025-3-百味花园.webp" alt="南京｜百味花园">
            </div>
            <div class="winner-content">
              <h4>百味花园</h4>
              <p>二等奖（华东-28组·南京）</p>
            </div>
          </div>
          <div class="winner-card">
            <div class="winner-image">
              <img src="https://images.communitygarden.org.cn/communitygarden/2025-4-循环花园.webp" alt="台州｜循环花园">
            </div>
            <div class="winner-content">
              <h4>循环花园</h4>
              <p>二等奖（华东-23组·台州）</p>
            </div>
          </div>
        </div>
        <br>
        <div class="intro-buttons">
          <a href="https://mp.weixin.qq.com/s/x_PaFR9sVJmIOb7LsvJkPg" target="_blank" class="intro-button">查看获奖详情</a>
        </div>
      </div>
    </section>

    <!-- 参与方式区块 -->
    <section class="participation-section" id="participation">
      <div class="section-header">
        <h2 class="section-title">参与方式</h2>
      </div>
      <div class="participation-content">
        <div class="participation-grid">
          <div class="participation-card">
            <h4>成为志愿者</h4>
            <p>亲身参与各个社区花园项目的现场营造和活动组织，用双手创造美好。</p>
          </div>
          <div class="participation-card">
            <h4>参加培训与工作坊</h4>
            <p>加入我们的社区规划师培育计划，或参加各类主题工作坊，学习社区营造的知识与技能。</p>
          </div>
          <div class="participation-card">
            <h4>加入社区花园网络</h4>
            <p>参与一年一度的全国社区花园设计营建竞赛，与来自全国各地的行动者交流学习，分享经验。</p>
          </div>
          <div class="participation-card">
            <h4>发起在地行动</h4>
            <p>如果你有改变自己社区的想法，我们可以为你提供经验支持和资源链接，帮助你在自己的家园发起项目。</p>
          </div>
        </div>
      </div>
      <div class="special-message">
        <p>我们相信，每个人都有改变社区的力量。我们邀请每一位关心社区、热爱生活的市民加入我们的行列。</p>
      </div>
    </section>

    <!-- 往届回顾区块（硬编码） -->
    <section class="review-section" id="review">
      <div class="section-header">
        <h2 class="section-title">往届回顾</h2>
      </div>
      <div class="review-content">
        <div class="review-grid">
          <a href="https://mp.weixin.qq.com/s/x_PaFR9sVJmIOb7LsvJkPg" target="_blank" class="review-card-link">
            <div class="review-card">
              <div class="review-image">
                <img src="https://images.communitygarden.org.cn/communitygarden/第5届海报.png" alt="2025年竞赛">
              </div>
              <div class="review-content-area">
                <p>获奖名单|2025年第五届社区花园竞赛行动</p>
              </div>
            </div>
          </a>

          <a href="https://mp.weixin.qq.com/s?__biz=Mzg3ODYyMDE4MQ==&mid=2247494284&idx=1&sn=56a716dddcc781e0f34e6e1102627084&scene=21#wechat_redirect" target="_blank" class="review-card-link">
            <div class="review-card">
              <div class="review-image">
                <img src="https://images.communitygarden.org.cn/communitygarden/2024竞赛行动.jpg" alt="2024年竞赛">
              </div>
              <div class="review-content-area">
                <p>获奖名单|2024年第四届社区花园竞赛行动</p>
              </div>
            </div>
          </a>

          <a href="https://mp.weixin.qq.com/s?__biz=Mzg3ODYyMDE4MQ==&mid=2247491015&idx=1&sn=25c58cd053dba5dd1f3a45168c429d8&scene=21#wechat_redirect" target="_blank" class="review-card-link">
            <div class="review-card">
              <div class="review-image">
                <img src="https://images.communitygarden.org.cn/communitygarden/2023竞赛行动.jpg" alt="2023年竞赛">
              </div>
              <div class="review-content-area">
                <p>获奖名单|2023年第三届社区花园竞赛行动</p>
              </div>
            </div>
          </a>

          <a href="https://mp.weixin.qq.com/s?__biz=Mzg3ODYyMDE4MQ==&mid=2247489687&idx=1&sn=9cefe7151e09bff7cf2534d8b6595e61&scene=21#wechat_redirect" target="_blank" class="review-card-link">
            <div class="review-card">
              <div class="review-image">
                <img src="https://images.communitygarden.org.cn/communitygarden/2022竞赛行动.jpg" alt="2022年竞赛">
              </div>
              <div class="review-content-area">
                <p>获奖名单|2022年第二届社区花园竞赛行动</p>
              </div>
            </div>
          </a>

          <a href="https://mp.weixin.qq.com/s?__biz=Mzg3ODYyMDE4MQ==&mid=2247487472&idx=1&sn=03c885174c7ffd67a2156cc22351035b&scene=21#wechat_redirect" target="_blank" class="review-card-link">
            <div class="review-card">
              <div class="review-image">
                <img src="https://images.communitygarden.org.cn/communitygarden/2021竞赛行动.jpg" alt="2021年竞赛">
              </div>
              <div class="review-content-area">
                <p>获奖名单|2021年首届社区花园竞赛行动</p>
              </div>
            </div>
          </a>
        </div>
      </div>
    </section>

    <div class="modal-overlay" v-if="showCompetitionModal" @click.self="showCompetitionModal = false">
      <div class="modal-container">
        <button class="modal-close" @click="showCompetitionModal = false">&times;</button>
        <div class="modal-body">
          <h2 class="modal-title">第六届全国社区花园设计营造竞赛与社区参与行动</h2>
          <p class="modal-subtitle">主题：共同关切</p>
          <div class="modal-section">
            <h3>主题阐述</h3>
            <p>本届竞赛以「共同关切」为主题，取法人类学家项飙教授的最新表述，社区花园作为空间载体，回应现代社会 "附近消失" 的困境，重建人与人、人与社区的真实联结。</p>
            <p>“共同关切”，是对当下城市生活 "附近消解、邻里疏离" 的回应。落脚于社区花园营造：关切土地与自然、关切邻里与社群、关切公共与日常、关切共建与延续。</p>
          </div>
          <div class="modal-section">
            <h3>时间安排</h3>
            <table class="modal-table">
              <tbody>
              <tr><td>活动报名</td><td>即日起 ~ 10月28日（报名最终截止，期间可持续报名）</td></tr>
              <tr><td>确定选点地址</td><td></td></tr>
              <tr><td>设计/营建阶段</td><td></td></tr>
              <tr><td>可持续运维阶段</td><td>运维不少于7天</td></tr>
              <tr><td>成果提交</td><td>10月28日</td></tr>
              <tr><td>最终评审</td><td>11月上旬</td></tr>
              <tr><td>颁奖</td><td>11月（后续通知）</td></tr>
              </tbody>
            </table>
          </div>
          <div class="modal-section">
            <h3>报名须知</h3>
            <h4>招募要求</h4>
            <ul>
              <li>在校生或在职/自由职业人士（不限专业及学校）</li>
              <li>场地日常使用者（如居民、村民、学生、商户、办公人员等，不限身份）</li>
            </ul>
            <h4>组队要求</h4>
            <ul>
              <li>场地日常使用者：每组至少1人，且不设上限（过程中切实深度参与）</li>
              <li>专业者（学生/从业者）：每组0-7人，支持跨学科、多元化人员组队参与</li>
              <li>指导教师：0-3人（可跨校，自行联络）</li>
            </ul>
          </div>
          <div class="modal-section">
            <h3>场地共建规则</h3>
            <p><strong>两种选址途径：</strong></p>
            <ul>
              <li>自主选址：参赛团队自行寻访、对接符合改造条件的社区场地</li>
              <li>清单选址：暂未找到实践场地的团队，可在共享点位清单中挑选合适场地</li>
            </ul>
            <p>场地面积不限，推荐改造面积 5–20 平方米进行先期实验。评审不以面积大小作为评分依据。</p>
          </div>
          <div class="modal-section">
            <h3>花园建造与材料规范</h3>
            <ul>
              <li>植物选择：优先选用乡土适生植物，降低养护成本，避免外来物种影响</li>
              <li>结构安全：构筑物、装置等必须保证结构坚固稳定，杜绝安全隐患</li>
              <li>可持续运维：花园建成后至少完成 7 天以上运维工作</li>
              <li>材料选择：以可回收、可降解材料为主，倡导利用回收废弃物进行改造再利用</li>
            </ul>
          </div>
          <div class="modal-section">
            <h3>成果要求</h3>
            <p><strong>1. 小红书全过程打卡笔记</strong> —— 全程至少8条有效笔记，覆盖组队、调研、设计、营造、运维5个阶段。须带固定话题并 @官方账号。</p>
            <p><strong>2. 汇报 PowerPoint（30页以内）</strong> —— 包含过程提炼、主题阐述、可持续路径、创新意义。</p>
            <p><strong>3. 汇报视频录制（5分钟以内）</strong> —— 清晰阐述汇报核心内容，突出项目重点与特色。</p>
          </div>
          <div class="modal-section">
            <h3>奖项设置与评审机制</h3>
            <p>一等奖1组 / 二等奖3组 / 三等奖5组，特别奖项将在评审后公开发布。颁发证书。</p>
            <p>综合评分：专家评审 70% + 往届优秀代表评审 20% + 参赛小组互评 10%。</p>
          </div>
          <div class="modal-section">
            <h3>特别说明</h3>
            <ul>
              <li>资料保密：未经书面许可，不得擅自公开发布涉及政府、社区的相关数据与信息</li>
              <li>安全第一：场地踏勘、走访调研须2人及以上结伴同行</li>
              <li>社区沟通与伦理：保持谦逊有礼、真诚尊重，严格保护个人及居民隐私</li>
            </ul>
          </div>
          <div class="modal-section">
            <h3>组织机构</h3>
            <p><strong>指导单位：</strong>中国风景园林学会、上海市风景园林学会</p>
            <p><strong>主办单位：</strong>同济大学建筑与城市规划学院景观学系、《中国园林》杂志社</p>
            <p><strong>承办单位：</strong>上海市城市更新及其空间技术优化重点实验室社区花园与社区营造实验中心、四叶草堂</p>
            <p><strong>联系方式：</strong>霍老师 021-55897175（工作日 10:00-17:00）</p>
          </div>
          <div class="modal-section" style="text-align: center; margin-top: 30px;">
            <a href="https://landscape-caup.tongji.edu.cn/c3/7b/c10586a377723/page.htm" target="_blank" class="intro-button">前往官方页面查看完整信息</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const showCompetitionModal = ref(false)
</script>

<style scoped>
/* Hero Section */
.hero {
  position: relative;
  height: 60vh;
  min-height: 450px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('https://images.communitygarden.org.cn/communitygarden/头图-花开中国.jpg') center center/cover no-repeat;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(90, 125, 90, 0.3);
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  color: var(--white);
  max-width: 900px;
  padding: 0 40px;
  transform: translateY(50px);
}

.hero-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 56px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 6px;
  margin-bottom: 25px;
  text-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}

.hero-subtitle {
  font-size: 16px;
  font-weight: 300;
  letter-spacing: 3px;
  opacity: 0.9;
  text-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
}

section {
  padding: 100px 60px;
}

.section-header {
  text-align: center;
  margin-bottom: 60px;
}

.section-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 36px;
  font-weight: 700;
  color: var(--primary-green-dark);
  margin-bottom: 15px;
  letter-spacing: 3px;
}

.section-subtitle {
  font-size: 14px;
  color: var(--text-light);
  letter-spacing: 2px;
  font-weight: 300;
}

/* 简洁介绍区块 */
.intro-plain-section {
  background: var(--white);
  padding: 60px 60px 80px;
}

.intro-plain-container {
  max-width: 800px;
  margin: 0 auto;
}

.special-message {
  text-align: center;
  margin: 30px auto;
  max-width: 800px;
}

.special-message p {
  font-size: 18px !important;
  font-weight: 500 !important;
  line-height: 1.6 !important;
  color: var(--primary-green) !important;
  margin: 30px 0 !important;
  font-family: 'Noto Serif SC', serif !important;
  letter-spacing: 2px;
  text-align: left;
}

.intro-buttons {
  display: flex;
  justify-content: center;
  gap: 25px;
  margin-top: 30px;
}

.intro-button {
  display: inline-block;
  padding: 15px 30px;
  background: var(--primary-green);
  color: var(--white);
  text-decoration: none;
  border-radius: 25px;
  font-family: 'Noto Serif SC', serif;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.intro-button:hover {
  background: var(--primary-green-dark);
  transform: translateY(-2px);
}

/* 竞赛区块 */
.competition-section {
  background: var(--bg-light);
}

.competition-content {
  max-width: 1100px;
  margin: 0 auto;
}

.competition-intro {
  text-align: left;
  margin-bottom: 50px;
}

.competition-intro p {
  font-size: 15px;
  line-height: 2;
  color: var(--text-gray);
  max-width: 800px;
  margin: 0 auto;
}

.data-visualization {
  text-align: center;
  margin: 40px 0;
}

.data-visualization img {
  max-width: 100%;
  border-radius: 12px;
}

.winners-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 30px;
  margin-top: 60px;
}

.winner-card {
  background: var(--white);
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 15px var(--shadow);
  transition: all 0.3s ease;
}

.winner-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px var(--shadow);
}

.winner-image {
  height: 200px;
  overflow: hidden;
}

.winner-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
}

.winner-content {
  padding: 25px;
  text-align: center;
}

.winner-content h4 {
  font-family: 'Noto Serif SC', serif;
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-green-dark);
  margin-bottom: 10px;
}

.winner-content p {
  font-size: 14px;
  color: var(--text-gray);
  margin: 0;
}

/* 第五届区块 */
.fifth-edition-section {
  background: var(--bg-cream);
}

.fifth-edition-content {
  max-width: 1100px;
  margin: 0 auto;
}

.edition-theme {
  text-align: center;
  margin: 40px 0;
}

.edition-theme p {
  font-size: 15px;
  line-height: 2;
  color: var(--text-gray);
  max-width: 800px;
  margin: 0 auto;
  text-align: left;
}

.edition-philosophy {
  background: var(--bg-cream);
  border-radius: 15px;
  margin: 50px 0;
}

.edition-philosophy p {
  font-size: 15px;
  line-height: 2;
  color: var(--text-gray);
  text-align: left;
}

/* 参与方式区块 */
.participation-section {
  background: var(--bg-light);
}

.participation-content {
  max-width: 1100px;
  margin: 0 auto;
}

.participation-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 40px;
}

.participation-card {
  background: var(--white);
  padding: 40px 30px;
  border-radius: 15px;
  text-align: center;
}

.participation-card h4 {
  font-family: 'Noto Serif SC', serif;
  font-size: 20px;
  font-weight: 700;
  color: var(--primary-green);
  margin-bottom: 20px;
}

.participation-card p {
  font-size: 15px;
  line-height: 2;
  color: var(--text-gray);
}

/* 往届回顾区块 */
.review-section {
  background: var(--white);
}

.review-content {
  max-width: 1100px;
  margin: 0 auto;
}

.review-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-top: 60px;
}

.review-card-link {
  text-decoration: none;
  color: inherit;
  display: block;
}

.review-card {
  background: var(--bg-cream);
  border-radius: 15px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.review-card-link:hover .review-card {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px var(--shadow);
}

.review-image {
  height: 150px;
  overflow: hidden;
}

.review-image img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center center;
}

.review-content-area {
  padding: 30px;
}

.review-content-area p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-gray);
}

/* 第六届入口卡片 */
.edition-2026-card {
  background: linear-gradient(135deg, #f0f7f0 0%, #e8f5e9 100%);
  border: 2px solid var(--primary-green);
  border-radius: 16px;
  padding: 35px 40px;
  margin: 40px 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.edition-2026-card::before {
  content: '';
  position: absolute;
  top: -30px;
  right: -30px;
  width: 120px;
  height: 120px;
  background: var(--primary-green);
  opacity: 0.06;
  border-radius: 50%;
}

.edition-2026-badge {
  display: inline-block;
  background: var(--primary-green);
  color: var(--white);
  padding: 6px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-bottom: 20px;
}

.edition-2026-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 36px;
  font-weight: 700;
  color: var(--primary-green-dark);
  margin-bottom: 10px;
  letter-spacing: 4px;
}

.edition-2026-subtitle {
  font-size: 15px;
  color: var(--text-gray);
  margin-bottom: 20px;
  letter-spacing: 1px;
}

.edition-2026-desc {
  font-size: 15px;
  line-height: 1.9;
  color: var(--text-gray);
  max-width: 700px;
  margin: 0 auto 25px;
}

.edition-2026-meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  max-width: 700px;
  margin: 0 auto 30px;
  text-align: left;
}

.edition-2026-meta-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-gray);
  background: var(--white);
  padding: 12px 16px;
  border-radius: 10px;
}

.meta-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.edition-2026-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.edition-2026-btn {
  display: inline-block;
  padding: 14px 30px;
  border-radius: 25px;
  font-family: 'Noto Serif SC', serif;
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.edition-2026-btn-primary {
  background: var(--primary-green);
  color: var(--white);
}

.edition-2026-btn-primary:hover {
  background: var(--primary-green-dark);
  transform: translateY(-2px);
}

.edition-2026-btn-outline {
  background: transparent;
  color: var(--primary-green);
  border: 1.5px solid var(--primary-green);
}

.edition-2026-btn-outline:hover {
  background: var(--primary-green);
  color: var(--white);
  transform: translateY(-2px);
}

/* 弹层 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow-y: auto;
}

.modal-container {
  background: var(--white);
  border-radius: 16px;
  max-width: 800px;
  width: 100%;
  max-height: 85vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.modal-close {
  position: sticky;
  top: 10px;
  right: 10px;
  float: right;
  z-index: 10;
  background: var(--bg-light);
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 24px;
  color: var(--text-gray);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.modal-close:hover {
  background: var(--primary-green);
  color: var(--white);
}

.modal-body {
  padding: 40px;
}

.modal-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 28px;
  font-weight: 700;
  color: var(--primary-green-dark);
  margin-bottom: 5px;
  letter-spacing: 2px;
}

.modal-subtitle {
  font-size: 18px;
  color: var(--primary-green);
  margin-bottom: 30px;
  font-weight: 600;
}

.modal-section {
  margin-bottom: 25px;
}

.modal-section h3 {
  font-family: 'Noto Serif SC', serif;
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-green-dark);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--bg-cream);
}

.modal-section h4 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-gray);
  margin: 12px 0 8px;
}

.modal-section p {
  font-size: 14px;
  line-height: 1.9;
  color: var(--text-gray);
  margin-bottom: 8px;
}

.modal-section ul {
  list-style: disc;
  padding-left: 20px;
  margin-bottom: 10px;
}

.modal-section ul li {
  font-size: 14px;
  line-height: 1.9;
  color: var(--text-gray);
}

.modal-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.modal-table td {
  padding: 10px 15px;
  border-bottom: 1px solid var(--bg-cream);
  color: var(--text-gray);
  line-height: 1.6;
}

.modal-table td:first-child {
  font-weight: 600;
  width: 140px;
  color: var(--primary-green-dark);
  white-space: nowrap;
}

/* 响应式 */
@media (max-width: 1100px) {
  section {
    padding: 80px 40px;
  }

  .winners-grid,
  .participation-grid,
  .review-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .edition-2026-meta {
    grid-template-columns: 1fr;
  }

  .edition-2026-title {
    font-size: 28px;
  }

  .edition-2026-card {
    padding: 25px 20px;
  }

  .modal-body {
    padding: 25px;
  }

  .modal-title {
    font-size: 22px;
  }
}

@media (max-width: 768px) {
  section {
    padding: 60px 20px;
  }

  .hero {
    height: 40vh;
    min-height: 300px;
  }

  .hero-title {
    font-size: 36px;
    letter-spacing: 3px;
  }

  .hero-subtitle {
    font-size: 13px;
  }

  .section-title {
    font-size: 28px;
  }

  .intro-buttons {
    flex-direction: column;
    align-items: center;
  }

  .intro-plain-section {
    padding: 40px 20px 60px;
  }

  .special-message {
    margin: 30px 20px;
    padding: 25px 20px;
  }

  .special-message p {
    font-size: 14px !important;
  }

  .winners-grid,
  .participation-grid,
  .review-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
  }

  .winner-image {
    height: 150px;
  }

  .winner-content {
    padding: 15px;
  }

  .winner-content h4 {
    font-size: 14px;
  }

  .winner-content p {
    font-size: 12px;
  }

  .edition-2026-actions {
    flex-direction: column;
    align-items: center;
  }

  .edition-2026-meta {
    grid-template-columns: 1fr;
  }

  .modal-container {
    max-height: 90vh;
    border-radius: 12px;
  }

  .modal-body {
    padding: 20px;
  }

  .modal-title {
    font-size: 20px;
  }
}

@media (max-width: 576px) {
  .winners-grid,
  .participation-grid,
  .review-grid {
    grid-template-columns: 1fr;
  }
}
</style>
