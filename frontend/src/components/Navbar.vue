<template>
  <nav class="navbar" :class="{ scrolled: isScrolled }">
    <div class="navbar-container">
      <!-- Logo and title (fixed left) -->
      <div class="left-section">
        <router-link to="/" class="brand">
          <img src="../assets/logo.svg" alt="Logo" class="logo" :class="{ small: isScrolled }" />
          <span class="title" :class="{ small: isScrolled }">JI Course Review</span>
        </router-link>
      </div>

      <!-- Right section with search, nav links and avatar (fixed right) -->
      <div class="right-section">
        <!-- Search bar - transitions smoothly between full bar and icon -->
        <div class="search-container" :class="{ compact: isScrolled }" @click="handleSearchClick">
          <el-input v-model="searchQuery" placeholder="Search courses..." class="search-input"
            :class="{ shrinking: isScrolled }" @keyup.enter="performSearch" />
          <el-button type="primary" icon="Search" circle class="search-icon-btn" :class="{ small: isScrolled }">
          </el-button>
        </div>

        <!-- Navigation links -->
        <div class="nav-links">
          <router-link to="/best" class="nav-link" :class="{ small: isScrolled }">Best Courses</router-link>
          <router-link to="/layups" class="nav-link" :class="{ small: isScrolled }">Layups</router-link>
        </div>

        <!-- User avatar dropdown -->
        <el-dropdown class="user-dropdown" @command="handleCommand">
          <div class="avatar-wrapper">
            <el-avatar :size="isScrolled ? 32 : 40" :style="{ backgroundColor: userAvatarColor }" class="avatar">
              {{ userAvatarText }}
            </el-avatar>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="account">{{ username }}</el-dropdown-item>
              <el-dropdown-item command="reviews">My Reviews</el-dropdown-item>
              <el-dropdown-item command="logout" divided class="logout-item">Logout</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const searchQuery = ref("");
const isScrolled = ref(false);
const username = ref("Guest");
const colorCache = {}; // Cache for avatar colors
const isSearchExpanded = ref(false);

const userAvatarColor = computed(() => {
  if (username.value === "Guest") {
    return "#C0C4CC"; // Default color for guests
  }

  // Check if we have a cached color for this username
  if (colorCache[username.value]) {
    return colorCache[username.value];
  }

  // Generate a hash from the username
  let hash = 0;
  for (let i = 0; i < username.value.length; i++) {
    hash = username.value.charCodeAt(i) + ((hash << 5) - hash);
  }

  // Convert the hash to a color
  let color = "#";
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff;
    color += ("00" + value.toString(16)).slice(-2);
  }

  // Store in cache
  colorCache[username.value] = color;
  return color;
});

// Get the first letter of username - as a computed property
const userAvatarText = computed(() => {
  if (!username.value || username.value === "Guest") {
    return "G";
  }
  return username.value.charAt(0).toUpperCase();
});

// Handle scroll event
const handleScroll = () => {
  isScrolled.value = window.scrollY > 50;
};

// Handle dropdown commands
const handleCommand = (command) => {
  switch (command) {
    case "account":
      router.push("/account");
      break;
    case "reviews":
      router.push("/my/reviews");
      break;
    case "logout":
      // Handle logout
      break;
  }
};

// Unified search click handler
const handleSearchClick = () => {
  if (isScrolled.value) {
    isSearchExpanded.value = true;
    isScrolled.value = false; // Temporarily unscroll

    // Focus the input after a brief delay for transitions
    setTimeout(() => {
      document.querySelector(".search-input input").focus();
    }, 100);

    // Add a one-time click listener to detect clicks outside
    const handleClickOutside = (e) => {
      if (!e.target.closest(".search-container")) {
        isSearchExpanded.value = false;
        isScrolled.value = window.scrollY > 50; // Restore scroll state
        document.removeEventListener("click", handleClickOutside);
      }
    };

    document.addEventListener("click", handleClickOutside);
  }
};

// Perform search
const performSearch = () => {
  if (searchQuery.value.trim().length >= 2) {
    router.push({
      path: "/search",
      query: { q: searchQuery.value.trim() },
    });
  }
};

// Fetch user status
const fetchUserStatus = async () => {
  try {
    const response = await fetch("/api/user/status/");
    if (response.ok) {
      const data = await response.json();
      username.value = data.username || "Guest";
    }
  } catch (error) {
    console.error("Error fetching user status:", error);
  }
};

onMounted(() => {
  window.addEventListener("scroll", handleScroll);
  fetchUserStatus();
});
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
  height: 80px;
}

.navbar.scrolled {
  height: 60px;
}

.navbar-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  /* This pushes the left and right sections apart */
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  padding: 0 1.5rem;
}

.left-section {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
  height: 100%;
}

.right-section {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  transition: all 0.3s ease;
}

.brand {
  display: flex;
  align-items: center;
  text-decoration: none;
}

.logo {
  height: 40px;
  margin-right: 0.75rem;
  transition: all 0.3s ease;
}

.logo.small {
  height: 30px;
}

.title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--el-color-primary);
  transition: all 0.3s ease;
  overflow: hidden;
  white-space: nowrap;
}

.title.small {
  font-size: 0.95rem;
}

.search-container {
  position: relative;
  width: 300px;
  transition: all 0.3s ease;
  display: flex;
  justify-content: flex-end;
  /* Change from center to flex-end to align to the right */
  cursor: pointer;
}

.search-container.compact {
  width: 40px;
}

.search-input {
  width: 100%;
  right: 1.2rem;
  transition: all 0.3s ease;
  transform-origin: right center;
  /* Keep this for the right-side expansion */
  position: relative;
}

:deep(.search-input .el-input__wrapper) {
  border-top-left-radius: 20px;
  border-bottom-left-radius: 20px;
  padding-left: 15px;
}

.search-input.shrinking {
  width: 0px;
  opacity: 0;
  margin-right: 40px;
  /* Add margin to accommodate the search icon */
  pointer-events: none;
}

.search-icon-btn {
  font-size: 1.2rem;
  transition: all 0.3s ease;
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%) scale(1);
  opacity: 1;
  pointer-events: none;
  /* Keep button non-interactive */
  z-index: 1;
}

/* .search-icon-btn.small {
  font-size: 1rem;
  transform: translateY(-50%) scale(0.9);
} */

.nav-links {
  display: flex;
  gap: 1.5rem;
  transition: all 0.3s ease;
}

.nav-link {
  text-decoration: none;
  color: var(--el-text-color-regular);
  font-weight: 500;
  transition: all 0.3s ease;
  white-space: nowrap;
  font-size: 1rem;
}

.nav-link:hover {
  color: var(--el-color-primary);
}

.nav-link.small {
  font-size: 0.9rem;
}

.user-dropdown {
  transition: all 0.3s ease;
}

.avatar-wrapper {
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 50%;
  transition: background-color 0.3s;
}

.avatar {
  transition: all 0.3s ease;
}

.avatar-wrapper:hover {
  background-color: var(--el-color-primary-light-9);
}

:deep(.logout-item) {
  color: var(--el-color-danger);
}

@media (max-width: 768px) {
  .navbar-container {
    padding: 0 0.75rem;
  }

  .title {
    display: none;
  }

  .search-container {
    width: 200px;
  }

  .search-container.compact {
    width: 40px;
  }

  .nav-links {
    display: none;
  }
}
</style>
