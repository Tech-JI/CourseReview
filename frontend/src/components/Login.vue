<template>
  <div class="h-full bg-white">
    <div class="flex min-h-full flex-1 flex-col justify-center px-6 py-12 lg:px-8">
      <div class="sm:mx-auto sm:w-full sm:max-w-sm">
        <h1 class="mt-10 text-center text-2xl font-bold leading-9 tracking-tight text-gray-900">
          JI选课社区身份验证系统
        </h1>
      </div>

      <div class="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
        <form id="verify-form" @submit.prevent="handleTurnstileVerify" class="space-y-6">
          <div>
            <!-- Turnstile widget container -->
            <div
              id="turnstile-container"
              class="cf-turnstile"
            ></div>
          </div>
          <input type="hidden" name="session_id" :value="config.session_id" />
          <div>
            <button
              type="submit"
              id="submit-btn"
              :disabled="!isTurnstileValid || !configLoaded"
              class="flex w-full justify-center rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-semibold leading-6 text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span v-if="!configLoaded">加载中...</span>
              <span v-else-if="loading">获取中...</span>
              <span v-else>获取8位验证码</span>
            </button>
          </div>
        </form>

        <div id="countdown" class="mt-4 text-center text-sm text-gray-500"></div>
        <div id="result" class="mt-4" v-html="resultHtml"></div>
        <div id="code" class="mt-6 text-center text-2xl font-bold text-gray-900">{{ verificationCode }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';

// 响应式数据
const config = ref({
  TURNSTILE_SITE_KEY: '',
  SURVEY_URL: '',
  session_id: ''
});
const configLoaded = ref(false);
const loading = ref(false);
const isTurnstileValid = ref(false);
const verificationCode = ref('');
const resultHtml = ref('');

let turnstileWidgetId = null;

// Turnstile 回调函数 (需要在全局作用域定义，以便 Turnstile 脚本调用)
window.onSuccess = (token) => {
  console.log("Turnstile Success Callback", token);
  isTurnstileValid.value = true;
};

window.onExpired = () => {
  console.warn("Turnstile 验证已过期，重新加载");
  if (window.turnstile && turnstileWidgetId !== null) {
    window.turnstile.reset(turnstileWidgetId);
  }
  isTurnstileValid.value = false;
};

// 在组件挂载时加载必要的数据和初始化
onMounted(async () => {
  try {
    // 1. 获取必要的配置信息
    await fetchConfig();
    configLoaded.value = true;
    
    // 2. 初始化 Turnstile (确保脚本已加载)
    await initializeTurnstile();
    
  } catch (error) {
    console.error("初始化失败:", error);
    showError("初始化失败，请刷新页面重试。");
  }
});

// 在组件卸载前清理
onBeforeUnmount(() => {
  // 移除全局回调函数
  delete window.onSuccess;
  delete window.onExpired;
  
  // 如果需要，可以移除 Turnstile widget
  if (window.turnstile && turnstileWidgetId !== null) {
    window.turnstile.remove(turnstileWidgetId);
  }
});

// 监听 config.TURNSTILE_SITE_KEY 的变化，一旦获取到就渲染 Turnstile
watch(() => config.value.TURNSTILE_SITE_KEY, (newSiteKey) => {
  console.log("TURNSTILE_SITE_KEY changed to:", newSiteKey);
  console.log("Type of newSiteKey:", typeof newSiteKey);
  if (newSiteKey && typeof newSiteKey === 'string' && window.turnstile) {
    console.log("调用 renderTurnstile");
    renderTurnstile();
  } else {
    console.log("条件不满足，未调用 renderTurnstile. newSiteKey:", newSiteKey, "type:", typeof newSiteKey, "window.turnstile:", window.turnstile);
  }
});

// 获取配置信息和 session ID
async function fetchConfig() {
  try {
    const response = await fetch('/verify/api/config/', {
      method: 'GET',
      credentials: 'include' // 确保发送 cookies
    });
    
    console.log("API response:", response);
    
    if (response.ok) {
      const data = await response.json();
      console.log("Parsed JSON data:", data);
      
      // 检查 data 的结构
      if (typeof data === 'object' && data !== null) {
        config.value = data;
        console.log("Config updated:", config.value);
      } else {
        console.error("Unexpected data format:", data);
        throw new Error('Unexpected data format from API');
      }
    } else {
      console.error("API request failed with status:", response.status);
      throw new Error('无法获取配置信息');
    }
  } catch (error) {
    console.error("获取配置信息失败:", error);
    throw error;
  }
}

// 初始化 Turnstile
function initializeTurnstile() {
  return new Promise((resolve) => {
    // 检查 Turnstile 脚本是否已加载
    if (window.turnstile) {
      resolve();
      return;
    }
    
    // 如果未加载，可以设置一个更长的检查间隔
    const checkInterval = setInterval(() => {
      if (window.turnstile) {
        clearInterval(checkInterval);
        resolve();
      }
    }, 200); // 每200ms检查一次
    
    // 设置超时 (10秒)
    setTimeout(() => {
      clearInterval(checkInterval);
      console.warn("Turnstile 脚本加载超时");
      resolve(); // 即使超时也继续，让应用可以运行
    }, 10000);
  });
}

// 渲染 Turnstile widget
function renderTurnstile() {
  const sitekey = config.value.TURNSTILE_SITE_KEY;
  console.log("准备渲染 Turnstile widget, sitekey:", sitekey);
  console.log("Type of sitekey:", typeof sitekey);
  
  if (!sitekey) {
    console.warn("Turnstile sitekey is not available");
    return;
  }
  
  if (typeof sitekey !== 'string') {
    console.error("Turnstile sitekey is not a string:", sitekey);
    return;
  }
  
  // 如果之前已经渲染过，先移除旧的 widget
  if (turnstileWidgetId !== null && window.turnstile) {
    console.log("移除旧的 Turnstile widget");
    window.turnstile.remove(turnstileWidgetId);
  }
  
  // 渲染新的 widget
  const container = document.getElementById('turnstile-container');
  if (container) {
    console.log("找到 Turnstile container");
    turnstileWidgetId = window.turnstile.render('#turnstile-container', {
      sitekey: sitekey,
      callback: window.onSuccess,
      'expired-callback': window.onExpired,
      // 显式指定域名，有时能解决挂起问题
      'data-domain': window.location.hostname === 'localhost' ? 'localhost:5173' : '032bb397fcfb.ngrok-free.app'
    });
    console.log("Turnstile widget rendered with ID:", turnstileWidgetId);
    
    // 添加一个定时器来检查 widget 是否成功初始化
    setTimeout(() => {
      if (turnstileWidgetId !== null) {
        try {
          const widgetResponse = window.turnstile.getResponse(turnstileWidgetId);
          console.log("Widget response after render:", widgetResponse);
        } catch (e) {
          console.error("Error getting widget response:", e);
        }
      }
    }, 2000); // 2秒后检查
    
  } else {
    console.error("Turnstile container not found");
  }
}

// 处理 Turnstile 验证
async function handleTurnstileVerify() {
  if (!isTurnstileValid.value) {
    showError("请先完成验证码验证");
    return;
  }
  
  loading.value = true;
  
  try {
    const formData = new FormData();
    // 获取 Turnstile token
    const token = window.turnstile.getResponse(turnstileWidgetId);
    formData.append('cf-turnstile-response', token);
    formData.append('session_id', config.value.session_id);
    
    const response = await fetch('/verify/turnstile/', {
      method: 'POST',
      body: formData,
      credentials: 'include' // 确保发送 cookies
    });
    
    const data = await response.json();
    
    if (data.success) {
      verificationCode.value = data.code;
      showSuccess("验证通过，已复制验证码");
      
      // 尝试复制到剪贴板
      try {
        await navigator.clipboard.writeText(data.code);
        console.log("验证码已复制到剪贴板");
      } catch (err) {
        console.error("复制到剪贴板失败:", err);
      }
      
      startCountdown(60);
      
      // 打开问卷
      setTimeout(() => {
        window.open(config.value.SURVEY_URL, "_blank", "width=800,height=600");
      }, 1000);
      
      // 启动 SSE 监听
      startSSEListener();
    } else {
      showError(data.error || "验证失败");
    }
  } catch (error) {
    console.error("验证请求失败:", error);
    showError("验证请求失败，请重试。");
  } finally {
    loading.value = false;
  }
}

// 显示成功消息
function showSuccess(message) {
  resultHtml.value = `
    <div class="rounded-md bg-green-50 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm font-medium text-green-800">${message}</p>
        </div>
      </div>
    </div>
  `;
}

// 显示错误消息
function showError(message) {
  resultHtml.value = `
    <div class="rounded-md bg-red-50 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">验证失败</h3>
          <div class="mt-2 text-sm text-red-700">
            <p>${message}</p>
          </div>
        </div>
      </div>
    </div>
  `;
}

// 倒计时
let countdownInterval;
function startCountdown(seconds) {
  const countdownEl = document.getElementById('countdown');
  if (countdownInterval) clearInterval(countdownInterval);
  
  countdownInterval = setInterval(() => {
    seconds--;
    if (countdownEl) {
      countdownEl.textContent = `${seconds}秒后过期`;
    }
    if (seconds <= 0) {
      clearInterval(countdownInterval);
      if (countdownEl) {
        countdownEl.textContent = "验证码已过期";
      }
      verificationCode.value = "";
    }
  }, 1000);
}

// SSE 监听器
let sse;
function startSSEListener() {
  if (sse) {
    sse.close();
  }
  
  sse = new EventSource(`/verify/sse/?session_id=${config.value.session_id}`);
  
  sse.onmessage = function (event) {
    try {
      const data = JSON.parse(event.data);
      console.log("SSE received:", data);
      if (data.status === "fully_verified") {
        // 显示欢迎消息
        resultHtml.value = `
          <div class="rounded-md bg-blue-50 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm font-medium text-blue-800">🎉 欢迎你，${data.name}</p>
              </div>
            </div>
          </div>
        `;
        
        sse.close();
        
        // 调用 completeLogin 函数完成登录流程
        completeLogin();
      }
    } catch (e) {
      console.error("解析SSE数据失败:", e);
    }
  };
  
  sse.onerror = function (event) {
    console.error("SSE连接错误:", event);
    // 可以在这里添加重连逻辑
  };
}

// 完成登录流程
async function completeLogin() {
  try {
    const response = await fetch('/verify/complete_login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') // 获取 CSRF token
      },
      body: JSON.stringify({ session_id: config.value.session_id }),
      credentials: 'include' // 确保发送 cookies
    });
    
    const data = await response.json();
    console.log("Complete login response:", data);
    
    if (data.status === "success") {
      // 登录成功，重定向到 CourseReview 主页
      window.location.href = "/";
    } else {
      console.error("Complete login failed:", data.detail);
      showError(data.detail || "登录过程中发生错误");
    }
  } catch (error) {
    console.error("Complete login request failed:", error);
    showError("登录请求失败，请重试。");
  }
}

// 辅助函数：获取 cookie 值
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
</script>

<style scoped>
/* 如果需要特定的样式，可以在这里添加 */
</style>
