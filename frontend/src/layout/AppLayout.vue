<template>
  <div class="min-h-full">
    <Disclosure
      v-slot="{ open }"
      as="nav"
      class="border-b border-gray-200 bg-white"
    >
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 justify-between">
          <div class="flex">
            <div class="flex shrink-0 items-center">
              <router-link to="/" class="text-xl font-bold text-indigo-600">
                JI Course Review
              </router-link>
            </div>
            <div
              class="hidden sm:-my-px sm:ml-6 sm:flex sm:space-x-8 relative z-10"
            >
              <router-link
                v-for="item in navigation"
                :key="item.name"
                :to="item.href"
                :class="[
                  $route.path === item.href ||
                  ($route.path.startsWith('/course') &&
                    item.name === 'Browse Courses')
                    ? 'border-indigo-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700',
                  'inline-flex items-center border-b-2 px-3 py-2 text-sm font-medium cursor-pointer min-h-[44px]',
                ]"
              >
                {{ item.name }}
              </router-link>
            </div>
          </div>

          <div
            v-if="showSearchBar"
            class="flex-1 flex justify-center px-2 lg:ml-6 lg:justify-end self-center"
          >
            <div class="max-w-lg w-full lg:max-w-xs">
              <label for="search" class="sr-only">Search courses</label>
              <div class="relative">
                <div
                  class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3"
                >
                  <MagnifyingGlassIcon
                    class="h-5 w-5 text-gray-400"
                    aria-hidden="true"
                  />
                </div>
                <input
                  id="search"
                  v-model="searchQuery"
                  name="search"
                  class="block w-full rounded-md border-0 bg-white py-1.5 pl-10 pr-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                  placeholder="Search courses..."
                  type="search"
                  @keyup.enter="performSearch"
                />
              </div>
            </div>
          </div>

          <div class="hidden sm:ml-6 sm:flex sm:items-center relative z-10">
            <div v-if="isAuthenticated" class="relative">
              <Menu as="div" class="relative">
                <div>
                  <MenuButton
                    class="relative flex max-w-xs items-center rounded-full bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-hidden cursor-pointer hover:bg-gray-50"
                  >
                    <span class="absolute -inset-1.5" />
                    <span class="sr-only">Open user menu</span>
                    <div
                      class="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center"
                    >
                      <UserIcon class="h-5 w-5 text-indigo-600" />
                    </div>
                  </MenuButton>
                </div>
                <transition
                  enter-active-class="transition ease-out duration-200"
                  enter-from-class="transform opacity-0 scale-95"
                  enter-to-class="transform opacity-100 scale-100"
                  leave-active-class="transition ease-in duration-75"
                  leave-from-class="transform opacity-100 scale-100"
                  leave-to-class="transform opacity-0 scale-95"
                >
                  <MenuItems
                    class="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white py-1 ring-1 shadow-lg ring-black/5 focus:outline-hidden"
                  >
                    <MenuItem
                      v-for="item in userNavigation"
                      :key="item.name"
                      v-slot="{ active }"
                    >
                      <button
                        :class="[
                          active ? 'bg-gray-100 outline-hidden' : '',
                          'block px-4 py-2 text-sm text-gray-700 w-full text-left cursor-pointer hover:bg-gray-100',
                        ]"
                        @click="item.action"
                      >
                        {{ item.name }}
                      </button>
                    </MenuItem>
                  </MenuItems>
                </transition>
              </Menu>
            </div>
            <div v-else class="space-x-4">
              <router-link
                to="/accounts/login"
                class="text-gray-500 hover:text-gray-700 px-3 py-2 text-sm font-medium cursor-pointer inline-flex items-center min-h-[44px]"
              >
                Login
              </router-link>
            </div>
          </div>

          <div class="-mr-2 flex items-center sm:hidden">
            <DisclosureButton
              class="relative inline-flex items-center justify-center rounded-md bg-white p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:outline-hidden"
            >
              <span class="absolute -inset-0.5" />
              <span class="sr-only">Open main menu</span>
              <Bars3Icon
                v-if="!open"
                class="block h-6 w-6"
                aria-hidden="true"
              />
              <XMarkIcon v-else class="block h-6 w-6" aria-hidden="true" />
            </DisclosureButton>
          </div>
        </div>
      </div>

      <DisclosurePanel class="sm:hidden">
        <div class="space-y-1 pt-2 pb-3">
          <DisclosureButton
            v-for="item in navigation"
            :key="item.name"
            as="router-link"
            :to="item.href"
            :class="[
              $route.path === item.href
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-transparent text-gray-600 hover:border-gray-300 hover:bg-gray-50 hover:text-gray-800',
              'block border-l-4 py-2 pr-4 pl-3 text-base font-medium',
            ]"
          >
            {{ item.name }}
          </DisclosureButton>
        </div>
        <div v-if="!isAuthenticated" class="border-t border-gray-200 pt-4 pb-3">
          <div class="space-y-1">
            <DisclosureButton
              as="router-link"
              to="/accounts/login"
              class="block px-4 py-2 text-base font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-800"
            >
              Login
            </DisclosureButton>
          </div>
        </div>
      </DisclosurePanel>
    </Disclosure>

    <main>
      <slot />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useAuth } from "../composables/useAuth";
import { useRoute, useRouter } from "vue-router";
import {
  Disclosure,
  DisclosureButton,
  DisclosurePanel,
  Menu,
  MenuButton,
  MenuItem,
  MenuItems,
} from "@headlessui/vue";
import {
  Bars3Icon,
  XMarkIcon,
  MagnifyingGlassIcon,
  UserIcon,
} from "@heroicons/vue/24/outline";

const route = useRoute();
const router = useRouter();
const searchQuery = ref("");
const { isAuthenticated, logout } = useAuth();

const navigation = [
  { name: "Home", href: "/" },
  { name: "Browse Courses", href: "/courses" },
];

const handleLogout = async () => {
  const ok = await logout();
  if (ok) {
    router.push("/");
  }
};

const userNavigation = [{ name: "Sign out", href: "#", action: handleLogout }];

const showSearchBar = computed(() => {
  return route.path !== "/";
});

const performSearch = () => {
  const query = searchQuery.value.trim();
  if (query.length >= 2) {
    router.push({
      path: "/courses",
      query: { code: query.toUpperCase() },
    });
    searchQuery.value = "";
  }
};
</script>
