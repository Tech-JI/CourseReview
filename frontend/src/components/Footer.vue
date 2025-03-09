<template>
  <footer class="footer">
    <div class="footer-content">
      <div class="footer-section">
        <h4>JI Course Review</h4>
        <p>Your guide to courses at JI</p>
      </div>
      
      <div class="footer-section">
        <h4>Quick Links</h4>
        <ul>
          <li><router-link to="/best">Best Courses</router-link></li>
          <li><router-link to="/layups">Layups</router-link></li>
          <li><router-link to="/departments">Departments</router-link></li>
        </ul>
      </div>
      
      <div class="footer-section">
        <h4>Contact</h4>
        <p>Email: support@jicoursereview.com</p>
      </div>
    </div>
    
    <div class="footer-bottom">
      <p>&copy; {{ new Date().getFullYear() }} JI Course Review. All rights reserved.</p>
    </div>
  </footer>
</template>

<script setup>
import { ref } from 'vue'

const year = ref(new Date().getFullYear())
</script>

<style scoped>
.footer {
  background-color: var(--el-color-primary);
  color: white;
  padding: 2rem 1rem;
  margin-top: auto;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
}

.footer-section {
  flex: 1;
  margin: 0 1rem;
}

.footer-section h4 {
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.footer-section ul {
  list-style: none;
  padding: 0;
}

.footer-section ul li {
  margin: 0.5rem 0;
}

.footer-section a {
  color: white;
  text-decoration: none;
  transition: opacity 0.2s;
}

.footer-section a:hover {
  opacity: 0.8;
}

.footer-bottom {
  text-align: center;
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

@media (max-width: 768px) {
  .footer-content {
    flex-direction: column;
    text-align: center;
  }
  
  .footer-section {
    margin: 1rem 0;
  }
}
</style>
