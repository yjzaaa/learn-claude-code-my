/**
 * UI Store - 界面状态管理
 * 管理主题、字体、布局等 UI 设置
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 
  | 'midnight'      // 青夜 - 深青蓝 + 暖玫瑰
  | 'warm-paper'    // 暖纸 - 温暖的纸张质感
  | 'forest'        // 森绿 - 森林绿色调
  | 'lavender'      // 薰衣草 - 淡紫色调
  | 'ocean'         // 深海 - 深海蓝色调
  | 'charcoal'      // 墨炭 - 极简深灰
  | 'sakura';       // 樱粉 - 樱花粉色

export type FontMode = 'serif' | 'sans';

export type LayoutMode = 'full' | 'compact';

interface UIState {
  // 主题设置
  theme: Theme;
  setTheme: (theme: Theme) => void;
  
  // 字体模式
  fontMode: FontMode;
  setFontMode: (mode: FontMode) => void;
  
  // 布局模式
  layoutMode: LayoutMode;
  setLayoutMode: (mode: LayoutMode) => void;
  
  // 纹理背景
  showTexture: boolean;
  setShowTexture: (show: boolean) => void;
  
  // Sidebar 折叠
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  
  // 预览面板显示
  previewVisible: boolean;
  setPreviewVisible: (visible: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'midnight',
      setTheme: (theme) => set({ theme }),
      
      fontMode: 'serif',
      setFontMode: (fontMode) => set({ fontMode }),
      
      layoutMode: 'full',
      setLayoutMode: (layoutMode) => set({ layoutMode }),
      
      showTexture: true,
      setShowTexture: (showTexture) => set({ showTexture }),
      
      sidebarCollapsed: false,
      setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
      
      previewVisible: true,
      setPreviewVisible: (previewVisible) => set({ previewVisible }),
    }),
    {
      name: 'hana-ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        fontMode: state.fontMode,
        layoutMode: state.layoutMode,
        showTexture: state.showTexture,
        sidebarCollapsed: state.sidebarCollapsed,
        previewVisible: state.previewVisible,
      }),
    }
  )
);
